from rest_framework import serializers

from apps.core.serializers import DualKeyModelSerializer
from apps.registrations.models import Registration

from .models import Payment

__all__ = ["PaymentSerializer"]


class PaymentSerializer(DualKeyModelSerializer):
    """
    Payment serializer enforcing domain payment rules:
    - Dual-key registration / registration_id resolution with Registration.objects.select_related("user")
    - Positive amount_paid (> 0)
    - ADR-0001 case-insensitive 'completed' status normalization to 'Completed'
    """

    id = serializers.UUIDField(read_only=True)
    registration_id = serializers.CharField(required=False, write_only=False)
    amount_paid = serializers.IntegerField(required=False)

    dual_key_fields = {
        "registration": {
            "queryset": Registration.objects.select_related("user"),
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

    def validate(self, attrs):
        if self.instance is None:
            required_fields = ["payment_method", "payment_status", "amount_paid"]
            missing = [f for f in required_fields if f not in attrs and f not in self.initial_data]
            if missing:
                raise serializers.ValidationError({f: "This field is required." for f in missing})

        if "amount_paid" in attrs and attrs["amount_paid"] <= 0:
            raise serializers.ValidationError({"amount_paid": "Amount paid must be positive."})

        # ADR-0001: Normalize 'completed' (case-insensitive) to 'Completed'
        status_val = attrs.get("payment_status")
        if status_val is None and self.initial_data:
            status_val = self.initial_data.get("payment_status")
        if status_val is not None and str(status_val).strip().lower() == "completed":
            attrs["payment_status"] = "Completed"

        return super().validate(attrs)

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
