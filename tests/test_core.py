import uuid
from unittest.mock import MagicMock

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.db import models
from rest_framework import serializers
from rest_framework.test import APIRequestFactory

from apps.core.permissions import (
    IsSuperuser,
    RoleOwnershipPermission,
    get_user_role_names,
    is_admin_user,
    is_organizer_user,
)
from apps.core.serializers import DualKeyModelSerializer, _resolve_foreign_key
from apps.core.views import PartialUpdateMixin

User = get_user_model()


# Dummy models for testing model-agnostic core serializer
class Author(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)

    class Meta:
        app_label = "core"


class Book(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=100)
    author = models.ForeignKey(Author, on_delete=models.CASCADE, related_name="books")

    class Meta:
        app_label = "core"


class DummyBookSerializer(DualKeyModelSerializer):
    dual_key_fields = {
        "author": {
            "model": Author,
            "id_keys": ("author_id", "author"),
            "required_on_create": True,
            "label": "Author",
        }
    }

    class Meta:
        model = Book
        fields = ["id", "title", "author", "author_id"]
        read_only_fields = ["id", "author"]


@pytest.mark.django_db
def test_resolve_foreign_key_with_id_and_instance():
    """Verify _resolve_foreign_key resolves ID or instance without model-specific branching."""
    author = Author(id=uuid.uuid4(), name="Tolkien")
    attrs = {"author_id": str(author.id)}

    mock_qs = MagicMock()
    mock_qs.get.return_value = author

    _resolve_foreign_key(
        attrs=attrs,
        initial_data={},
        instance=None,
        field_name="author",
        id_keys=["author_id", "author"],
        queryset=mock_qs,
    )
    assert attrs["author"] == author
    assert "author_id" not in attrs
    mock_qs.get.assert_called_once_with(id=str(author.id))


@pytest.mark.django_db
def test_resolve_foreign_key_missing_and_not_found():
    """Verify _resolve_foreign_key raises ValidationError on missing or non-existent target."""
    mock_qs = MagicMock()
    mock_qs.get.side_effect = Exception("Not found")

    # Missing
    attrs = {}
    with pytest.raises(serializers.ValidationError) as exc:
        _resolve_foreign_key(
            attrs=attrs,
            initial_data={},
            instance=None,
            field_name="author",
            id_keys=["author_id", "author"],
            queryset=mock_qs,
            label="Author",
        )
    assert "author_id" in exc.value.detail

    # Not found
    attrs = {"author_id": "non-existent"}
    with pytest.raises(serializers.ValidationError) as exc:
        _resolve_foreign_key(
            attrs=attrs,
            initial_data={},
            instance=None,
            field_name="author",
            id_keys=["author_id", "author"],
            queryset=mock_qs,
            label="Author",
        )
    assert "author_id" in exc.value.detail


@pytest.mark.django_db
def test_dual_key_model_serializer_to_representation():
    """Verify DualKeyModelSerializer outputs string id and both <field> and <field>_id strings."""
    author = Author(id=uuid.uuid4(), name="George Orwell")
    book = Book(id=uuid.uuid4(), title="1984", author=author)

    serializer = DummyBookSerializer(instance=book)
    data = serializer.data

    assert data["id"] == str(book.id)
    assert data["author"] == str(author.id)
    assert data["author_id"] == str(author.id)
    assert data["title"] == "1984"


@pytest.mark.django_db
def test_role_caching_and_helper_functions(regular_user, admin_user, organizer_user):
    """Verify get_user_role_names caches roles on user instance and helpers work."""
    # Test caching on regular user
    roles = get_user_role_names(regular_user)
    assert isinstance(roles, set)
    assert getattr(regular_user, "_cached_role_names", None) == roles
    assert not is_admin_user(regular_user)
    assert not is_organizer_user(regular_user)

    # Test admin user
    assert is_admin_user(admin_user)

    # Test organizer user
    assert is_organizer_user(organizer_user)


