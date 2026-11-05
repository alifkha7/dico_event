from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from PIL import Image
from rest_framework import serializers
from rest_framework.validators import UniqueValidator

from .models import Event, EventPoster, Payment, Registration, Ticket

User = get_user_model()


def _resolve_foreign_key(
    attrs,
    initial_data,
    instance,
    field_name,
    id_keys,
    model_class,
    default_fn=None,
    required_on_create=True,
    label=None,
):
    """
    Resolve a foreign key from initial_data or attrs into a model instance.
    Eliminates duplicated FK resolution boilerplate across serializers.
    """
    raw_val = None
    for k in id_keys:
        val = initial_data.get(k) if initial_data else None
        if val is None and attrs:
            val = attrs.get(k)
        if val is not None:
            raw_val = val
            break

    primary_id_key = id_keys[0]
    display_label = label or model_class.__name__

    if raw_val is not None:
        if isinstance(raw_val, model_class):
            attrs[field_name] = raw_val
        else:
            try:
                if model_class is Ticket:
                    attrs[field_name] = Ticket.objects.select_related("event").get(id=raw_val)
                else:
                    attrs[field_name] = model_class.objects.get(id=raw_val)
            except Exception:
                raise serializers.ValidationError({primary_id_key: f"{model_class.__name__} not found."})
    elif instance is None and required_on_create:
        default_val = default_fn() if callable(default_fn) else None
        if default_val is not None:
            attrs[field_name] = default_val
        else:
            raise serializers.ValidationError({primary_id_key: f"{display_label} is required."})

    for k in id_keys:
        if k != field_name:
            attrs.pop(k, None)


class UserSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(read_only=True)
    password = serializers.CharField(write_only=True, required=False, allow_blank=True)
    email = serializers.EmailField(
        required=False,
        validators=[UniqueValidator(queryset=User.objects.all(), message="A user with that email already exists.")],
    )

    class Meta:
        model = User
        fields = ["id", "username", "email", "first_name", "last_name", "password"]
        extra_kwargs = {
            "username": {"required": True},
            "first_name": {"required": False, "allow_blank": True},
            "last_name": {"required": False, "allow_blank": True},
        }

    def validate(self, attrs):
        if self.instance is None:
            # Registration/Create requires password and email
            if not attrs.get("password"):
                raise serializers.ValidationError({"password": "Password is required."})
            if not attrs.get("email"):
                raise serializers.ValidationError({"email": "Email is required."})
        return attrs

    def create(self, validated_data):
        password = validated_data.pop("password")
        user = User(
            username=validated_data.get("username"),
            email=validated_data.get("email"),
            first_name=validated_data.get("first_name", ""),
            last_name=validated_data.get("last_name", ""),
        )
        user.set_password(password)
        user.save()
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop("password", None)
        if password:
            instance.set_password(password)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        ret["id"] = str(instance.id)
        return ret


class GroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = ["id", "name"]


class AssignRoleSerializer(serializers.Serializer):
    user_id = serializers.UUIDField(required=True)
    group_id = serializers.IntegerField(required=True)

    def validate_user_id(self, value):
        try:
            user = User.objects.get(id=value)
            return user
        except User.DoesNotExist:
            raise serializers.ValidationError("User not found.")

    def validate_group_id(self, value):
        try:
            group = Group.objects.get(id=value)
            return group
        except Group.DoesNotExist:
            raise serializers.ValidationError("Group not found.")


class EventSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(read_only=True)
    quota = serializers.IntegerField(required=False)
    organizer_id = serializers.CharField(required=False, write_only=False)

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
        request = self.context.get("request")

        # Check required fields on creation
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

        _resolve_foreign_key(
            attrs=attrs,
            initial_data=self.initial_data,
            instance=self.instance,
            field_name="organizer",
            id_keys=["organizer_id", "organizer"],
            model_class=User,
            default_fn=lambda: request.user if request and request.user and request.user.is_authenticated else None,
            required_on_create=True,
            label="Organizer",
        )
        return attrs

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        ret["id"] = str(instance.id)
        ret["organizer"] = str(instance.organizer_id)
        ret["organizer_id"] = str(instance.organizer_id)
        ret["quota"] = int(instance.quota)
        return ret


class TicketSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(read_only=True)
    price = serializers.IntegerField(required=False)
    quota = serializers.IntegerField(required=False)
    event_id = serializers.CharField(required=False, write_only=False)

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

        _resolve_foreign_key(
            attrs=attrs,
            initial_data=self.initial_data,
            instance=self.instance,
            field_name="event",
            id_keys=["event_id", "event"],
            model_class=Event,
            required_on_create=True,
        )
        return attrs

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        ret["id"] = str(instance.id)
        ret["event"] = str(instance.event_id)
        ret["event_id"] = str(instance.event_id)
        ret["name"] = str(instance.name)
        ret["price"] = int(instance.price)
        ret["quota"] = int(instance.quota)
        return ret


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


class EventPosterSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(read_only=True)
    event = serializers.CharField(source="event_id", read_only=True)

    class Meta:
        model = EventPoster
        fields = ["id", "image", "event"]

    def to_representation(self, instance):
        return {
            "id": str(instance.id),
            "image": instance.image,
            "event": str(instance.event_id),
        }


class EventPosterUploadSerializer(serializers.Serializer):
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
        # 1. Size limit: 500 KB = 500 * 1024 = 512,000 bytes
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
