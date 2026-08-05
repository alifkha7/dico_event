"""Serializers for the core app.

These serializers expose the custom user model and Django's built‑in
group model via the API. HATEOAS links are provided to illustrate
available actions for each resource.
"""

from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import Group
from rest_framework import serializers
from rest_framework.reverse import reverse

from core.models import User


class UserSerializer(serializers.HyperlinkedModelSerializer):
    """Serializer for ``User`` objects."""

    _links = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "username", "email", "first_name", "last_name", "password", "_links"]
        extra_kwargs = {"password": {"write_only": True}}

    def create(self, validated_data):
        password = validated_data.pop("password")
        validated_data["password"] = make_password(password)
        return User.objects.create(**validated_data)

    def get__links(self, obj):
        request = self.context.get("request")
        return [
            {
                "rel": "self",
                "href": reverse("user-list", request=request),
                "action": "POST",
                "types": ["application/json"],
            },
            {
                "rel": "self",
                "href": reverse("user-detail", kwargs={"pk": obj.pk}, request=request),
                "action": "GET",
                "types": ["application/json"],
            },
            {
                "rel": "self",
                "href": reverse("user-detail", kwargs={"pk": obj.pk}, request=request),
                "action": "PUT",
                "types": ["application/json"],
            },
            {
                "rel": "self",
                "href": reverse("user-detail", kwargs={"pk": obj.pk}, request=request),
                "action": "DELETE",
                "types": ["application/json"],
            },
        ]


class GroupSerializer(serializers.HyperlinkedModelSerializer):
    """Serializer for Django's built‑in ``Group`` model."""

    _links = serializers.SerializerMethodField()

    class Meta:
        model = Group
        fields = ["id", "name", "_links"]

    def get__links(self, obj):
        request = self.context.get("request")
        return [
            {
                "rel": "self",
                "href": reverse("group-list", request=request),
                "action": "POST",
                "types": ["application/json"],
            },
            {
                "rel": "self",
                "href": reverse("group-detail", kwargs={"pk": obj.pk}, request=request),
                "action": "GET",
                "types": ["application/json"],
            },
            {
                "rel": "self",
                "href": reverse("group-detail", kwargs={"pk": obj.pk}, request=request),
                "action": "PUT",
                "types": ["application/json"],
            },
            {
                "rel": "self",
                "href": reverse("group-detail", kwargs={"pk": obj.pk}, request=request),
                "action": "DELETE",
                "types": ["application/json"],
            },
        ]


class AssignRoleSerializer(serializers.Serializer):
    """Serializer used for assigning a group to a user."""

    user_id = serializers.UUIDField()
    group_id = serializers.IntegerField()
