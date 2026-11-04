from rest_framework import viewsets, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from loguru import logger

from .serializers import UserSerializer, GroupSerializer, AssignRoleSerializer
from .permissions import IsSuperuser, UserViewSetPermission

User = get_user_model()

class CustomTokenObtainPairView(TokenObtainPairView):
    def post(self, request, *args, **kwargs):
        username = request.data.get('username')
        response = super().post(request, *args, **kwargs)
        if response.status_code == status.HTTP_200_OK:
            logger.info(f"User '{username}' logged in successfully.")
        else:
            logger.error(f"Failed login attempt for user '{username}'.")
        return response


class CustomTokenRefreshView(TokenRefreshView):
    pass


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all().order_by('date_joined')
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

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', True)  # Always allow partial updates on PUT per spec
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        logger.info(f"User updated successfully: '{user.username}' (ID: {user.id})")
        return Response(serializer.data, status=status.HTTP_200_OK)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        user_id = str(instance.id)
        username = instance.username
        self.perform_destroy(instance)
        logger.info(f"User deleted successfully: '{username}' (ID: {user_id})")
        return Response(status=status.HTTP_204_NO_CONTENT)


class GroupViewSet(viewsets.ModelViewSet):
    queryset = Group.objects.all().order_by('id')
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

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', True)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        group = serializer.save()
        logger.info(f"Group updated successfully: '{group.name}' (ID: {group.id})")
        return Response(serializer.data, status=status.HTTP_200_OK)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        group_id = instance.id
        group_name = instance.name
        self.perform_destroy(instance)
        logger.info(f"Group deleted successfully: '{group_name}' (ID: {group_id})")
        return Response(status=status.HTTP_204_NO_CONTENT)


class AssignRoleView(APIView):
    permission_classes = [IsSuperuser]

    def post(self, request, *args, **kwargs):
        serializer = AssignRoleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user_id']
        group = serializer.validated_data['group_id']

        user.groups.add(group)
        logger.info(f"Role '{group.name}' (ID: {group.id}) assigned to user '{user.username}' (ID: {user.id})")
        return Response(
            {
                "message": f"Role '{group.name}' assigned to user '{user.username}' successfully.",
                "user_id": str(user.id),
                "group_id": group.id
            },
            status=status.HTTP_201_CREATED
        )
