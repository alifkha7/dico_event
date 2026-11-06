from rest_framework import permissions

from apps.core.permissions import RoleOwnershipPermission, can_create_or_manage_events

__all__ = [
    "CanUploadPosterPermission",
    "EventPosterUploadPermission",
    "EventViewSetPermission",
]


class EventViewSetPermission(RoleOwnershipPermission):
    """
    Declarative permission policy for EventViewSet:
    - Public list and retrieve per ADR-0001
    - Superuser and Admin platform-wide bypass
    - Organizer role required on create
    - Organizer resource ownership enforced on mutations (update, partial_update, destroy)
    """

    public_actions = ("list", "retrieve")
    allowed_create_roles = {"organizer"}
    owner_roles = {"organizer"}
    owner_field = "organizer_id"


class EventPosterUploadPermission(permissions.BasePermission):
    """Allows access to authenticated Superuser, Admin, or Organizer to upload posters."""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return can_create_or_manage_events(request.user)


CanUploadPosterPermission = EventPosterUploadPermission
