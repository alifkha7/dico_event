from django.http import Http404
from drf_spectacular.utils import OpenApiResponse, extend_schema
from loguru import logger
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication

from core.permissions import IsAdminOrSuperUser
from tickets.models import Ticket
from tickets.serializers import TicketSerializer


class TicketListCreateView(APIView):
    """List tickets or create a new ticket."""

    authentication_classes = [JWTAuthentication]

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAuthenticated(), IsAdminOrSuperUser()]
        return [IsAuthenticated()]

    @extend_schema(summary="List all tickets", responses={200: TicketSerializer(many=True)}, tags=["tickets"])
    def get(self, request):
        tickets = Ticket.objects.select_related("event").all().order_by("name")[:10]
        serializer = TicketSerializer(tickets, many=True)
        return Response({"tickets": serializer.data})

    @extend_schema(
        summary="Create a new ticket (Admin/Superuser only)",
        request=TicketSerializer,
        responses={201: TicketSerializer, 400: OpenApiResponse(description="Validation error")},
        tags=["tickets"],
    )
    def post(self, request):
        serializer = TicketSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            logger.info("Creating a new ticket with data: {}", request.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class TicketDetailView(APIView):
    """Retrieve, update or delete a single ticket."""

    def get_object(self, pk):
        try:
            ticket = Ticket.objects.select_related("event").get(pk=pk)
            self.check_object_permissions(self.request, ticket)
            return ticket
        except Ticket.DoesNotExist:
            logger.info("Ticket with ID {} not found", pk)
            raise Http404

    authentication_classes = [JWTAuthentication]

    def get_permissions(self):
        if self.request.method != "GET":
            return [IsAuthenticated(), IsAdminOrSuperUser()]
        return [IsAuthenticated()]

    @extend_schema(summary="Get ticket detail", responses={200: TicketSerializer}, tags=["tickets"])
    def get(self, request, pk):
        ticket = self.get_object(pk)
        serializer = TicketSerializer(ticket)
        return Response(serializer.data)

    @extend_schema(
        summary="Update ticket (Admin/Superuser only)",
        request=TicketSerializer,
        responses={200: TicketSerializer, 400: OpenApiResponse(description="Validation error")},
        tags=["tickets"],
    )
    def put(self, request, pk):
        ticket = self.get_object(pk)
        serializer = TicketSerializer(ticket, data=request.data)
        if serializer.is_valid():
            serializer.save()
            logger.info("Updating ticket with ID {} with data: {}", pk, request.data)
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        summary="Delete ticket (Admin/Superuser only)",
        responses={204: OpenApiResponse(description="Ticket deleted successfully")},
        tags=["tickets"],
    )
    def delete(self, request, pk):
        ticket = self.get_object(pk)
        ticket.delete()
        logger.info("Deleting ticket with ID {}", pk)
        return Response(status=status.HTTP_204_NO_CONTENT)
