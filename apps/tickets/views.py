from drf_spectacular.utils import extend_schema, extend_schema_view
from loguru import logger
from rest_framework import status, viewsets
from rest_framework.response import Response

from apps.core.mixins import PartialUpdateMixin

from .models import Ticket
from .permissions import TicketViewSetPermission
from .serializers import TicketSerializer

__all__ = ["TicketViewSet"]


@extend_schema_view(
    list=extend_schema(
        description="List all Tickets wrapped in a tickets envelope with constant O(1) query eager-loading."
    ),
    retrieve=extend_schema(description="Retrieve Ticket details by ID (unauthenticated public access per ADR-0001)."),
    create=extend_schema(description="Create a Ticket for an Event with non-negative price and positive quota."),
    update=extend_schema(description="Update Ticket details for an Event owned by the Organizer, Superuser, or Admin."),
    partial_update=extend_schema(
        description="Partially update Ticket details for an Event owned by the Organizer, Superuser, or Admin."
    ),
    destroy=extend_schema(description="Delete a Ticket for an Event owned by the Organizer, Superuser, or Admin."),
)
class TicketViewSet(PartialUpdateMixin, viewsets.ModelViewSet):
    queryset = Ticket.objects.select_related("event", "event__organizer").all().order_by("id")
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

    def perform_update(self, serializer):
        ticket = serializer.save()
        logger.info(f"Ticket updated successfully: '{ticket.name}' (ID: {ticket.id})")

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        ticket_id = str(instance.id)
        ticket_name = instance.name
        self.perform_destroy(instance)
        logger.info(f"Ticket deleted successfully: '{ticket_name}' (ID: {ticket_id})")
        return Response(status=status.HTTP_204_NO_CONTENT)
