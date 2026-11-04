from rest_framework import permissions

def is_admin_user(user):
    """Check if user is a Superuser or member of an 'admin' group (case-insensitive)."""
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    return user.groups.filter(name__iexact='admin').exists()

def is_organizer_user(user):
    """Check if user is a member of an 'organizer' group (case-insensitive)."""
    if not user or not user.is_authenticated:
        return False
    return user.groups.filter(name__iexact='organizer').exists()

def can_create_or_manage_events(user):
    """Check if user has permission to create or manage events."""
    return is_admin_user(user) or is_organizer_user(user)

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
        return str(obj.id) == str(request.user.id)

class EventViewSetPermission(permissions.BasePermission):
    """
    Permission logic for EventViewSet:
    - GET (list): AllowAny per ADR-0001 / spec
    - GET (retrieve): AllowAny per ADR-0001
    - POST (create): Superuser, Admin, or Organizer
    - PUT / PATCH (update):
        - Superuser or Admin on any event
        - Organizer only if event.organizer_id == request.user.id
        - Others forbidden (403)
    - DELETE (destroy):
        - Superuser or Admin on any event
        - Organizer only if event.organizer_id == request.user.id
        - Others forbidden (403)
    """
    def has_permission(self, request, view):
        if view.action in ['list', 'retrieve']:
            return True
        if not request.user or not request.user.is_authenticated:
            return False
        if view.action == 'create':
            return can_create_or_manage_events(request.user)
        if view.action in ['update', 'partial_update', 'destroy']:
            return can_create_or_manage_events(request.user)
        return False

    def has_object_permission(self, request, view, obj):
        if view.action == 'retrieve':
            return True
        if not request.user or not request.user.is_authenticated:
            return False
        if is_admin_user(request.user):
            return True
        if is_organizer_user(request.user):
            return str(obj.organizer_id) == str(request.user.id)
        return False

class TicketViewSetPermission(permissions.BasePermission):
    """
    Permission logic for TicketViewSet:
    - GET (list): AllowAny
    - GET (retrieve): AllowAny per ADR-0001
    - POST (create): Authenticated Superuser, Admin, or Organizer
    - PUT / PATCH (update): Authenticated Superuser, Admin, or Organizer
    - DELETE (destroy): Authenticated Superuser, Admin, or Organizer
    """
    def has_permission(self, request, view):
        if view.action in ['list', 'retrieve']:
            return True
        if not request.user or not request.user.is_authenticated:
            return False
        return can_create_or_manage_events(request.user)

    def has_object_permission(self, request, view, obj):
        if view.action == 'retrieve':
            return True
        if not request.user or not request.user.is_authenticated:
            return False
        return can_create_or_manage_events(request.user)

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
        return str(obj.registration.user_id) == str(request.user.id)
