from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from drf_spectacular.utils import extend_schema, inline_serializer
from loguru import logger
from rest_framework import serializers, status, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from apps.core.permissions import IsSuperuser
from apps.core.views import PartialUpdateMixin

from .permissions import UserViewSetPermission
from .serializers import (
    AssignRoleSerializer,
    CustomTokenObtainPairSerializer,
    GroupSerializer,
    UserSerializer,
)

User = get_user_model()


class CustomTokenObtainPairView(TokenObtainPairView):
    """
    Takes user credentials and returns a 3-hour JWT access token and refresh token.
    """

    serializer_class = CustomTokenObtainPairSerializer

    def post(self, request, *args, **kwargs):
        username = request.data.get("username")
        response = super().post(request, *args, **kwargs)
        if response.status_code == status.HTTP_200_OK:
            logger.info(f"User '{username}' logged in successfully.")
        else:
            logger.error(f"Failed login attempt for user '{username}'.")
        return response


class CustomTokenRefreshView(TokenRefreshView):
    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        if response.status_code == status.HTTP_200_OK:
            logger.info("Token refreshed successfully.")
        else:
            logger.error("Failed token refresh attempt.")
        return response


class UserViewSet(PartialUpdateMixin, viewsets.ModelViewSet):
    queryset = User.objects.prefetch_related("groups").all().order_by("date_joined")
    serializer_class = UserSerializer
    permission_classes = [UserViewSetPermission]

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        return Response({"users": serializer.data})

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        logger.info(f"User registered successfully: '{user.username}' (ID: {user.id})")
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def perform_update(self, serializer):
        user = serializer.save()
        logger.info(f"User updated successfully: '{user.username}' (ID: {user.id})")

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        user_id = str(instance.id)
        username = instance.username
        self.perform_destroy(instance)
        logger.info(f"User deleted successfully: '{username}' (ID: {user_id})")
        return Response(status=status.HTTP_204_NO_CONTENT)


class GroupViewSet(PartialUpdateMixin, viewsets.ModelViewSet):
    queryset = Group.objects.all().order_by("id")
    serializer_class = GroupSerializer
    permission_classes = [IsSuperuser]

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        return Response({"groups": serializer.data})

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        group = serializer.save()
        logger.info(f"Group created successfully: '{group.name}' (ID: {group.id})")
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def perform_update(self, serializer):
        group = serializer.save()
        logger.info(f"Group updated successfully: '{group.name}' (ID: {group.id})")

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        group_id = instance.id
        group_name = instance.name
        self.perform_destroy(instance)
        logger.info(f"Group deleted successfully: '{group_name}' (ID: {group_id})")
        return Response(status=status.HTTP_204_NO_CONTENT)


class AssignRoleView(APIView):
    permission_classes = [IsSuperuser]
    serializer_class = AssignRoleSerializer

    @extend_schema(
        request=AssignRoleSerializer,
        responses={
            status.HTTP_201_CREATED: inline_serializer(
                name="AssignRoleResponse",
                fields={
                    "message": serializers.CharField(),
                    "user_id": serializers.CharField(),
                    "group_id": serializers.IntegerField(),
                },
            )
        },
        description="Assign a role group to a user.",
    )
    def post(self, request, *args, **kwargs):
        serializer = AssignRoleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user_id"]
        group = serializer.validated_data["group_id"]

        user.groups.add(group)
        logger.info(f"Role '{group.name}' (ID: {group.id}) assigned to user '{user.username}' (ID: {user.id})")
        return Response(
            {
                "message": f"Role '{group.name}' assigned to user '{user.username}' successfully.",
                "user_id": str(user.id),
                "group_id": group.id,
            },
            status=status.HTTP_201_CREATED,
        )
