from rest_framework import permissions

def is_admin_user(user):
    """Check if user is a Superuser or member of an 'admin' group (case-insensitive)."""
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    return user.groups.filter(name__iexact='admin').exists()

class IsSuperuser(permissions.BasePermission):
    """Allows access only to superusers."""
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_superuser)

class IsAdminOrSuperuser(permissions.BasePermission):
    """Allows access to superusers or members of the admin group."""
    def has_permission(self, request, view):
        return bool(is_admin_user(request.user))

class UserViewSetPermission(permissions.BasePermission):
    """
    Permission logic for UserViewSet:
    - POST (register): AllowAny
    - GET (detail/retrieve): AllowAny per ADR-0001
    - GET (list): Admin or Superuser only (Authenticated User gets 403, Unauthenticated gets 401)
    - PUT/PATCH: Authenticated (Self, Admin, or Superuser)
    - DELETE: Authenticated (Self, Admin, or Superuser)
    """
    def has_permission(self, request, view):
        if view.action == 'create':
            return True
        if view.action == 'retrieve':
            return True
        if not request.user or not request.user.is_authenticated:
            return False
        if view.action == 'list':
            return is_admin_user(request.user)
        return True

    def has_object_permission(self, request, view, obj):
        if view.action == 'retrieve':
            return True
        if not request.user or not request.user.is_authenticated:
            return False
        if is_admin_user(request.user):
            return True
        return obj.id == request.user.id
