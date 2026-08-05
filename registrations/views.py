from django.http import Http404
from loguru import logger
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication

from core.permissions import IsAdminOrSuperUser
from registrations.models import Registration
from registrations.serializers import RegistrationSerializer


class RegistrationListCreateView(APIView):
    """List registrations or create a new registration."""

    authentication_classes = [JWTAuthentication]

    def get_permissions(self):
        if self.request.method == "GET":
            return [IsAuthenticated(), IsAdminOrSuperUser()]
        return [IsAuthenticated()]

    def get(self, request):
        registrations = Registration.objects.select_related("user", "ticket").all().order_by("id")[:10]
        serializer = RegistrationSerializer(registrations, many=True)
        return Response({"registrations": serializer.data})

    def post(self, request):
        serializer = RegistrationSerializer(data=request.data)
        if serializer.is_valid():
            registration = serializer.save()
            logger.info(f"Registration {registration.id} created by {registration.user.username}")
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class RegistrationDetailView(APIView):
    """Retrieve, update or delete a single registration."""

    authentication_classes = [JWTAuthentication]

    def get_permissions(self):
        if self.request.method == "PUT":
            return [IsAuthenticated(), IsAdminOrSuperUser()]
        return [IsAuthenticated()]

    def get_object(self, pk):
        try:
            registration = Registration.objects.select_related("user", "ticket").get(pk=pk)
            self.check_object_permissions(self.request, registration)
            return registration
        except Registration.DoesNotExist:
            logger.info(f"Registration with ID {pk} not found")
            raise Http404

    def get(self, request, pk):
        registration = self.get_object(pk)
        serializer = RegistrationSerializer(registration)
        return Response(serializer.data)

    def put(self, request, pk):
        registration = self.get_object(pk)
        serializer = RegistrationSerializer(
            registration,
            data=request.data,
        )
        if serializer.is_valid():
            serializer.save()
            logger.info(f"Registration {registration.id} updated by {registration.user.username}")
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        registration = self.get_object(pk)
        registration.delete()
        logger.info(f"Registration {registration.id} deleted by {registration.user.username}")
        return Response(status=status.HTTP_204_NO_CONTENT)
