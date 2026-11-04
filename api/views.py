import django_filters
from rest_framework import viewsets, status, filters
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from loguru import logger

from .models import Event
from .serializers import (
    UserSerializer,
    GroupSerializer,
    AssignRoleSerializer,
    EventSerializer,
)
from .permissions import (
    IsSuperuser,
    UserViewSetPermission,
    EventViewSetPermission,
)

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


class EventPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100

    def paginate_queryset(self, queryset, request, view=None):
        if 'page' not in request.query_params and 'page_size' not in request.query_params:
            return None
        return super().paginate_queryset(queryset, request, view=view)

    def get_paginated_response(self, data):
        return Response({
            'count': self.page.paginator.count,
            'next': self.get_next_link(),
            'previous': self.get_previous_link(),
            'events': data
        })


class EventFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(field_name='name', lookup_expr='icontains')
    category = django_filters.CharFilter(field_name='category', lookup_expr='iexact')
    status = django_filters.CharFilter(field_name='status', lookup_expr='iexact')
    location = django_filters.CharFilter(field_name='location', lookup_expr='icontains')
    organizer = django_filters.UUIDFilter(field_name='organizer_id')
    organizer_id = django_filters.UUIDFilter(field_name='organizer_id')

    class Meta:
        model = Event
        fields = ['name', 'category', 'status', 'location', 'organizer', 'organizer_id']


class EventViewSet(viewsets.ModelViewSet):
    queryset = Event.objects.all().order_by('start_time', 'id')
    serializer_class = EventSerializer
    permission_classes = [EventViewSetPermission]
    pagination_class = EventPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = EventFilter
    search_fields = ['name', 'description', 'location', 'category']
    ordering_fields = ['name', 'start_time', 'end_time', 'quota', 'status', 'category', 'id']
    ordering = ['start_time', 'id']

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            logger.info(f"Listing events (paginated): count={self.paginator.page.paginator.count}")
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        logger.info(f"Listing events: count={len(serializer.data)}")
        return Response({"events": serializer.data})

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        logger.info(f"Retrieved event: '{instance.name}' (ID: {instance.id})")
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        event = serializer.save()
        username = request.user.username if request.user and request.user.is_authenticated else 'anonymous'
        logger.info(f"Event created successfully: '{event.name}' (ID: {event.id}) by user '{username}'")
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', True)  # Always allow partial updates on PUT per spec
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        event = serializer.save()
        username = request.user.username if request.user and request.user.is_authenticated else 'anonymous'
        logger.info(f"Event updated successfully: '{event.name}' (ID: {event.id}) by user '{username}'")
        return Response(serializer.data, status=status.HTTP_200_OK)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        event_id = str(instance.id)
        event_name = instance.name
        self.perform_destroy(instance)
        username = request.user.username if request.user and request.user.is_authenticated else 'anonymous'
        logger.info(f"Event deleted successfully: '{event_name}' (ID: {event_id}) by user '{username}'")
        return Response(status=status.HTTP_204_NO_CONTENT)
