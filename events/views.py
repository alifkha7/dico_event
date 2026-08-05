import json
import os
import tempfile

from django.core.cache import cache
from django.http import Http404
from django.shortcuts import get_object_or_404
from loguru import logger
from minio import Minio
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication

from core.permissions import IsAdminOrOrganizerOrSuperUser, IsAdminOrSuperUser, IsEventOwnerOrAdminOrSuperUser

from .models import Event
from .serializers import EventPosterSerializer, EventSerializer


def get_minio_client():
    return Minio(
        endpoint=os.getenv("MINIO_ENDPOINT_URL"),
        access_key=os.getenv("MINIO_ACCESS_KEY"),
        secret_key=os.getenv("MINIO_SECRET_KEY"),
        secure=False,
    )


bucket_name = os.getenv("MINIO_BUCKET_NAME")
CACHE_KEY_LIST = "event_list"
CACHE_KEY_DETAIL = "event_detail_{}"


class EventListCreateView(APIView):
    """List events or create a new event."""

    authentication_classes = [JWTAuthentication]

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAuthenticated(), IsAdminOrOrganizerOrSuperUser()]
        return [IsAuthenticated()]

    def get(self, request):
        events = cache.get(CACHE_KEY_LIST)

        if not events:
            print("Data diambil dari database...")
            data = Event.objects.all().order_by("start_time")[:10]
            cache.get(CACHE_KEY_LIST)
            serializer = EventSerializer(data, many=True, context={"request": request})

            events_data = json.dumps(serializer.data)

            cache.set(CACHE_KEY_LIST, events_data, timeout=60 * 60)

            events = events_data
            data_source = "database"
        else:
            print("Data diambil dari cache...")
            data_source = "cache"

        response = Response({"events": json.loads(events)})
        response["X-Data-Source"] = data_source
        return response

    def post(self, request):
        serializer = EventSerializer(data=request.data, context={"request": request})
        if serializer.is_valid():
            serializer.save()
            cache.delete(CACHE_KEY_LIST)
            logger.info("Creating a new event with data: {}", request.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class EventDetailView(APIView):
    """Retrieve, update or delete a single event."""

    authentication_classes = [JWTAuthentication]

    def get_permissions(self):
        if self.request.method != "GET":
            return [IsAuthenticated(), IsEventOwnerOrAdminOrSuperUser()]
        return [IsAuthenticated()]

    def get_object(self, pk):
        try:
            event = Event.objects.get(pk=pk)
            self.check_object_permissions(self.request, event)
            return event
        except Event.DoesNotExist:
            logger.info("Event with ID {} not found", pk)
            raise Http404

    def get(self, request, pk):
        cache_key = CACHE_KEY_DETAIL.format(pk)
        event = cache.get(cache_key)

        if not event:
            data = Event.objects.get(pk=pk)
            serializer = EventSerializer(data, context={"request": request})

            event_data = json.dumps(serializer.data)

            cache.set(cache_key, event_data, timeout=60 * 60)

            event = event_data
            data_source = "database"
        else:
            print("Data diambil dari cache...")
            data_source = "cache"

        response = Response(json.loads(event))
        response["X-Data-Source"] = data_source
        return response

    def put(self, request, pk):
        event = self.get_object(pk)
        serializer = EventSerializer(event, data=request.data, context={"request": request})
        if serializer.is_valid():
            serializer.save()
            cache.delete(CACHE_KEY_LIST)
            cache.delete(CACHE_KEY_DETAIL.format(pk))
            logger.info("Updating event with ID {} with data: {}", pk, request.data)
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        event = self.get_object(pk)
        event.delete()
        cache.delete(CACHE_KEY_LIST)
        cache.delete(CACHE_KEY_DETAIL.format(pk))
        logger.info("Deleting event with ID {}", pk)
        return Response(status=status.HTTP_204_NO_CONTENT)


class EventPosterView(APIView):
    authentication_classes = [JWTAuthentication]
    parser_classes = [MultiPartParser, FormParser]

    def get_permissions(self):
        return [IsAuthenticated(), IsAdminOrSuperUser()]

    def post(self, request):
        serializer = EventPosterSerializer(data=request.data, context={"request": request})
        file = request.data.get("image")

        if serializer.is_valid():
            serializer.save()

            with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                for chunk in file.chunks():
                    temp_file.write(chunk)
                temp_file_path = temp_file.name

            try:
                object_name = f"{serializer.instance.image.name}"
                client = get_minio_client()

                if not client.bucket_exists(bucket_name):
                    client.make_bucket(bucket_name)

                client.fput_object(bucket_name, object_name, temp_file_path, content_type=file.content_type)
            except Exception as e:
                logger.error(f"Upload to Minio failed: {str(e)}")
                return Response(
                    {"error": f"Upload to Minio failed: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            finally:
                os.remove(temp_file_path)

            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class EventPosterDetailView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        event = get_object_or_404(Event, pk=pk)
        images = event.eventimage_set.all()

        serialized_images = []
        for image in images:
            client = get_minio_client()
            presigned_url = client.presigned_get_object(
                bucket_name, image.image.name, response_headers={"response-content-type": "image/jpeg"}
            )
            serialized_images.append({"id": image.id, "url": presigned_url})

        return Response(serialized_images)
