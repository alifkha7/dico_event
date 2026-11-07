from rest_framework import serializers

from apps.core.serializers import DualKeyModelSerializer
from apps.events.models import Event

from .models import Ticket

__all__ = ["TicketSerializer"]


class TicketSerializer(DualKeyModelSerializer):
    """
    Ticket serializer enforcing domain Ticket rules:
    - Dual-key event / event_id resolution with caller-supplied eager-loading hints
    - Non-negative price (>= 0)
    - Positive quota (> 0)
    - Valid sales window (sales_start < sales_end)
    """

    id = serializers.UUIDField(read_only=True)
    price = serializers.IntegerField(required=False)
    quota = serializers.IntegerField(required=False)
    event_id = serializers.CharField(required=False, write_only=False)

    dual_key_fields = {
        "event": {
            "queryset": Event.objects.select_related("organizer"),
            "id_keys": ("event_id", "event"),
            "required_on_create": True,
            "label": "Event",
        }
    }

    class Meta:
        model = Ticket
        fields = [
            "id",
            "event",
            "event_id",
            "name",
            "price",
            "sales_start",
            "sales_end",
            "quota",
        ]
        read_only_fields = ["id", "event"]

    def validate(self, attrs):
        if self.instance is None:
            required_fields = ["name", "price", "sales_start", "sales_end", "quota"]
            missing = [f for f in required_fields if f not in attrs and f not in self.initial_data]
            if missing:
                raise serializers.ValidationError({f: "This field is required." for f in missing})

        if "price" in attrs and attrs["price"] < 0:
            raise serializers.ValidationError({"price": "Price must be non-negative."})

        if "quota" in attrs and attrs["quota"] <= 0:
            raise serializers.ValidationError({"quota": "Quota must be positive."})

        start = attrs.get("sales_start", getattr(self.instance, "sales_start", None))
        end = attrs.get("sales_end", getattr(self.instance, "sales_end", None))
        if start is not None and end is not None and start >= end:
            raise serializers.ValidationError({"sales_end": "Sales end must be after sales start."})

        return super().validate(attrs)

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        ret["id"] = str(instance.id)
        ret["event"] = str(instance.event_id)
        ret["event_id"] = str(instance.event_id)
        ret["name"] = str(instance.name)
        ret["price"] = int(instance.price)
        ret["quota"] = int(instance.quota)
        return ret
