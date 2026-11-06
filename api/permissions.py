from rest_framework import permissions

from apps.core.permissions import (
    IsAdminOrSuperuser,
    IsSuperuser,
    RoleOwnershipPermission,
    _get_user_group_names_lower,
    can_create_or_manage_events,
    get_user_role_names,
    is_admin_user,
    is_organizer_user,
)
from apps.events.permissions import (
    CanUploadPosterPermission,
    EventPosterUploadPermission,
    EventViewSetPermission,
)
from apps.users.permissions import UserViewSetPermission

__all__ = [
    "CanUploadPosterPermission",
    "EventPosterUploadPermission",
    "EventViewSetPermission",
    "IsAdminOrSuperuser",
    "IsSuperuser",
    "PaymentViewSetPermission",
    "RegistrationViewSetPermission",
    "RoleOwnershipPermission",
    "TicketViewSetPermission",
    "UserViewSetPermission",
    "_get_user_group_names_lower",
    "can_create_or_manage_events",
    "get_user_role_names",
    "is_admin_user",
    "is_organizer_user",
]


class TicketViewSetPermission(permissions.BasePermission):
    """
    Permission logic for TicketViewSet:
    - GET (list): AllowAny
    - GET (retrieve): AllowAny per ADR-0001
    - POST (create): Authenticated Superuser, Admin, or Organizer
    - PUT / PATCH (update): Superuser, Admin, or Organizer who owns the event
    - DELETE (destroy): Superuser, Admin, or Organizer who owns the event
    """

    def has_permission(self, request, view):
        if view.action in ["list", "retrieve"]:
            return True
        if not request.user or not request.user.is_authenticated:
            return False
        return can_create_or_manage_events(request.user)

    def has_object_permission(self, request, view, obj):
        if view.action == "retrieve":
            return True
        if not request.user or not request.user.is_authenticated:
            return False
        if is_admin_user(request.user):
            return True
        if is_organizer_user(request.user):
            return str(obj.event.organizer_id) == str(request.user.id)
        return False


class RegistrationViewSetPermission(permissions.BasePermission):
    """
    Permission logic for RegistrationViewSet:
    - GET (list): Admin or Superuser only (regular user gets 403)
    - GET (retrieve): AllowAny per ADR-0001
    - POST (create): Authenticated users (User, Organizer, Admin, Superuser)
    - PUT / PATCH (update): Admin, Superuser, or owner User
    - DELETE (destroy): Admin, Superuser, or owner User
    """

    def has_permission(self, request, view):
        if view.action == "retrieve":
            return True
        if not request.user or not request.user.is_authenticated:
            return False
        if view.action == "list":
            return is_admin_user(request.user)
        return True

    def has_object_permission(self, request, view, obj):
        if view.action == "retrieve":
            return True
        if not request.user or not request.user.is_authenticated:
            return False
        if is_admin_user(request.user):
            return True
        return str(obj.user_id) == str(request.user.id)


class PaymentViewSetPermission(permissions.BasePermission):
    """
    Permission logic for PaymentViewSet:
    - GET (list): Admin or Superuser only (regular user gets 403)
    - GET (retrieve): AllowAny per ADR-0001
    - POST (create): Authenticated users (User, Organizer, Admin, Superuser)
    - PUT / PATCH (update): Admin, Superuser, or owner User
    - DELETE (destroy): Admin, Superuser, or owner User
    """

    def has_permission(self, request, view):
        if view.action == "retrieve":
            return True
        if not request.user or not request.user.is_authenticated:
            return False
        if view.action == "list":
            return is_admin_user(request.user)
        return True

    def has_object_permission(self, request, view, obj):
        if view.action == "retrieve":
            return True
        if not request.user or not request.user.is_authenticated:
            return False
        if is_admin_user(request.user):
            return True
        return str(obj.user_id) == str(request.user.id)
