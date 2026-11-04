from PIL import Image
from rest_framework import serializers
from rest_framework.validators import UniqueValidator
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from .models import Event, EventPoster

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(read_only=True)
    password = serializers.CharField(write_only=True, required=False, allow_blank=True)
    email = serializers.EmailField(
        required=False,
        validators=[UniqueValidator(queryset=User.objects.all(), message="A user with that email already exists.")]
    )

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'password']
        extra_kwargs = {
            'username': {'required': True},
            'first_name': {'required': False, 'allow_blank': True},
            'last_name': {'required': False, 'allow_blank': True},
        }

    def validate(self, attrs):
        if self.instance is None:
            # Registration/Create requires password and email
            if not attrs.get('password'):
                raise serializers.ValidationError({"password": "Password is required."})
            if not attrs.get('email'):
                raise serializers.ValidationError({"email": "Email is required."})
        return attrs

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = User(
            username=validated_data.get('username'),
            email=validated_data.get('email'),
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', ''),
        )
        user.set_password(password)
        user.save()
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        if password:
            instance.set_password(password)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        ret['id'] = str(instance.id)
        return ret


class GroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = ['id', 'name']


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
            'id',
            'name',
            'description',
            'location',
            'start_time',
            'end_time',
            'status',
            'quota',
            'category',
            'organizer_id',
            'organizer',
        ]
        read_only_fields = ['id', 'organizer']

    def validate(self, attrs):
        request = self.context.get('request')

        # Check required fields on creation
        if self.instance is None:
            required_fields = ['name', 'description', 'location', 'start_time', 'end_time', 'status', 'quota', 'category']
            missing = [f for f in required_fields if f not in attrs and f not in self.initial_data]
            if missing:
                raise serializers.ValidationError({f: "This field is required." for f in missing})

        organizer_raw = (
            self.initial_data.get('organizer_id')
            or self.initial_data.get('organizer')
            or attrs.get('organizer_id')
        )

        if organizer_raw:
            if isinstance(organizer_raw, User):
                attrs['organizer'] = organizer_raw
            else:
                try:
                    organizer_user = User.objects.get(id=organizer_raw)
                    attrs['organizer'] = organizer_user
                except Exception:
                    raise serializers.ValidationError({"organizer_id": "User not found."})
        elif self.instance is None:
            if request and request.user and request.user.is_authenticated:
                attrs['organizer'] = request.user
            else:
                raise serializers.ValidationError({"organizer_id": "Organizer is required."})

        attrs.pop('organizer_id', None)
        return attrs

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        ret['id'] = str(instance.id)
        ret['organizer'] = str(instance.organizer_id)
        ret['organizer_id'] = str(instance.organizer_id)
        ret['quota'] = int(instance.quota)
        return ret


class EventPosterSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(read_only=True)
    event = serializers.CharField(source='event_id', read_only=True)

    class Meta:
        model = EventPoster
        fields = ['id', 'image', 'event']

    def to_representation(self, instance):
        return {
            'id': str(instance.id),
            'image': instance.image,
            'event': str(instance.event_id),
        }


class EventPosterUploadSerializer(serializers.Serializer):
    event = serializers.CharField(required=True)
    image = serializers.FileField(required=True)

    def to_internal_value(self, data):
        data_dict = {}
        if hasattr(data, 'dict'):
            data_dict = data.dict()
        elif isinstance(data, dict):
            data_dict = data.copy()
        else:
            for k, v in data.items():
                data_dict[k] = v

        if 'event_id' in data_dict and 'event' not in data_dict:
            data_dict['event'] = data_dict['event_id']

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
            raise serializers.ValidationError(
                f"File size exceeds the 500 KB limit ({value.size} bytes)."
            )

        # 2. Content-type check
        content_type = getattr(value, 'content_type', '')
        if not content_type or not content_type.startswith('image/'):
            raise serializers.ValidationError("File must have an image/* MIME type.")

        # 3. Verification using Pillow
        try:
            img = Image.open(value)
            img.verify()
            if hasattr(value, 'seek'):
                value.seek(0)
        except Exception:
            raise serializers.ValidationError("Uploaded file is not a valid image.")

        return value
