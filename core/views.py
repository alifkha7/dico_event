"""Views for the core app.

Provides user and group management functionality including listing,
creating, updating and deleting users, managing groups and assigning
roles. Access is controlled via custom permission classes defined in
``core.permissions``.
"""

from django.contrib.auth.models import Group
from django.http import Http404
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiResponse, extend_schema
from loguru import logger
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication

from .models import User
from .permissions import (
    IsAdminOrSuperUser,
    IsOwnerOrAdminOrSuperUser,
    IsSuperUser,
)
from .serializers import AssignRoleSerializer, GroupSerializer, UserSerializer


class UserListCreateView(APIView):
    """List the first 10 users or create a new user."""

    authentication_classes = [JWTAuthentication]

    def get_permissions(self):
        if self.request.method == "GET":
            return [IsAuthenticated(), IsAdminOrSuperUser()]
        # POST requests are open for unauthenticated clients to allow self‑registration
        return []

    @extend_schema(
        summary="List all users (Admin/Superuser only)",
        responses={200: UserSerializer(many=True)},
        tags=["users"],
    )
    def get(self, request):
        users = User.objects.all().order_by("username")[:10]
        serializer = UserSerializer(users, many=True, context={"request": request})
        return Response({"users": serializer.data})

    @extend_schema(
        summary="Register a new user",
        request=UserSerializer,
        responses={201: UserSerializer, 400: OpenApiResponse(description="Validation error")},
        tags=["users"],
    )
    def post(self, request):
        serializer = UserSerializer(data=request.data, context={"request": request})
        if serializer.is_valid():
            serializer.save()
            logger.info("Creating a new user with data: {}", request.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserDetailView(APIView):
    """Retrieve, update or delete a user."""

    authentication_classes = [JWTAuthentication]

    def get_permissions(self):
        if self.request.method == "DELETE":
            return [IsAuthenticated(), IsAdminOrSuperUser()]
        return [IsAuthenticated(), IsOwnerOrAdminOrSuperUser()]

    def get_object(self, pk):
        try:
            user = User.objects.get(pk=pk)
            self.check_object_permissions(self.request, user)
            return user
        except User.DoesNotExist:
            logger.info("User with ID {} not found", pk)
            raise Http404

    @extend_schema(summary="Get user detail", responses={200: UserSerializer}, tags=["users"])
    def get(self, request, pk):
        user = self.get_object(pk)
        serializer = UserSerializer(user, context={"request": request})
        return Response(serializer.data)

    @extend_schema(
        summary="Update user",
        request=UserSerializer,
        responses={200: UserSerializer, 400: OpenApiResponse(description="Validation error")},
        tags=["users"],
    )
    def put(self, request, pk):
        user = self.get_object(pk)
        serializer = UserSerializer(user, data=request.data, context={"request": request})
        if serializer.is_valid():
            serializer.save()
            logger.info("Updating user with ID {} with data: {}", pk, request.data)
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        summary="Delete user (Admin/Superuser only)",
        responses={204: OpenApiResponse(description="User deleted successfully")},
        tags=["users"],
    )
    def delete(self, request, pk):
        user = self.get_object(pk)
        user.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class GroupListCreateView(APIView):
    """List or create groups. Only admins and superusers may access these endpoints."""

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, IsAdminOrSuperUser]

    @extend_schema(summary="List all groups", responses={200: GroupSerializer(many=True)}, tags=["groups"])
    def get(self, request):
        groups = Group.objects.all().order_by("name")[:10]
        serializer = GroupSerializer(groups, many=True, context={"request": request})
        return Response({"groups": serializer.data})

    @extend_schema(
        summary="Create a new group (Superuser only)",
        request=GroupSerializer,
        responses={201: GroupSerializer, 400: OpenApiResponse(description="Validation error")},
        tags=["groups"],
    )
    def post(self, request):
        serializer = GroupSerializer(data=request.data, context={"request": request})
        if serializer.is_valid():
            serializer.save()
            logger.info("Creating a new group with data: {}", request.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class GroupDetailView(APIView):
    """Retrieve, update or delete a group."""

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, IsAdminOrSuperUser]

    def get_object(self, pk):
        try:
            return Group.objects.get(pk=pk)
        except Group.DoesNotExist:
            raise Http404

    @extend_schema(summary="Get group detail", responses={200: GroupSerializer}, tags=["groups"])
    def get(self, request, pk):
        group = self.get_object(pk)
        serializer = GroupSerializer(group, context={"request": request})
        return Response(serializer.data)

    @extend_schema(
        summary="Update group",
        request=GroupSerializer,
        responses={200: GroupSerializer, 400: OpenApiResponse(description="Validation error")},
        tags=["groups"],
    )
    def put(self, request, pk):
        group = self.get_object(pk)
        serializer = GroupSerializer(group, data=request.data, context={"request": request})
        if serializer.is_valid():
            serializer.save()
            logger.info("Updating group with ID {} with data: {}", pk, request.data)
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        summary="Delete group",
        responses={204: OpenApiResponse(description="Group deleted successfully")},
        tags=["groups"],
    )
    def delete(self, request, pk):
        group = self.get_object(pk)
        group.delete()
        logger.info("Deleting group with ID {}", pk)
        return Response(status=status.HTTP_204_NO_CONTENT)


class AssignRoleView(APIView):
    """Assign a user to a group. Accessible only superusers."""

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, IsSuperUser]

    @extend_schema(
        summary="Assign a user to a role/group (Superuser only)",
        request=AssignRoleSerializer,
        responses={
            201: OpenApiResponse(description="Role assigned successfully"),
            400: OpenApiResponse(description="Validation error"),
        },
        tags=["assign-roles"],
    )
    def post(self, request):
        serializer = AssignRoleSerializer(data=request.data)
        if serializer.is_valid():
            user = get_object_or_404(User, pk=request.data["user_id"])
            group = get_object_or_404(Group, pk=request.data["group_id"])
            user.groups.add(group)
            logger.info("Assigned group {} to user {}", group.name, user.username)
            return Response({"message": "role assigned successfully"}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class HealthCheckView(APIView):
    """Health check endpoint to verify API and DB status."""

    authentication_classes = []
    permission_classes = []

    @extend_schema(
        summary="Health check — API & DB status",
        responses={
            200: OpenApiResponse(description='API healthy: {"status": "ok", "db": "healthy"}'),
            503: OpenApiResponse(description='DB unhealthy: {"status": "error", "db": "unhealthy"}'),
        },
        tags=["health"],
    )
    def get(self, request):
        try:
            # Perform a lightweight DB check
            User.objects.exists()
            return Response({"status": "ok", "db": "healthy"}, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error("Health check failed: {}", str(e))
            return Response({"status": "error", "db": "unhealthy"}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
