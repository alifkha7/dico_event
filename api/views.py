from loguru import logger
from rest_framework import status, viewsets
from rest_framework.response import Response

from apps.core.mixins import PartialUpdateMixin
from apps.events.views import (
    EventFilter,
    EventPagination,
    EventPostersListView,
    EventPosterUploadView,
    EventSetPagination,
    EventViewSet,
)
from apps.registrations.views import RegistrationViewSet
from apps.tickets.views import TicketViewSet
from apps.users.serializers import (
    AssignRoleSerializer,
    GroupSerializer,
    UserSerializer,
)
from apps.users.views import (
    AssignRoleView,
    CustomTokenObtainPairView,
    CustomTokenRefreshView,
    GroupViewSet,
    UserViewSet,
)

from .models import Payment
from .permissions import (
    PaymentViewSetPermission,
)
from .serializers import (
    EventPosterSerializer,
    EventPosterUploadSerializer,
    EventSerializer,
    PaymentSerializer,
    RegistrationSerializer,
    TicketSerializer,
)

__all__ = [
    "AssignRoleSerializer",
    "AssignRoleView",
    "CustomTokenObtainPairView",
    "CustomTokenRefreshView",
    "EventFilter",
    "EventPagination",
    "EventPosterSerializer",
    "EventPosterUploadSerializer",
    "EventPosterUploadView",
    "EventPostersListView",
    "EventSerializer",
    "EventSetPagination",
    "EventViewSet",
    "GroupSerializer",
    "GroupViewSet",
    "PartialUpdateMixin",
    "PaymentSerializer",
    "PaymentViewSet",
    "RegistrationSerializer",
    "RegistrationViewSet",
    "TicketSerializer",
    "TicketViewSet",
    "UserSerializer",
    "UserViewSet",
]


class PaymentViewSet(PartialUpdateMixin, viewsets.ModelViewSet):
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
