import os
import uuid
from datetime import timedelta
from urllib.parse import urlparse

from django.conf import settings
from loguru import logger
from minio import Minio
from PIL import Image
from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied

from apps.core.permissions import is_admin_user
from apps.events.models import EventPoster

__all__ = [
    "attach_event_poster",
    "generate_presigned_poster_url",
    "get_minio_client",
    "get_public_minio_client",
    "parse_minio_endpoint",
    "upload_poster_to_minio",
    "validate_poster_image",
]


def parse_minio_endpoint(endpoint_url: str, default_secure: bool = False) -> tuple[str, bool]:
    """
    Parse a MinIO endpoint URL into (endpoint, secure).
    Handles endpoints with schemes (http://, https://) or raw host:port strings.
    """
    if not endpoint_url:
        return "localhost:9000", default_secure

    endpoint_str = endpoint_url.strip()
    if endpoint_str.startswith("http://"):
        parsed = urlparse(endpoint_str)
        return parsed.netloc or parsed.path, False
    elif endpoint_str.startswith("https://"):
        parsed = urlparse(endpoint_str)
        return parsed.netloc or parsed.path, True
    else:
        # Raw host or host:port
        clean = endpoint_str.rstrip("/")
        return clean, default_secure


def get_minio_client() -> Minio:
    """
    Instantiate and return an official MinIO SDK client configured from Django settings.
    Settings strictly read:
    - MINIO_ENDPOINT_URL
    - MINIO_ACCESS_KEY
    - MINIO_SECRET_KEY
    - MINIO_USE_SSL
    """
    endpoint_url = getattr(settings, "MINIO_ENDPOINT_URL", "localhost:9000")
    default_secure = getattr(settings, "MINIO_USE_SSL", False)
    endpoint, secure = parse_minio_endpoint(endpoint_url, default_secure=default_secure)

    access_key = getattr(settings, "MINIO_ACCESS_KEY", "minioadmin")
    secret_key = getattr(settings, "MINIO_SECRET_KEY", "minioadmin")

    client = Minio(
        endpoint=endpoint,
        access_key=access_key,
        secret_key=secret_key,
        secure=secure,
    )
    return client


def get_public_minio_client() -> Minio:
    """
    Instantiate and return a MinIO client configured for public presigned URL generation.
    Reads:
    - MINIO_PUBLIC_ENDPOINT_URL (falling back to MINIO_ENDPOINT_URL)
    - MINIO_ACCESS_KEY
    - MINIO_SECRET_KEY
    - MINIO_USE_SSL
    Region defaults explicitly to 'us-east-1' to enable pure local signing without network lookups.
    """
    public_url = getattr(settings, "MINIO_PUBLIC_ENDPOINT_URL", "").strip() or getattr(
        settings, "MINIO_ENDPOINT_URL", "localhost:9000"
    )
    default_secure = getattr(settings, "MINIO_USE_SSL", False)
    endpoint, secure = parse_minio_endpoint(public_url, default_secure=default_secure)

    access_key = getattr(settings, "MINIO_ACCESS_KEY", "minioadmin")
    secret_key = getattr(settings, "MINIO_SECRET_KEY", "minioadmin")

    return Minio(
        endpoint=endpoint,
        access_key=access_key,
        secret_key=secret_key,
        secure=secure,
        region="us-east-1",
    )


def generate_presigned_poster_url(image_key: str | None) -> str | None:
    """
    Generate a time-limited presigned GET URL for a stored event poster object key.
    Uses the public MinIO client with explicit region='us-east-1' for local cryptographic signing.
    Returns None if image_key is empty or if presigning encounters any error, logging a warning.
    """
    key = str(image_key).strip() if image_key else ""
    if not key:
        return None

    try:
        expiry_seconds = getattr(settings, "MINIO_PRESIGNED_EXPIRY_SECONDS", 3600)
        bucket_name = getattr(settings, "MINIO_BUCKET_NAME", "dicoevent-posters")
        client = get_public_minio_client()
        return client.presigned_get_object(
            bucket_name=bucket_name,
            object_name=key,
            expires=timedelta(seconds=expiry_seconds),
        )
    except Exception as exc:
        logger.warning(f"Failed to generate presigned URL for image '{image_key}': {exc}")
        return None


