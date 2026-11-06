import django_filters
from django.core.exceptions import ValidationError
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from loguru import logger
from rest_framework import exceptions, filters, permissions, status, viewsets
from rest_framework.pagination import PageNumberPagination
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.mixins import PartialUpdateMixin
from apps.events.caching import CachedEventViewSetMixin
from apps.events.models import Event, EventPoster
from apps.events.permissions import EventPosterUploadPermission, EventViewSetPermission
from apps.events.serializers import (
    EventPosterSerializer,
    EventPosterUploadSerializer,
    EventSerializer,
)
from apps.events.storage import attach_event_poster

__all__ = [
    "EventFilter",
    "EventPagination",
    "EventPosterUploadView",
    "EventPostersListView",
    "EventSetPagination",
    "EventViewSet",
]


class EventPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 100

    def paginate_queryset(self, queryset, request, view=None):
        if "page" not in request.query_params and "page_size" not in request.query_params:
            return None
        return super().paginate_queryset(queryset, request, view=view)

    def get_paginated_response(self, data):
        return Response(
            {
                "count": self.page.paginator.count,
                "next": self.get_next_link(),
                "previous": self.get_previous_link(),
                "events": data,
            }
        )


EventSetPagination = EventPagination


class EventFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(field_name="name", lookup_expr="icontains")
    category = django_filters.CharFilter(field_name="category", lookup_expr="iexact")
    status = django_filters.CharFilter(field_name="status", lookup_expr="iexact")
    location = django_filters.CharFilter(field_name="location", lookup_expr="icontains")
    organizer = django_filters.UUIDFilter(field_name="organizer_id")
    organizer_id = django_filters.UUIDFilter(field_name="organizer_id")

    class Meta:
        model = Event
        fields = ["name", "category", "status", "location", "organizer", "organizer_id"]


class EventViewSet(CachedEventViewSetMixin, PartialUpdateMixin, viewsets.ModelViewSet):
    """
    ModelViewSet for managing Events.
    Inherits CachedEventViewSetMixin to delegate Redis caching, query normalization,
    X-Data-Source headers, and mutation invalidation with zero manual cache orchestration.
    """

    queryset = Event.objects.select_related("organizer").all().order_by("start_time", "id")
    serializer_class = EventSerializer
    permission_classes = [EventViewSetPermission]
    pagination_class = EventPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = EventFilter
    search_fields = ["name", "description", "location", "category"]
    ordering_fields = ["name", "start_time", "end_time", "quota", "status", "category", "id"]
    ordering = ["start_time", "id"]


class EventPosterUploadView(APIView):
    """Upload endpoint for Event Posters (max 500 KB, valid image/* MIME type)."""

    parser_classes = (MultiPartParser, FormParser)
    permission_classes = [EventPosterUploadPermission]
    serializer_class = EventPosterUploadSerializer

    @extend_schema(
        request=EventPosterUploadSerializer,
        responses={status.HTTP_201_CREATED: EventPosterSerializer},
        description="Upload an Event Poster image (image/* MIME type, max 500 KB).",
    )
    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data, context={"request": request})
        if not serializer.is_valid():
            logger.error(f"Event poster upload validation failed: {serializer.errors}")
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        event = serializer.validated_data["event"]
        image_file = serializer.validated_data["image"]

        try:
            poster = attach_event_poster(event, image_file, request.user)
        except exceptions.PermissionDenied as exc:
            return Response({"detail": str(exc.detail)}, status=status.HTTP_403_FORBIDDEN)
        except Exception as exc:
            logger.error(f"Failed to upload poster to MinIO: {exc}")
            return Response({"error": "Storage service unavailable."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        response_serializer = EventPosterSerializer(poster)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)


class EventPostersListView(APIView):
    """List all posters for a specific event."""

    permission_classes = [permissions.AllowAny]
    serializer_class = EventPosterSerializer

    @extend_schema(
        responses={status.HTTP_200_OK: EventPosterSerializer(many=True)},
        description="List all posters for a specific event.",
    )
    def get(self, request, event_id=None, *args, **kwargs):
        if event_id is None:
            event_id = request.query_params.get("event") or request.query_params.get("event_id")

        if not event_id:
            posters = EventPoster.objects.all().order_by("id")
            serializer = self.serializer_class(posters, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)

        try:
            event = Event.objects.get(id=event_id)
        except (Event.DoesNotExist, ValueError, ValidationError):
            return Response({"detail": "Event not found."}, status=status.HTTP_404_NOT_FOUND)

        posters = EventPoster.objects.filter(event=event).order_by("id")
        serializer = self.serializer_class(posters, many=True)
        logger.info(f"Retrieved {len(serializer.data)} posters for event '{event.name}' (ID: {event.id})")
        return Response(serializer.data, status=status.HTTP_200_OK)
