from django.db import transaction
from rest_framework import serializers
from rest_framework.reverse import reverse

from core.models import User

from .models import Registration, Ticket


class RegistrationSerializer(serializers.HyperlinkedModelSerializer):
    _links = serializers.SerializerMethodField()
    ticket = serializers.CharField(source="ticket.name", read_only=True)
    user = serializers.CharField(source="user.username", read_only=True)

    ticket_id = serializers.PrimaryKeyRelatedField(queryset=Ticket.objects.all(), write_only=True, source="ticket")

    user_id = serializers.PrimaryKeyRelatedField(queryset=User.objects.all(), write_only=True, source="user")

    class Meta:
        model = Registration
        fields = ["id", "ticket", "user", "ticket_id", "user_id", "_links"]

    def get__links(self, obj):
        request = self.context.get("request")
        return [
            {
                "rel": "self",
                "href": reverse("registration-list", request=request),
                "action": "POST",
                "types": ["application/json"],
            },
            {
                "rel": "self",
                "href": reverse("registration-detail", kwargs={"pk": obj.pk}, request=request),
                "action": "GET",
                "types": ["application/json"],
            },
            {
                "rel": "self",
                "href": reverse("registration-detail", kwargs={"pk": obj.pk}, request=request),
                "action": "PUT",
                "types": ["application/json"],
            },
            {
                "rel": "self",
                "href": reverse("registration-detail", kwargs={"pk": obj.pk}, request=request),
                "action": "DELETE",
                "types": ["application/json"],
            },
        ]

    def create(self, validated_data):
        with transaction.atomic():
            ticket = validated_data["ticket"]
            # Lock the ticket row to prevent race conditions during high concurrency
            ticket = Ticket.objects.select_for_update().get(id=ticket.id)

            if ticket.quota <= 0:
                raise serializers.ValidationError({"ticket": "This ticket is sold out."})

            ticket.quota -= 1
            ticket.save()

            return super().create(validated_data)
