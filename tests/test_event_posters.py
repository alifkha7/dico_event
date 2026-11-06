import io
import os
import uuid
from unittest.mock import MagicMock, patch

import pytest
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image
from rest_framework import exceptions, status

from apps.events.models import Event, EventPoster
from apps.events.storage import attach_event_poster

# ==========================================
# Helpers for image generation
# ==========================================


def create_valid_test_image(format="PNG", size=(50, 50), color=(0, 128, 255)):
    """Generate a small valid image in memory."""
    buf = io.BytesIO()
    img = Image.new("RGB", size, color=color)
    img.save(buf, format=format)
    buf.seek(0)
    return SimpleUploadedFile(
        name=f"test_poster.{format.lower()}", content=buf.getvalue(), content_type=f"image/{format.lower()}"
    )


def create_oversized_test_image():
    """Generate a valid image exceeding 500 KB (512,000 bytes)."""
    buf = io.BytesIO()
    # 600x600 random noise PNG generates ~1 MB
    img = Image.frombytes("RGB", (600, 600), os.urandom(600 * 600 * 3))
    img.save(buf, format="PNG")
    buf.seek(0)
    assert len(buf.getvalue()) > 500 * 1024
    return SimpleUploadedFile(name="oversized_poster.png", content=buf.getvalue(), content_type="image/png")


@pytest.fixture
def sample_event(organizer_user):
    return Event.objects.create(
        name="Tech Conference 2026",
        description="Leading tech event in Jakarta.",
        location="Jakarta",
        start_time="2026-11-20T09:00:00Z",
        end_time="2026-11-20T17:00:00Z",
        status="published",
        quota=200,
        category="Technology",
        organizer=organizer_user,
    )


# ==========================================
# 1. MinIO Configuration & Storage Unit Tests
# ==========================================


def test_get_minio_client_configuration(monkeypatch):
    """Verify get_minio_client configures endpoint, access key, secret key, and SSL."""
    monkeypatch.setattr(settings, "MINIO_ENDPOINT_URL", "http://minio.custom.local:9000")
    monkeypatch.setattr(settings, "MINIO_ACCESS_KEY", "custom_access")
    monkeypatch.setattr(settings, "MINIO_SECRET_KEY", "custom_secret")

    from apps.events.storage import get_minio_client

    client = get_minio_client()
    assert client._base_url._url.netloc == "minio.custom.local:9000"
    assert client._base_url.is_https is False
    creds = client._provider.retrieve()
    assert creds.access_key == "custom_access"
    assert creds.secret_key == "custom_secret"


def test_get_minio_client_endpoint_parsing():
    """Verify endpoint parsing handles raw host:port, http://, and https://."""
    from apps.events.storage import parse_minio_endpoint

    endpoint, secure = parse_minio_endpoint("http://minio.test:9000")
    assert endpoint == "minio.test:9000"
    assert secure is False

    endpoint, secure = parse_minio_endpoint("https://s3.amazonaws.com")
    assert endpoint == "s3.amazonaws.com"
    assert secure is True

    endpoint, secure = parse_minio_endpoint("localhost:9000", default_secure=False)
    assert endpoint == "localhost:9000"
    assert secure is False

    endpoint, secure = parse_minio_endpoint("localhost:9000", default_secure=True)
    assert endpoint == "localhost:9000"
    assert secure is True


def test_upload_poster_to_minio_creates_bucket_if_missing(monkeypatch):
    """Verify upload_poster_to_minio checks bucket existence and creates bucket if missing."""
    mock_client = MagicMock()
    mock_client.bucket_exists.return_value = False

    with patch("apps.events.storage.get_minio_client", return_value=mock_client):
        from apps.events.storage import upload_poster_to_minio

        fake_file = io.BytesIO(b"fake image data")
        result_key = upload_poster_to_minio(fake_file, "poster.png", "image/png")

        mock_client.bucket_exists.assert_called_once_with(settings.MINIO_BUCKET_NAME)
        mock_client.make_bucket.assert_called_once_with(settings.MINIO_BUCKET_NAME)
        mock_client.put_object.assert_called_once()
        assert isinstance(result_key, str) and len(result_key) > 0
        assert "poster.png" in result_key


# ==========================================
# 2. EventPoster Model Unit Tests
# ==========================================


