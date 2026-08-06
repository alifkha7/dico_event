from django.http import Http404
from drf_spectacular.utils import OpenApiResponse, extend_schema
from loguru import logger
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication

from core.permissions import IsAdminOrSuperUser

from .models import Payment
from .serializers import PaymentSerializer


class PaymentListCreateView(APIView):
    """List payments or create a new payment."""

    authentication_classes = [JWTAuthentication]

    def get_permissions(self):
        if self.request.method == "GET":
            return [IsAuthenticated(), IsAdminOrSuperUser()]
        return [IsAuthenticated()]

    @extend_schema(
        summary="List all payments (Admin/Superuser only)",
        responses={200: PaymentSerializer(many=True)},
        tags=["payments"],
    )
    def get(self, request):
        payments = Payment.objects.select_related("registration").all().order_by("registration_id")[:10]
        serializer = PaymentSerializer(payments, many=True)
        return Response({"payments": serializer.data})

    @extend_schema(
        summary="Create a new payment",
        request=PaymentSerializer,
        responses={201: PaymentSerializer, 400: OpenApiResponse(description="Validation error")},
        tags=["payments"],
    )
    def post(self, request):
        serializer = PaymentSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            logger.info("Creating a new payment with data: {}", request.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PaymentDetailView(APIView):
    """Retrieve, update or delete a single payment."""

    authentication_classes = [JWTAuthentication]

    def get_permissions(self):
        if self.request.method == "GET":
            return [IsAuthenticated(), IsAdminOrSuperUser()]
        return [IsAuthenticated()]

    def get_object(self, pk):
        try:
            payment = Payment.objects.select_related("registration").get(pk=pk)
            self.check_object_permissions(self.request, payment)
            return payment
        except Payment.DoesNotExist:
            logger.info("Payment with ID {} not found", pk)
            raise Http404

    @extend_schema(
        summary="Get payment detail (Admin/Superuser only)",
        responses={200: PaymentSerializer},
        tags=["payments"],
    )
    def get(self, request, pk):
        payment = self.get_object(pk)
        serializer = PaymentSerializer(payment)
        return Response(serializer.data)

    @extend_schema(
        summary="Update payment (Admin/Superuser only)",
        request=PaymentSerializer,
        responses={200: PaymentSerializer, 400: OpenApiResponse(description="Validation error")},
        tags=["payments"],
    )
    def put(self, request, pk):
        payment = self.get_object(pk)
        serializer = PaymentSerializer(payment, data=request.data)
        if serializer.is_valid():
            serializer.save()
            logger.info("Updating payment with ID {} with data: {}", pk, request.data)
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        summary="Delete payment (Admin/Superuser only)",
        responses={204: OpenApiResponse(description="Payment deleted successfully")},
        tags=["payments"],
    )
    def delete(self, request, pk):
        payment = self.get_object(pk)
        payment.delete()
        logger.info("Deleting movie with ID {}", pk)
        return Response(status=status.HTTP_204_NO_CONTENT)
