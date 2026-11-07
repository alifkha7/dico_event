from django.contrib.auth import get_user_model
from rest_framework import serializers

from apps.core.serializers import DualKeyModelSerializer, _resolve_foreign_key
from apps.events.serializers import (
    EventPosterSerializer,
    EventPosterUploadSerializer,
    EventSerializer,
)
from apps.tickets.serializers import TicketSerializer
from apps.users.serializers import (
    AssignRoleSerializer,
    CustomTokenObtainPairSerializer,
    GroupSerializer,
    UserSerializer,
)

from .models import Payment, Registration, Ticket

User = get_user_model()

__all__ = [
    "AssignRoleSerializer",
    "CustomTokenObtainPairSerializer",
    "DualKeyModelSerializer",
    "EventPosterSerializer",
    "EventPosterUploadSerializer",
    "EventSerializer",
    "GroupSerializer",
    "PaymentSerializer",
    "RegistrationSerializer",
    "TicketSerializer",
    "UserSerializer",
    "_resolve_foreign_key",
]


class RegistrationSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(read_only=True)
    ticket_id = serializers.CharField(required=False, write_only=False)
    user_id = serializers.CharField(required=False, write_only=False)

    class Meta:
        model = Registration
        fields = ["id", "ticket", "ticket_id", "user", "user_id"]
        read_only_fields = ["id", "ticket", "user"]

    def validate(self, attrs):
        request = self.context.get("request")

        _resolve_foreign_key(
            attrs=attrs,
            initial_data=self.initial_data,
            instance=self.instance,
            field_name="ticket",
            id_keys=["ticket_id", "ticket"],
            model_class=Ticket,
            required_on_create=True,
            select_related=("event",),
        )

        _resolve_foreign_key(
            attrs=attrs,
            initial_data=self.initial_data,
            instance=self.instance,
            field_name="user",
            id_keys=["user_id", "user"],
            model_class=User,
            default_fn=lambda: request.user if request and request.user and request.user.is_authenticated else None,
            required_on_create=True,
            label="User",
        )
        return attrs

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        ret["id"] = str(instance.id)
        ret["ticket"] = str(instance.ticket_id)
        ret["ticket_id"] = str(instance.ticket_id)
        ret["user"] = str(instance.user_id)
        ret["user_id"] = str(instance.user_id)
        return ret


class PaymentSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(read_only=True)
    registration_id = serializers.CharField(required=False, write_only=False)
    amount_paid = serializers.IntegerField(required=False)

    class Meta:
        model = Payment
        fields = [
            "id",
            "registration",
            "registration_id",
            "payment_method",
            "payment_status",
            "amount_paid",
        ]
        read_only_fields = ["id", "registration"]

    def validate(self, attrs):
        if self.instance is None:
            required_fields = ["payment_method", "payment_status", "amount_paid"]
            missing = [f for f in required_fields if f not in attrs and f not in self.initial_data]
            if missing:
                raise serializers.ValidationError({f: "This field is required." for f in missing})

        _resolve_foreign_key(
            attrs=attrs,
            initial_data=self.initial_data,
            instance=self.instance,
            field_name="registration",
            id_keys=["registration_id", "registration"],
            model_class=Registration,
            required_on_create=True,
            select_related=("user",),
        )

        # ADR-0001: Normalize 'completed' (case-insensitive) to 'Completed'
        status_val = attrs.get("payment_status") or self.initial_data.get("payment_status")
        if status_val is not None and str(status_val).strip().lower() == "completed":
            attrs["payment_status"] = "Completed"

        return attrs

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        ret["id"] = str(instance.id)
        ret["registration"] = str(instance.registration_id)
        ret["registration_id"] = str(instance.registration_id)
        ret["payment_method"] = str(instance.payment_method)
        if instance.payment_status and instance.payment_status.strip().lower() == "completed":
            ret["payment_status"] = "Completed"
        else:
            ret["payment_status"] = str(instance.payment_status)
        ret["amount_paid"] = int(instance.amount_paid)
        return ret
