from drf_spectacular.utils import extend_schema, extend_schema_view
from loguru import logger
from rest_framework import status, viewsets
from rest_framework.response import Response

from apps.core.mixins import PartialUpdateMixin

from .models import Registration
from .permissions import RegistrationViewSetPermission
from .serializers import RegistrationSerializer

__all__ = ["RegistrationViewSet"]


@extend_schema_view(
    list=extend_schema(
        description=(
            "List all Registrations wrapped in a registrations envelope with constant O(1) query "
            "eager-loading (Admin and Superuser only)."
        )
    ),
    retrieve=extend_schema(
        description="Retrieve Registration details by ID (unauthenticated public access per ADR-0001)."
    ),
    create=extend_schema(
        description=(
            "Create a Registration for a Ticket for a User and automatically "
            "schedule a 2-hour pre-Event reminder notification."
        )
    ),
    update=extend_schema(description="Update Registration details owned by the User, Superuser, or Admin."),
    partial_update=extend_schema(
        description="Partially update Registration details owned by the User, Superuser, or Admin."
    ),
    destroy=extend_schema(description="Delete a Registration owned by the User, Superuser, or Admin."),
)
class RegistrationViewSet(PartialUpdateMixin, viewsets.ModelViewSet):
    """
    Registration ViewSet managing User Registration lifecycles and automated reminders:
    - Eager-loading ticket, ticket__event, and user for constant O(1) query performance
    - Delegation of 2-hour pre-Event reminder scheduling to RegistrationSerializer.create
    - Declarative User ownership and ADR-0001 unauthenticated detail retrieve permissions
    """

    queryset = Registration.objects.select_related("ticket", "ticket__event", "user").all().order_by("id")
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

    def perform_update(self, serializer):
        registration = serializer.save()
        logger.info(f"Registration updated successfully: (ID: {registration.id})")

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        registration_id = str(instance.id)
        self.perform_destroy(instance)
        logger.info(f"Registration deleted successfully: (ID: {registration_id})")
        return Response(status=status.HTTP_204_NO_CONTENT)
