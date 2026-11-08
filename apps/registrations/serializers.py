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

    def _validate_and_lock_registration_intake(self, ticket, user, instance=None, lock_rows=False):
        """
        Validate registration intake rules and optionally lock ticket/event rows with select_for_update():
        - Sales window check: enforced on create or when ticket is changing on update
        - Uniqueness check: single registration per (ticket, user)
        - Ticket quota check: enforced on create or when ticket is changing on update
        - Event quota check: enforced on create or when ticket changes across events on update
        """
        if lock_rows:
            locked_ticket = Ticket.objects.select_for_update().select_related("event").get(pk=ticket.pk)
            locked_event = Event.objects.select_for_update().filter(tickets=locked_ticket).get()
        else:
            locked_ticket = ticket
            locked_event = getattr(ticket, "event", None)

        instance_pk = instance.pk if instance else None
        is_ticket_changing = instance is None or str(ticket.pk) != str(instance.ticket_id)

        if is_ticket_changing:
            now = timezone.now()
            if now < locked_ticket.sales_start or now > locked_ticket.sales_end:
                raise serializers.ValidationError({"ticket": "Ticket sales window is not currently active."})

        if Registration.objects.filter(ticket=locked_ticket, user=user).exclude(pk=instance_pk).exists():
            raise serializers.ValidationError({"detail": "User is already registered for this ticket."})

        if is_ticket_changing:
            ticket_reg_count = Registration.objects.filter(ticket=locked_ticket).exclude(pk=instance_pk).count()
            if ticket_reg_count >= locked_ticket.quota:
                raise serializers.ValidationError({"ticket": "Ticket quota has been reached."})

            if locked_event is not None and hasattr(locked_event, "quota"):
                if instance is None or locked_ticket.event_id != instance.ticket.event_id:
                    event_reg_count = (
                        Registration.objects.filter(ticket__event=locked_event).exclude(pk=instance_pk).count()
                    )
                    if event_reg_count >= locked_event.quota:
                        raise serializers.ValidationError({"ticket": "Event quota has been reached."})

        return locked_ticket, locked_event

    def validate(self, attrs):
        attrs = super().validate(attrs)
        ticket = attrs.get("ticket") or (self.instance.ticket if self.instance else None)
        user = attrs.get("user") or (self.instance.user if self.instance else None)

        if ticket is not None and user is not None:
            self._validate_and_lock_registration_intake(
                ticket=ticket, user=user, instance=self.instance, lock_rows=False
            )

        return attrs

    def create(self, validated_data):
        ticket = validated_data["ticket"]
        user = validated_data["user"]

        try:
            with transaction.atomic():
                self._validate_and_lock_registration_intake(ticket=ticket, user=user, instance=None, lock_rows=True)
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

        try:
            with transaction.atomic():
                self._validate_and_lock_registration_intake(ticket=ticket, user=user, instance=instance, lock_rows=True)
                return super().update(instance, validated_data)
        except IntegrityError:
            raise serializers.ValidationError({"detail": "User is already registered for this ticket."})