def upload_poster_to_minio(file_obj, filename: str, content_type: str = "application/octet-stream") -> str:
    """
    Upload an event poster file object to MinIO (max 500 KB per Coding Standard #1).
    Ensures bucket exists (creates if not exists), uploads the object, and returns the object key.
    """
    client = get_minio_client()
    bucket_name = getattr(settings, "MINIO_BUCKET_NAME", "dicoevent-posters")

    if not client.bucket_exists(bucket_name):
        logger.info(f"MinIO bucket '{bucket_name}' does not exist. Creating bucket...")
        client.make_bucket(bucket_name)

    clean_filename = os.path.basename(filename)
    unique_key = f"{uuid.uuid4().hex}_{clean_filename}"

    if hasattr(file_obj, "size"):
        size = file_obj.size
    else:
        file_obj.seek(0, os.SEEK_END)
        size = file_obj.tell()
        file_obj.seek(0)

    if hasattr(file_obj, "seek"):
        file_obj.seek(0)

    client.put_object(
        bucket_name=bucket_name,
        object_name=unique_key,
        data=file_obj,
        length=size,
        content_type=content_type,
    )
    logger.info(f"Event poster uploaded to MinIO: '{unique_key}' ({size} bytes) in bucket '{bucket_name}'.")
    return unique_key


def validate_poster_image(image_file):
    """
    Validate that an image file does not exceed 500 KB (500 * 1024 bytes)
    and is a valid image according to Pillow.
    Raises serializers.ValidationError on failure.
    """
    max_size = 500 * 1024
    size = getattr(image_file, "size", None)
    if size is None and hasattr(image_file, "seek") and hasattr(image_file, "tell"):
        image_file.seek(0, os.SEEK_END)
        size = image_file.tell()
        image_file.seek(0)

    if size is not None and size > max_size:
        raise serializers.ValidationError(f"File size exceeds the 500 KB limit ({size} bytes).")

    content_type = getattr(image_file, "content_type", None)
    if content_type is not None and not content_type.startswith("image/"):
        raise serializers.ValidationError("File must have an image/* MIME type.")

    try:
        img = Image.open(image_file)
        img.verify()
        if hasattr(image_file, "seek"):
            image_file.seek(0)
    except Exception:
        raise serializers.ValidationError("Uploaded file is not a valid image.")

    return image_file


def attach_event_poster(event, image_file, actor):
    """
    Deep intake seam encapsulating Organizer ownership verification, MinIO object upload (<= 500 KB),
    and EventPoster persistence.
    """
    if not is_admin_user(actor):
        if str(event.organizer_id) != str(getattr(actor, "id", None)):
            logger.warning(
                f"Actor '{getattr(actor, 'username', '')}' (ID: {getattr(actor, 'id', '')}) denied upload to "
                f"event '{event.name}' (ID: {event.id}, Organizer ID: {event.organizer_id})."
            )
            raise PermissionDenied("You do not have permission to upload a poster for this event.")

    validate_poster_image(image_file)

    filename = getattr(image_file, "name", "poster.png")
    content_type = getattr(image_file, "content_type", "image/jpeg")

    stored_filename = upload_poster_to_minio(
        file_obj=image_file,
        filename=filename,
        content_type=content_type,
    )

    poster = EventPoster.objects.create(
        event=event,
        image=stored_filename,
    )
    username = (
        getattr(actor, "username", "anonymous") if actor and getattr(actor, "is_authenticated", False) else "anonymous"
    )
    logger.info(
        f"Poster uploaded successfully for event '{event.name}' (ID: {event.id}): '{stored_filename}' "
        f"(Poster ID: {poster.id}) by user '{username}'"
    )
    return poster
