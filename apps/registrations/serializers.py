from django.contrib.auth import get_user_model
from loguru import logger
from rest_framework import serializers

from apps.core.serializers import DualKeyModelSerializer
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

    def create(self, validated_data):
        registration = super().create(validated_data)
        try:
            schedule_event_reminder(registration)
        except Exception as exc:
            logger.warning(f"Failed to schedule 2-hour pre-event reminder for registration {registration.id}: {exc}")
        return registration