@pytest.mark.django_db
def test_event_poster_model_creation(sample_event):
    """Verify EventPoster model has UUID pk, cascade delete on Event, and stores image string."""
    poster = EventPoster.objects.create(event=sample_event, image="unique_key_banner.png")
    assert poster.id is not None
    assert str(poster.event.id) == str(sample_event.id)
    assert poster.image == "unique_key_banner.png"
    assert EventPoster._meta.db_table == "event_posters"

    poster_id = poster.id
    # Test cascade delete
    sample_event.delete()
    assert not EventPoster.objects.filter(id=poster_id).exists()


# ==========================================
# 3. Poster Upload API (POST /api/events/upload/)
# ==========================================


@pytest.mark.django_db
def test_upload_poster_valid_image(api_client, superuser, admin_user, organizer_user, get_auth_header, sample_event):
    """Verify Superuser, Admin, and Organizer can upload valid poster images <= 500 KB."""
    with patch("apps.events.storage.upload_poster_to_minio", return_value="stored_poster_key_1.png") as mock_upload:
        # 1. Superuser upload
        image = create_valid_test_image()
        res = api_client.post(
            "/api/events/upload/",
            {"image": image, "event": str(sample_event.id)},
            format="multipart",
            **get_auth_header(superuser),
        )
        assert res.status_code == status.HTTP_201_CREATED
        assert "id" in res.data and isinstance(res.data["id"], str) and res.data["id"]
        assert "image" in res.data and res.data["image"] == "stored_poster_key_1.png"
        assert "event" in res.data and res.data["event"] == str(sample_event.id)
        mock_upload.assert_called_once()

    with patch("apps.events.storage.upload_poster_to_minio", return_value="stored_poster_key_2.png"):
        # 2. Organizer upload
        image2 = create_valid_test_image(format="JPEG")
        res2 = api_client.post(
            "/api/events/upload/",
            {"image": image2, "event": str(sample_event.id)},
            format="multipart",
            **get_auth_header(organizer_user),
        )
        assert res2.status_code == status.HTTP_201_CREATED
        assert res2.data["image"] == "stored_poster_key_2.png"

    with patch("apps.events.storage.upload_poster_to_minio", return_value="stored_poster_key_3.png"):
        # 3. Admin upload
        image3 = create_valid_test_image()
        res3 = api_client.post(
            "/api/events/upload/",
            {"image": image3, "event": str(sample_event.id)},
            format="multipart",
            **get_auth_header(admin_user),
        )
        assert res3.status_code == status.HTTP_201_CREATED
        assert res3.data["image"] == "stored_poster_key_3.png"

    # Database records verified
    assert EventPoster.objects.filter(event=sample_event).count() == 3


@pytest.mark.django_db
def test_upload_poster_no_trailing_slash(api_client, organizer_user, get_auth_header, sample_event):
    """Verify POST /api/events/upload without trailing slash works per ADR-0001."""
    with patch("apps.events.storage.upload_poster_to_minio", return_value="notrail_key.png"):
        image = create_valid_test_image()
        res = api_client.post(
            "/api/events/upload",
            {"image": image, "event": str(sample_event.id)},
            format="multipart",
            **get_auth_header(organizer_user),
        )
        assert res.status_code == status.HTTP_201_CREATED
        assert res.data["image"] == "notrail_key.png"


