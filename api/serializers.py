from rest_framework import serializers
from rest_framework.validators import UniqueValidator
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from .models import Event, Ticket, Registration, Payment

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


class TicketSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(read_only=True)
    price = serializers.IntegerField(required=False)
    quota = serializers.IntegerField(required=False)
    event_id = serializers.CharField(required=False, write_only=False)

    class Meta:
        model = Ticket
        fields = [
            'id',
            'event',
            'event_id',
            'name',
            'price',
            'sales_start',
            'sales_end',
            'quota',
        ]
        read_only_fields = ['id', 'event']

    def validate(self, attrs):
        if self.instance is None:
            required_fields = ['name', 'price', 'sales_start', 'sales_end', 'quota']
            missing = [f for f in required_fields if f not in attrs and f not in self.initial_data]
            if missing:
                raise serializers.ValidationError({f: "This field is required." for f in missing})

        event_raw = (
            self.initial_data.get('event_id')
            or self.initial_data.get('event')
            or attrs.get('event_id')
        )

        if event_raw:
            if isinstance(event_raw, Event):
                attrs['event'] = event_raw
            else:
                try:
                    event_instance = Event.objects.get(id=event_raw)
                    attrs['event'] = event_instance
                except Exception:
                    raise serializers.ValidationError({"event_id": "Event not found."})
        elif self.instance is None:
            raise serializers.ValidationError({"event_id": "Event is required."})

        attrs.pop('event_id', None)
        return attrs

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        ret['id'] = str(instance.id)
        ret['event'] = str(instance.event_id)
        ret['event_id'] = str(instance.event_id)
        ret['name'] = str(instance.name)
        ret['price'] = int(instance.price)
        ret['quota'] = int(instance.quota)
        return ret


class RegistrationSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(read_only=True)
    ticket_id = serializers.CharField(required=False, write_only=False)
    user_id = serializers.CharField(required=False, write_only=False)

    class Meta:
        model = Registration
        fields = ['id', 'ticket', 'ticket_id', 'user', 'user_id']
        read_only_fields = ['id', 'ticket', 'user']

    def validate(self, attrs):
        request = self.context.get('request')

        ticket_raw = (
            self.initial_data.get('ticket_id')
            or self.initial_data.get('ticket')
            or attrs.get('ticket_id')
        )
        if ticket_raw:
            if isinstance(ticket_raw, Ticket):
                attrs['ticket'] = ticket_raw
            else:
                try:
                    ticket_obj = Ticket.objects.get(id=ticket_raw)
                    attrs['ticket'] = ticket_obj
                except Exception:
                    raise serializers.ValidationError({"ticket_id": "Ticket not found."})
        elif self.instance is None:
            raise serializers.ValidationError({"ticket_id": "Ticket is required."})

        user_raw = (
            self.initial_data.get('user_id')
            or self.initial_data.get('user')
            or attrs.get('user_id')
        )
        if user_raw:
            if isinstance(user_raw, User):
                attrs['user'] = user_raw
            else:
                try:
                    user_obj = User.objects.get(id=user_raw)
                    attrs['user'] = user_obj
                except Exception:
                    raise serializers.ValidationError({"user_id": "User not found."})
        elif self.instance is None:
            if request and request.user and request.user.is_authenticated:
                attrs['user'] = request.user
            else:
                raise serializers.ValidationError({"user_id": "User is required."})

        attrs.pop('ticket_id', None)
        attrs.pop('user_id', None)
        return attrs

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        ret['id'] = str(instance.id)
        ret['ticket'] = str(instance.ticket_id)
        ret['ticket_id'] = str(instance.ticket_id)
        ret['user'] = str(instance.user_id)
        ret['user_id'] = str(instance.user_id)
        return ret


class PaymentSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(read_only=True)
    registration_id = serializers.CharField(required=False, write_only=False)
    amount_paid = serializers.IntegerField(required=False)

    class Meta:
        model = Payment
        fields = [
            'id',
            'registration',
            'registration_id',
            'payment_method',
            'payment_status',
            'amount_paid',
        ]
        read_only_fields = ['id', 'registration']

    def validate(self, attrs):
        if self.instance is None:
            required_fields = ['payment_method', 'payment_status', 'amount_paid']
            missing = [f for f in required_fields if f not in attrs and f not in self.initial_data]
            if missing:
                raise serializers.ValidationError({f: "This field is required." for f in missing})

        reg_raw = (
            self.initial_data.get('registration_id')
            or self.initial_data.get('registration')
            or attrs.get('registration_id')
        )
        if reg_raw:
            if isinstance(reg_raw, Registration):
                attrs['registration'] = reg_raw
            else:
                try:
                    reg_obj = Registration.objects.get(id=reg_raw)
                    attrs['registration'] = reg_obj
                except Exception:
                    raise serializers.ValidationError({"registration_id": "Registration not found."})
        elif self.instance is None:
            raise serializers.ValidationError({"registration_id": "Registration is required."})

        # ADR-0001: Normalize 'completed' (case-insensitive) to 'Completed'
        status_val = attrs.get('payment_status') or self.initial_data.get('payment_status')
        if status_val is not None and str(status_val).strip().lower() == 'completed':
            attrs['payment_status'] = 'Completed'

        attrs.pop('registration_id', None)
        return attrs

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        ret['id'] = str(instance.id)
        ret['registration'] = str(instance.registration_id)
        ret['registration_id'] = str(instance.registration_id)
        ret['payment_method'] = str(instance.payment_method)
        if instance.payment_status and instance.payment_status.strip().lower() == 'completed':
            ret['payment_status'] = 'Completed'
        else:
            ret['payment_status'] = str(instance.payment_status)
        ret['amount_paid'] = int(instance.amount_paid)
        return ret