@pytest.mark.django_db
def test_is_superuser_permission(superuser, regular_user):
    """Verify IsSuperuser permission allows superuser and denies regular or anonymous user."""
    perm = IsSuperuser()
    factory = APIRequestFactory()

    req_super = factory.get("/api/test/")
    req_super.user = superuser
    assert perm.has_permission(req_super, None) is True

    req_reg = factory.get("/api/test/")
    req_reg.user = regular_user
    assert perm.has_permission(req_reg, None) is False

    req_anon = factory.get("/api/test/")
    req_anon.user = AnonymousUser()
    assert perm.has_permission(req_anon, None) is False


@pytest.mark.django_db
def test_role_ownership_permission_lifecycle(admin_user, organizer_user, regular_user):
    """
    Verify RoleOwnershipPermission requires explicit public_actions,
    denies unauthenticated retrieve by default, and enforces ownership.
    """
    perm = RoleOwnershipPermission()
    perm.owner_field = "organizer_id"
    perm.owner_roles = {"organizer"}

    factory = APIRequestFactory()

    # 1. Default RoleOwnershipPermission has public_actions = () and denies unauthenticated retrieve
    request = factory.get("/api/items/123/")
    request.user = AnonymousUser()
    view = MagicMock(action="retrieve")
    dummy_obj = MagicMock(organizer_id=str(organizer_user.id))

    assert perm.has_permission(request, view) is False
    assert perm.has_object_permission(request, view, dummy_obj) is False

    # 1b. When public_actions explicitly contains "retrieve", unauthenticated retrieve is allowed
    perm.public_actions = ("retrieve",)
    assert perm.has_permission(request, view) is True
    assert perm.has_object_permission(request, view, dummy_obj) is True
    perm.public_actions = ()

    # 2. Unauthenticated GET list is forbidden
    view.action = "list"
    assert perm.has_permission(request, view) is False

    # 3. Admin user bypasses object permission
    request.user = admin_user
    view.action = "update"
    assert perm.has_permission(request, view) is True
    assert perm.has_object_permission(request, view, dummy_obj) is True

    # 4. Organizer owns object -> True
    request.user = organizer_user
    view.action = "update"
    assert perm.has_permission(request, view) is True
    assert perm.has_object_permission(request, view, dummy_obj) is True

    # 5. Organizer does not own object -> False
    other_obj = MagicMock(organizer_id=str(uuid.uuid4()))
    assert perm.has_object_permission(request, view, other_obj) is False

    # 6. Regular user cannot update organizer resource -> False
    request.user = regular_user
    assert perm.has_object_permission(request, view, dummy_obj) is False


def test_partial_update_mixin():
    """Verify PartialUpdateMixin sets partial=True on PUT update kwargs."""

    class BaseView:
        def update(self, request, *args, **kwargs):
            return kwargs

    class DummyViewSet(PartialUpdateMixin, BaseView):
        pass

    mixin = DummyViewSet()
    res = mixin.update(None)
    # partial is defaulted to True
    assert res.get("partial") is True


def test_core_modules_do_not_import_domain_apps():
    """Verify apps.core modules never import from domain apps or legacy api."""
    import ast
    from pathlib import Path

    from django.conf import settings

    core_dir = Path(settings.BASE_DIR) / "apps" / "core"
    forbidden_prefixes = (
        "apps.users",
        "apps.events",
        "apps.tickets",
        "apps.registrations",
        "apps.payments",
        "api",
    )

    for py_file in core_dir.rglob("*.py"):
        tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert not alias.name.startswith(forbidden_prefixes), (
                        f"{py_file.name} imports forbidden domain module '{alias.name}'"
                    )
            elif isinstance(node, ast.ImportFrom) and node.module:
                assert not node.module.startswith(forbidden_prefixes), (
                    f"{py_file.name} imports from forbidden domain module '{node.module}'"
                )