@pytest.mark.django_db
def test_upload_poster_missing_fields(api_client, organizer_user, get_auth_header, sample_event):
    """Verify 400 Bad Request when image or event field is missing or invalid."""
    # Missing image
    res1 = api_client.post(
        "/api/events/upload/", {"event": str(sample_event.id)}, format="multipart", **get_auth_header(organizer_user)
    )
    assert res1.status_code == status.HTTP_400_BAD_REQUEST

    # Missing event
    image = create_valid_test_image()
    res2 = api_client.post(
        "/api/events/upload/", {"image": image}, format="multipart", **get_auth_header(organizer_user)
    )
    assert res2.status_code == status.HTTP_400_BAD_REQUEST

    # Non-existent event UUID
    image2 = create_valid_test_image()
    res3 = api_client.post(
        "/api/events/upload/",
        {"image": image2, "event": str(uuid.uuid4())},
        format="multipart",
        **get_auth_header(organizer_user),
    )
    assert res3.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_upload_poster_non_image_file_rejected(api_client, organizer_user, get_auth_header, sample_event):
    """Verify non-image files (.txt, .pdf, or disguised image) are rejected with 400."""
    with patch("apps.events.storage.upload_poster_to_minio") as mock_upload:
        # Plain text
        txt_file = SimpleUploadedFile("readme.txt", b"plain text content", content_type="text/plain")
        res1 = api_client.post(
            "/api/events/upload/",
            {"image": txt_file, "event": str(sample_event.id)},
            format="multipart",
            **get_auth_header(organizer_user),
        )
        assert res1.status_code == status.HTTP_400_BAD_REQUEST
        mock_upload.assert_not_called()

        # PDF file
        pdf_file = SimpleUploadedFile("doc.pdf", b"%PDF-1.4...", content_type="application/pdf")
        res2 = api_client.post(
            "/api/events/upload/",
            {"image": pdf_file, "event": str(sample_event.id)},
            format="multipart",
            **get_auth_header(organizer_user),
        )
        assert res2.status_code == status.HTTP_400_BAD_REQUEST
        mock_upload.assert_not_called()

        # Disguised non-image file with image/png MIME type
        fake_png = SimpleUploadedFile("fake.png", b"This is text posing as png", content_type="image/png")
        res3 = api_client.post(
            "/api/events/upload/",
            {"image": fake_png, "event": str(sample_event.id)},
            format="multipart",
            **get_auth_header(organizer_user),
        )
        assert res3.status_code == status.HTTP_400_BAD_REQUEST
        mock_upload.assert_not_called()

    # Nothing saved in DB
    assert EventPoster.objects.filter(event=sample_event).count() == 0


@pytest.mark.django_db
def test_upload_poster_oversized_image_rejected(api_client, organizer_user, get_auth_header, sample_event):
    """Verify images > 500 KB (512,000 bytes) are rejected with 400 Bad Request."""
    with patch("apps.events.storage.upload_poster_to_minio") as mock_upload:
        large_image = create_oversized_test_image()
        res = api_client.post(
            "/api/events/upload/",
            {"image": large_image, "event": str(sample_event.id)},
            format="multipart",
            **get_auth_header(organizer_user),
        )
        assert res.status_code == status.HTTP_400_BAD_REQUEST
        mock_upload.assert_not_called()

    assert EventPoster.objects.filter(event=sample_event).count() == 0


@pytest.mark.django_db
def test_upload_poster_permissions_unauthenticated_and_regular_user(
    api_client, regular_user, get_auth_header, sample_event
):
    """Verify unauthenticated requests return 401 and regular users return 403."""
    image = create_valid_test_image()
    # Unauthenticated
    res1 = api_client.post("/api/events/upload/", {"image": image, "event": str(sample_event.id)}, format="multipart")
    assert res1.status_code == status.HTTP_401_UNAUTHORIZED

    # Regular user (non-admin, non-organizer)
    image2 = create_valid_test_image()
    res2 = api_client.post(
        "/api/events/upload/",
        {"image": image2, "event": str(sample_event.id)},
        format="multipart",
        **get_auth_header(regular_user),
    )
    assert res2.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_upload_poster_organizer_other_event_forbidden(api_client, organizer_group, get_auth_header, sample_event):
    """Verify Organizer cannot upload poster to another Organizer's event (403 Forbidden)."""
    from django.contrib.auth import get_user_model

    User = get_user_model()
    other_organizer = User.objects.create_user(
        username="other_org_poster", email="other_org_poster@dicoevent.com", password="password123"
    )
    other_organizer.groups.add(organizer_group)
    image = create_valid_test_image()
    res = api_client.post(
        "/api/events/upload/",
        {"image": image, "event": str(sample_event.id)},
        format="multipart",
        **get_auth_header(other_organizer),
    )
    assert res.status_code == status.HTTP_403_FORBIDDEN


# ==========================================
# 4. Poster Retrieval API (GET /api/events/<id>/poster/)
# ==========================================


@pytest.mark.django_db
def test_get_event_posters_list(api_client, sample_event, regular_user, get_auth_header):
    """Verify GET /api/events/<id>/poster/ returns top-level JSON array of poster objects."""
    p1 = EventPoster.objects.create(event=sample_event, image="key1.png")
    p2 = EventPoster.objects.create(event=sample_event, image="key2.png")

    # Unauthenticated read (AllowAny per ADR-0001)
    res = api_client.get(f"/api/events/{sample_event.id}/poster/")
    assert res.status_code == status.HTTP_200_OK
    assert isinstance(res.data, list)
    assert len(res.data) == 2

    # Verify poster item attributes
    poster_items = {item["id"]: item for item in res.data}
    assert str(p1.id) in poster_items
    assert poster_items[str(p1.id)]["image"] == "key1.png"
    assert str(p2.id) in poster_items
    assert poster_items[str(p2.id)]["image"] == "key2.png"

    # Authenticated read
    res_auth = api_client.get(f"/api/events/{sample_event.id}/poster/", **get_auth_header(regular_user))
    assert res_auth.status_code == status.HTTP_200_OK
    assert isinstance(res_auth.data, list)
    assert len(res_auth.data) == 2


