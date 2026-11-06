from django.contrib.auth import get_user_model
from PIL import Image
from rest_framework import serializers

from apps.core.serializers import DualKeyModelSerializer
from apps.events.models import Event, EventPoster

User = get_user_model()

__all__ = [
    "EventPosterSerializer",
    "EventPosterUploadSerializer",
    "EventSerializer",
]


class EventSerializer(DualKeyModelSerializer):
    """Event serializer with dual-key organizer/organizer_id resolution."""

    id = serializers.UUIDField(read_only=True)
    quota = serializers.IntegerField(required=False)
    organizer_id = serializers.CharField(required=False, write_only=False)

    dual_key_fields = {
        "organizer": {
            "model": User,
            "id_keys": ("organizer_id", "organizer"),
            "default_to_request_user": True,
            "required_on_create": True,
            "label": "Organizer",
        }
    }

    class Meta:
        model = Event
        fields = [
            "id",
            "name",
            "description",
            "location",
            "start_time",
            "end_time",
            "status",
            "quota",
            "category",
            "organizer_id",
            "organizer",
        ]
        read_only_fields = ["id", "organizer"]

    def validate(self, attrs):
        if self.instance is None:
            required_fields = [
                "name",
                "description",
                "location",
                "start_time",
                "end_time",
                "status",
                "quota",
                "category",
            ]
            missing = [f for f in required_fields if f not in attrs and f not in self.initial_data]
            if missing:
                raise serializers.ValidationError({f: "This field is required." for f in missing})

        return super().validate(attrs)

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        ret["quota"] = int(instance.quota)
        return ret


class EventPosterSerializer(serializers.ModelSerializer):
    """Event Poster serializer serializing id, image, and event foreign key as strings."""

    id = serializers.UUIDField(read_only=True)
    event = serializers.CharField(source="event_id", read_only=True)

    class Meta:
        model = EventPoster
        fields = ["id", "image", "event"]

    def to_representation(self, instance):
        return {
            "id": str(instance.id),
            "image": str(instance.image),
            "event": str(instance.event_id),
        }


class EventPosterUploadSerializer(serializers.Serializer):
    """Serializer validating Event Poster uploads (max 500 KB, valid image/* MIME type)."""

    event = serializers.CharField(required=True)
    image = serializers.FileField(required=True)

    def to_internal_value(self, data):
        data_dict = {}
        if hasattr(data, "dict"):
            data_dict = data.dict()
        elif isinstance(data, dict):
            data_dict = data.copy()
        else:
            for k, v in data.items():
                data_dict[k] = v

        if "event_id" in data_dict and "event" not in data_dict:
            data_dict["event"] = data_dict["event_id"]

        return super().to_internal_value(data_dict)

    def validate_event(self, value):
        try:
            event = Event.objects.get(id=value)
            return event
        except (Event.DoesNotExist, ValueError, TypeError):
            raise serializers.ValidationError("Event not found.")

    def validate_image(self, value):
        # 1. Size limit: 500 KB = 500 * 1024 = 512,000 bytes per Coding Standard #1
        max_size = 500 * 1024
        if value.size > max_size:
            raise serializers.ValidationError(f"File size exceeds the 500 KB limit ({value.size} bytes).")

        # 2. Content-type check
        content_type = getattr(value, "content_type", "")
        if not content_type or not content_type.startswith("image/"):
            raise serializers.ValidationError("File must have an image/* MIME type.")

        # 3. Verification using Pillow
        try:
            img = Image.open(value)
            img.verify()
            if hasattr(value, "seek"):
                value.seek(0)
        except Exception:
            raise serializers.ValidationError("Uploaded file is not a valid image.")

        return value
