from django.http import Http404
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

    def get(self, request):
        payments = Payment.objects.all().order_by("registration_id")[:10]
        serializer = PaymentSerializer(payments, many=True)
        return Response({"payments": serializer.data})

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
            payment = Payment.objects.get(pk=pk)
            self.check_object_permissions(self.request, payment)
            return payment
        except Payment.DoesNotExist:
            logger.info("Payment with ID {} not found", pk)
            raise Http404

    def get(self, request, pk):
        payment = self.get_object(pk)
        serializer = PaymentSerializer(payment)
        return Response(serializer.data)

    def put(self, request, pk):
        payment = self.get_object(pk)
        serializer = PaymentSerializer(payment, data=request.data)
        if serializer.is_valid():
            serializer.save()
            logger.info("Updating payment with ID {} with data: {}", pk, request.data)
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        payment = self.get_object(pk)
        payment.delete()
        logger.info("Deleting movie with ID {}", pk)
        return Response(status=status.HTTP_204_NO_CONTENT)
