from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.utils import timezone
from loguru import logger
from rest_framework import serializers

from apps.core.serializers import DualKeyModelSerializer
from apps.events.models import Event
from apps.registrations.models import Registration
from apps.registrations.tasks import schedule_event_reminder
from apps.tickets.models import Ticket

User = get_user_model()

__all__ = ["RegistrationSerializer"]


class RegistrationSerializer(DualKeyModelSerializer):
    """
    Registration serializer enforcing domain User Registration rules and 2-hour pre-Event reminder lifecycle:
    - Dual-key ticket / ticket_id resolution with Ticket.objects.select_related("event")
    - Dual-key user / user_id resolution defaulting to request.user
    - Unique (ticket, user) registration enforcement
    - Active ticket sales window verification (sales_start <= now <= sales_end)
    - Row-level locking (select_for_update) on Ticket and Event during intake to enforce quota capacity
    - Automatic resilient 2-hour pre-Event reminder scheduling inside create()
    """

    id = serializers.UUIDField(read_only=True)
    ticket_id = serializers.CharField(required=False, write_only=False)
    user_id = serializers.CharField(required=False, write_only=False)

    dual_key_fields = {
        "ticket": {
            "queryset": Ticket.objects.select_related("event"),
            "id_keys": ("ticket_id", "ticket"),
            "required_on_create": True,
            "label": "Ticket",
        },
        "user": {
            "queryset": User.objects.all(),
            "id_keys": ("user_id", "user"),
            "default_to_request_user": True,
            "required_on_create": True,
            "label": "User",
        },
    }

    class Meta:
        model = Registration
        fields = ["id", "ticket", "ticket_id", "user", "user_id"]
        read_only_fields = ["id", "ticket", "user"]

    def validate(self, attrs):
        attrs = super().validate(attrs)
        ticket = attrs.get("ticket") or (self.instance.ticket if self.instance else None)
        user = attrs.get("user") or (self.instance.user if self.instance else None)
        instance_pk = self.instance.pk if self.instance else None

        if ticket is not None and user is not None:
            now = timezone.now()
            if now < ticket.sales_start or now > ticket.sales_end:
                raise serializers.ValidationError({"ticket": "Ticket sales window is not currently active."})

            if Registration.objects.filter(ticket=ticket, user=user).exclude(pk=instance_pk).exists():
                raise serializers.ValidationError({"detail": "User is already registered for this ticket."})

            ticket_reg_count = Registration.objects.filter(ticket=ticket).exclude(pk=instance_pk).count()
            if ticket_reg_count >= ticket.quota:
                raise serializers.ValidationError({"ticket": "Ticket quota has been reached."})

            event = getattr(ticket, "event", None)
            if event is not None and hasattr(event, "quota"):
                event_reg_count = Registration.objects.filter(ticket__event=event).exclude(pk=instance_pk).count()
                if event_reg_count >= event.quota:
                    raise serializers.ValidationError({"ticket": "Event quota has been reached."})

        return attrs

    def create(self, validated_data):
        ticket = validated_data["ticket"]
        user = validated_data["user"]
        instance_pk = self.instance.pk if self.instance else None

        try:
            with transaction.atomic():
                locked_ticket = Ticket.objects.select_for_update().select_related("event").get(pk=ticket.pk)
                locked_event = Event.objects.select_for_update().filter(tickets=locked_ticket).get()

                now = timezone.now()
                if now < locked_ticket.sales_start or now > locked_ticket.sales_end:
                    raise serializers.ValidationError({"ticket": "Ticket sales window is not currently active."})

                if Registration.objects.filter(ticket=locked_ticket, user=user).exclude(pk=instance_pk).exists():
                    raise serializers.ValidationError({"detail": "User is already registered for this ticket."})

                ticket_reg_count = Registration.objects.filter(ticket=locked_ticket).exclude(pk=instance_pk).count()
                if ticket_reg_count >= locked_ticket.quota:
                    raise serializers.ValidationError({"ticket": "Ticket quota has been reached."})

                event_reg_count = (
                    Registration.objects.filter(ticket__event=locked_event).exclude(pk=instance_pk).count()
                )
                if event_reg_count >= locked_event.quota:
                    raise serializers.ValidationError({"ticket": "Event quota has been reached."})

                registration = super().create(validated_data)
        except IntegrityError:
            raise serializers.ValidationError({"detail": "User is already registered for this ticket."})

        try:
            schedule_event_reminder(registration)
        except Exception as exc:
            logger.warning(f"Failed to schedule 2-hour pre-event reminder for registration {registration.id}: {exc}")
        return registration

    def update(self, instance, validated_data):
        ticket = validated_data.get("ticket", instance.ticket)
        user = validated_data.get("user", instance.user)
        instance_pk = instance.pk

        try:
            with transaction.atomic():
                locked_ticket = Ticket.objects.select_for_update().select_related("event").get(pk=ticket.pk)
                locked_event = Event.objects.select_for_update().filter(tickets=locked_ticket).get()

                now = timezone.now()
                if now < locked_ticket.sales_start or now > locked_ticket.sales_end:
                    raise serializers.ValidationError({"ticket": "Ticket sales window is not currently active."})

                if Registration.objects.filter(ticket=locked_ticket, user=user).exclude(pk=instance_pk).exists():
                    raise serializers.ValidationError({"detail": "User is already registered for this ticket."})

                if ticket.pk != instance.ticket_id:
                    ticket_reg_count = Registration.objects.filter(ticket=locked_ticket).exclude(pk=instance_pk).count()
                    if ticket_reg_count >= locked_ticket.quota:
                        raise serializers.ValidationError({"ticket": "Ticket quota has been reached."})

                    if locked_ticket.event_id != instance.ticket.event_id:
                        event_reg_count = (
                            Registration.objects.filter(ticket__event=locked_event).exclude(pk=instance_pk).count()
                        )
                        if event_reg_count >= locked_event.quota:
                            raise serializers.ValidationError({"ticket": "Event quota has been reached."})

                return super().update(instance, validated_data)
        except IntegrityError:
            raise serializers.ValidationError({"detail": "User is already registered for this ticket."})
