from django.db import transaction
from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied

from apps.core.permissions import is_admin_user
from apps.core.serializers import DualKeyModelSerializer
from apps.registrations.models import Registration

from .models import Payment

__all__ = ["CANONICAL_PAYMENT_STATUSES", "PaymentSerializer"]

CANONICAL_PAYMENT_STATUSES = {
    "pending": "Pending",
    "completed": "Completed",
    "failed": "Failed",
    "refunded": "Refunded",
}


class PaymentSerializer(DualKeyModelSerializer):
    """
    Payment serializer enforcing domain payment rules:
    - Dual-key registration / registration_id resolution with Registration.objects.select_related("user", "ticket")
    - Non-negative amount_paid matching exact Ticket.price
    - Case-insensitive payment_status validation and canonical normalization
      ('Pending', 'Completed', 'Failed', 'Refunded')
    """

    id = serializers.UUIDField(read_only=True)
    registration_id = serializers.CharField(required=False, write_only=False)
    payment_status = serializers.CharField(required=False, allow_blank=True)
    amount_paid = serializers.IntegerField(required=False)

    dual_key_fields = {
        "registration": {
            "queryset": Registration.objects.select_related("user", "ticket"),
            "id_keys": ("registration_id", "registration"),
            "required_on_create": True,
            "label": "Registration",
        }
    }

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

    def validate_amount_paid(self, value):
        if value is not None and value < 0:
            raise serializers.ValidationError("Amount paid must be non-negative.")
        return value

    def validate_payment_status(self, value):
        if value is None:
            return value
        cleaned = str(value).strip().lower()
        if not cleaned or cleaned not in CANONICAL_PAYMENT_STATUSES:
            raise serializers.ValidationError(
                "Invalid payment status. Must be one of: Pending, Completed, Failed, Refunded."
            )
        normalized = CANONICAL_PAYMENT_STATUSES[cleaned]
        if normalized == "Refunded":
            request = self.context.get("request")
            if request and hasattr(request, "user") and not is_admin_user(request.user):
                raise PermissionDenied("Only Admin or Superuser actors can set payment status to Refunded.")
        return normalized

    def validate(self, attrs):
        if self.instance is None:
            required_fields = ["payment_method", "payment_status", "amount_paid"]
            missing = [f for f in required_fields if f not in attrs and f not in self.initial_data]
            if missing:
                raise serializers.ValidationError({f: "This field is required." for f in missing})

        attrs = super().validate(attrs)

        # Resolve registration and validate exact ticket price matching
        registration = attrs.get("registration") or (self.instance.registration if self.instance else None)
        amount_paid = (
            attrs.get("amount_paid")
            if "amount_paid" in attrs
            else (self.instance.amount_paid if self.instance else None)
        )

        if registration and hasattr(registration, "ticket") and amount_paid is not None:
            ticket_price = registration.ticket.price
            if amount_paid != ticket_price:
                raise serializers.ValidationError(
                    {"amount_paid": f"Amount paid must equal the ticket price ({ticket_price})."}
                )

        target_status = attrs.get("payment_status") or (self.instance.payment_status if self.instance else None)
        if target_status == "Completed" and registration:
            with transaction.atomic():
                Registration.objects.select_for_update().get(pk=registration.pk)
                existing_completed = (
                    Payment.objects.filter(registration=registration, payment_status="Completed")
                    .exclude(pk=self.instance.pk if self.instance else None)
                    .exists()
                )
                if existing_completed:
                    raise serializers.ValidationError(
                        {"payment_status": "This registration already has a completed payment."}
                    )

        return attrs

    def create(self, validated_data):
        registration = validated_data.get("registration")
        payment_status = validated_data.get("payment_status")
        with transaction.atomic():
            if registration and payment_status == "Completed":
                Registration.objects.select_for_update().get(pk=registration.pk)
                if Payment.objects.filter(registration=registration, payment_status="Completed").exists():
                    raise serializers.ValidationError(
                        {"payment_status": "This registration already has a completed payment."}
                    )
            return super().create(validated_data)

    def update(self, instance, validated_data):
        registration = validated_data.get("registration") or instance.registration
        payment_status = validated_data.get("payment_status") or instance.payment_status
        with transaction.atomic():
            if registration and payment_status == "Completed":
                Registration.objects.select_for_update().get(pk=registration.pk)
                if (
                    Payment.objects.filter(registration=registration, payment_status="Completed")
                    .exclude(pk=instance.pk)
                    .exists()
                ):
                    raise serializers.ValidationError(
                        {"payment_status": "This registration already has a completed payment."}
                    )
            return super().update(instance, validated_data)

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        ret["id"] = str(instance.id)
        ret["registration"] = str(instance.registration_id)
        ret["registration_id"] = str(instance.registration_id)
        ret["payment_method"] = str(instance.payment_method)
        raw_status = str(instance.payment_status).strip().lower() if instance.payment_status else ""
        ret["payment_status"] = CANONICAL_PAYMENT_STATUSES.get(raw_status, str(instance.payment_status))
        ret["amount_paid"] = int(instance.amount_paid)
        return ret
