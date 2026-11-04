import django_filters
from django.core.exceptions import ValidationError
from rest_framework import viewsets, status, filters, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.pagination import PageNumberPagination
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from loguru import logger

from .models import Event, Ticket, Registration, Payment, EventPoster
from .serializers import (
    UserSerializer,
    GroupSerializer,
    AssignRoleSerializer,
    EventSerializer,
    TicketSerializer,
    RegistrationSerializer,
    PaymentSerializer,
    EventPosterSerializer,
    EventPosterUploadSerializer,
)
from .permissions import (
    IsSuperuser,
    UserViewSetPermission,
    EventViewSetPermission,
    TicketViewSetPermission,
    RegistrationViewSetPermission,
    PaymentViewSetPermission,
    CanUploadPosterPermission,
)
from .caching import (
    get_cached_event_detail,
    set_cached_event_detail,
    get_cached_event_list,
    set_cached_event_list,
    invalidate_event_list_cache,
    invalidate_all_event_caches,
)
from . import storage

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
        query_string = request.META.get('QUERY_STRING', '')
        cached_data = get_cached_event_list(query_string)
        if cached_data is not None:
            logger.info(f"Serving events list from cache (query: '{query_string}').")
            response = Response(cached_data, status=status.HTTP_200_OK)
            response['X-Data-Source'] = 'cache'
            return response

        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            logger.info(f"Listing events from database (paginated): count={self.paginator.page.paginator.count}")
            paginated_response = self.get_paginated_response(serializer.data)
            set_cached_event_list(query_string, paginated_response.data)
            paginated_response['X-Data-Source'] = 'database'
            return paginated_response

        serializer = self.get_serializer(queryset, many=True)
        logger.info(f"Listing events from database: count={len(serializer.data)}")
        data = {"events": serializer.data}
        set_cached_event_list(query_string, data)
        response = Response(data, status=status.HTTP_200_OK)
        response['X-Data-Source'] = 'database'
        return response

    def retrieve(self, request, *args, **kwargs):
        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field
        pk = kwargs.get(lookup_url_kwarg, kwargs.get('pk'))
        cached_data = get_cached_event_detail(pk)
        if cached_data is not None:
            logger.info(f"Serving event detail from cache (ID: {pk}).")
            response = Response(cached_data, status=status.HTTP_200_OK)
            response['X-Data-Source'] = 'cache'
            return response

        instance = self.get_object()
        serializer = self.get_serializer(instance)
        set_cached_event_detail(pk, serializer.data)
        logger.info(f"Retrieved event from database: '{instance.name}' (ID: {instance.id})")
        response = Response(serializer.data, status=status.HTTP_200_OK)
        response['X-Data-Source'] = 'database'
        return response

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        event = serializer.save()
        invalidate_event_list_cache()
        username = request.user.username if request.user and request.user.is_authenticated else 'anonymous'
        logger.info(f"Event created successfully: '{event.name}' (ID: {event.id}) by user '{username}'")
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', True)  # Always allow partial updates on PUT per spec
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        event = serializer.save()
        invalidate_all_event_caches(pk=str(event.id))
        username = request.user.username if request.user and request.user.is_authenticated else 'anonymous'
        logger.info(f"Event updated successfully: '{event.name}' (ID: {event.id}) by user '{username}'")
        return Response(serializer.data, status=status.HTTP_200_OK)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        event_id = str(instance.id)
        event_name = instance.name
        self.perform_destroy(instance)
        invalidate_all_event_caches(pk=event_id)
        username = request.user.username if request.user and request.user.is_authenticated else 'anonymous'
        logger.info(f"Event deleted successfully: '{event_name}' (ID: {event_id}) by user '{username}'")
        return Response(status=status.HTTP_204_NO_CONTENT)


class TicketViewSet(viewsets.ModelViewSet):
    queryset = Ticket.objects.all().order_by('id')
    serializer_class = TicketSerializer
    permission_classes = [TicketViewSetPermission]

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        logger.info(f"Listing tickets: count={len(serializer.data)}")
        return Response({"tickets": serializer.data})

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        logger.info(f"Retrieved ticket: '{instance.name}' (ID: {instance.id})")
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        ticket = serializer.save()
        logger.info(f"Ticket created successfully: '{ticket.name}' (ID: {ticket.id})")
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', True)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        ticket = serializer.save()
        logger.info(f"Ticket updated successfully: '{ticket.name}' (ID: {ticket.id})")
        return Response(serializer.data, status=status.HTTP_200_OK)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        ticket_id = str(instance.id)
        ticket_name = instance.name
        self.perform_destroy(instance)
        logger.info(f"Ticket deleted successfully: '{ticket_name}' (ID: {ticket_id})")
        return Response(status=status.HTTP_204_NO_CONTENT)


