from drf_spectacular.utils import extend_schema, extend_schema_view
from loguru import logger
from rest_framework import status, viewsets
from rest_framework.response import Response

from apps.core.mixins import PartialUpdateMixin

from .models import Payment
from .permissions import PaymentViewSetPermission
from .serializers import PaymentSerializer

__all__ = ["PaymentViewSet"]


@extend_schema_view(
    list=extend_schema(
        description=(
            "List all Payments wrapped in a payments envelope with constant O(1) query "
            "eager-loading (Admin and Superuser only)."
        )
    ),
    retrieve=extend_schema(description="Retrieve Payment details by ID (unauthenticated public access per ADR-0001)."),
    create=extend_schema(
        description=("Create a Payment settlement for a Registration by an authenticated User, Admin, or Superuser.")
    ),
    update=extend_schema(
        description=(
            "Update Payment details with case-insensitive 'completed' status normalized to 'Completed' (ADR-0001)."
        )
    ),
    partial_update=extend_schema(
        description=(
            "Partially update Payment details with case-insensitive 'completed' "
            "status normalized to 'Completed' (ADR-0001)."
        )
    ),
    destroy=extend_schema(description="Delete a Payment owned by the User, Superuser, or Admin."),
)
class PaymentViewSet(PartialUpdateMixin, viewsets.ModelViewSet):
    """
    Payment ViewSet managing financial settlements and status normalization:
    - Eager-loading registration and registration__user for constant O(1) query performance
    - Normalization of case-insensitive 'completed' to 'Completed' (ADR-0001)
    - Declarative User ownership and ADR-0001 unauthenticated detail retrieve permissions
    """

    queryset = Payment.objects.select_related("registration", "registration__user").all().order_by("id")
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

    def perform_update(self, serializer):
        payment = serializer.save()
        logger.info(f"Payment updated successfully: (ID: {payment.id}, Status: {payment.payment_status})")

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        payment_id = str(instance.id)
        self.perform_destroy(instance)
        logger.info(f"Payment deleted successfully: (ID: {payment_id})")
        return Response(status=status.HTTP_204_NO_CONTENT)