@pytest.mark.django_db
def test_get_event_posters_no_trailing_slash_and_aliases(api_client, sample_event):
    """Verify optional trailing slashes and /posters plural alias per ADR-0001."""
    EventPoster.objects.create(event=sample_event, image="key.png")

    # No trailing slash
    res1 = api_client.get(f"/api/events/{sample_event.id}/poster")
    assert res1.status_code == status.HTTP_200_OK
    assert isinstance(res1.data, list)
    assert len(res1.data) == 1

    # Plural alias with trailing slash
    res2 = api_client.get(f"/api/events/{sample_event.id}/posters/")
    assert res2.status_code == status.HTTP_200_OK
    assert len(res2.data) == 1

    # Plural alias without trailing slash
    res3 = api_client.get(f"/api/events/{sample_event.id}/posters")
    assert res3.status_code == status.HTTP_200_OK
    assert len(res3.data) == 1


@pytest.mark.django_db
def test_get_event_posters_empty_and_not_found(api_client, sample_event):
    """Verify empty array when no posters exist, and 404 when event does not exist."""
    # Empty posters
    res = api_client.get(f"/api/events/{sample_event.id}/poster/")
    assert res.status_code == status.HTTP_200_OK
    assert res.data == []

    # Non-existent event
    random_id = uuid.uuid4()
    res_404 = api_client.get(f"/api/events/{random_id}/poster/")
    assert res_404.status_code == status.HTTP_404_NOT_FOUND


# ==========================================
# 5. Deep Intake Seam Tests: attach_event_poster
# ==========================================


@pytest.mark.django_db
def test_attach_event_poster_organizer_success(sample_event, organizer_user):
    """Verify attach_event_poster uploads image to MinIO and creates EventPoster for owner Organizer."""
    with patch("apps.events.storage.upload_poster_to_minio", return_value="attached_owner_key.png") as mock_upload:
        image = create_valid_test_image()
        poster = attach_event_poster(sample_event, image, organizer_user)
        assert poster.id is not None
        assert poster.image == "attached_owner_key.png"
        assert poster.event_id == sample_event.id
        mock_upload.assert_called_once()


@pytest.mark.django_db
def test_attach_event_poster_admin_and_superuser_bypass(sample_event, admin_user, superuser):
    """Verify attach_event_poster allows Admin and Superuser to attach poster to any event."""
    with patch("apps.events.storage.upload_poster_to_minio", return_value="attached_admin_key.png"):
        image1 = create_valid_test_image()
        poster1 = attach_event_poster(sample_event, image1, admin_user)
        assert poster1.image == "attached_admin_key.png"

    with patch("apps.events.storage.upload_poster_to_minio", return_value="attached_superuser_key.png"):
        image2 = create_valid_test_image()
        poster2 = attach_event_poster(sample_event, image2, superuser)
        assert poster2.image == "attached_superuser_key.png"


@pytest.mark.django_db
def test_attach_event_poster_non_owner_forbidden(sample_event, organizer_group, regular_user):
    """Verify attach_event_poster raises PermissionDenied for non-owner Organizer and regular user."""
    from django.contrib.auth import get_user_model

    User = get_user_model()
    other_org = User.objects.create_user(
        username="another_org_attacher", email="another_attacher@dicoevent.com", password="password123"
    )
    other_org.groups.add(organizer_group)

    image = create_valid_test_image()
    with patch("apps.events.storage.upload_poster_to_minio") as mock_upload:
        with pytest.raises(exceptions.PermissionDenied) as exc1:
            attach_event_poster(sample_event, image, other_org)
        assert "You do not have permission to upload a poster for this event." in str(exc1.value)
        mock_upload.assert_not_called()

        with pytest.raises(exceptions.PermissionDenied) as exc2:
            attach_event_poster(sample_event, image, regular_user)
        assert "You do not have permission to upload a poster for this event." in str(exc2.value)
        mock_upload.assert_not_called()