class RegistrationViewSet(viewsets.ModelViewSet):
    queryset = Registration.objects.all().order_by('id')
    serializer_class = RegistrationSerializer
    permission_classes = [RegistrationViewSetPermission]

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        logger.info(f"Listing registrations: count={len(serializer.data)}")
        return Response({"registrations": serializer.data})

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        logger.info(f"Retrieved registration: (ID: {instance.id})")
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        registration = serializer.save()
        logger.info(f"Registration created successfully: (ID: {registration.id})")
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', True)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        registration = serializer.save()
        logger.info(f"Registration updated successfully: (ID: {registration.id})")
        return Response(serializer.data, status=status.HTTP_200_OK)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        reg_id = str(instance.id)
        self.perform_destroy(instance)
        logger.info(f"Registration deleted successfully: (ID: {reg_id})")
        return Response(status=status.HTTP_204_NO_CONTENT)


class PaymentViewSet(viewsets.ModelViewSet):
    queryset = Payment.objects.all().order_by('id')
    serializer_class = PaymentSerializer
    permission_classes = [PaymentViewSetPermission]

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        logger.info(f"Listing payments: count={len(serializer.data)}")
        return Response({"payments": serializer.data})

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        logger.info(f"Retrieved payment: (ID: {instance.id})")
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payment = serializer.save()
        logger.info(f"Payment created successfully: (ID: {payment.id}, Status: {payment.payment_status})")
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', True)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        payment = serializer.save()
        logger.info(f"Payment updated successfully: (ID: {payment.id}, Status: {payment.payment_status})")
        return Response(serializer.data, status=status.HTTP_200_OK)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        payment_id = str(instance.id)
        self.perform_destroy(instance)
        logger.info(f"Payment deleted successfully: (ID: {payment_id})")
        return Response(status=status.HTTP_204_NO_CONTENT)


class EventPosterUploadView(APIView):
    parser_classes = (MultiPartParser, FormParser)
    permission_classes = [CanUploadPosterPermission]

    def post(self, request, *args, **kwargs):
        serializer = EventPosterUploadSerializer(data=request.data, context={'request': request})
        if not serializer.is_valid():
            logger.error(f"Event poster upload validation failed: {serializer.errors}")
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        event = serializer.validated_data['event']
        image_file = serializer.validated_data['image']

        try:
            stored_filename = storage.upload_poster_to_minio(
                file_obj=image_file,
                filename=image_file.name,
                content_type=getattr(image_file, 'content_type', 'image/jpeg')
            )
        except Exception as exc:
            logger.error(f"Failed to upload poster to MinIO: {exc}")
            return Response({"error": "Storage service unavailable."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        poster = EventPoster.objects.create(
            event=event,
            image=stored_filename,
        )
        username = request.user.username if request.user and request.user.is_authenticated else 'anonymous'
        logger.info(
            f"Poster uploaded successfully for event '{event.name}' (ID: {event.id}): '{stored_filename}' "
            f"(Poster ID: {poster.id}) by user '{username}'"
        )
        return Response(
            {
                "id": str(poster.id),
                "image": poster.image,
                "event": str(poster.event_id),
            },
            status=status.HTTP_201_CREATED
        )


class EventPostersListView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, event_id, *args, **kwargs):
        try:
            event = Event.objects.get(id=event_id)
        except (Event.DoesNotExist, ValueError, ValidationError):
            return Response({"detail": "Event not found."}, status=status.HTTP_404_NOT_FOUND)

        posters = EventPoster.objects.filter(event=event).order_by('id')
        data = [
            {
                "id": str(p.id),
                "image": p.image,
                "event": str(p.event_id),
            }
            for p in posters
        ]
        logger.info(f"Retrieved {len(data)} posters for event '{event.name}' (ID: {event.id})")
        return Response(data, status=status.HTTP_200_OK)
