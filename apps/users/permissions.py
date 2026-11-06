from apps.core.permissions import (
    IsAdminOrSuperuser,
    IsSuperuser,
    RoleOwnershipPermission,
    is_admin_user,
)


class UserViewSetPermission(RoleOwnershipPermission):
    """
    Permission logic for UserViewSet:
    - POST (register): AllowAny
    - GET (detail/retrieve): AllowAny per ADR-0001
    - GET (list): Admin or Superuser only (Authenticated User gets 403, Unauthenticated gets 401)
    - PUT/PATCH: Authenticated (Self, Admin, or Superuser)
    - DELETE: Admin or Superuser only (Authenticated regular User gets 403 per Story 9 / Spec)
    """

    public_actions = ("create", "retrieve")
    admin_only_actions = ("list", "destroy")
    owner_field = "id"
    disallow_owner_actions = ("destroy",)


__all__ = [
    "IsAdminOrSuperuser",
    "IsSuperuser",
    "UserViewSetPermission",
    "is_admin_user",
]
