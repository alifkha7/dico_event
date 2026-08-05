"""Permission classes used throughout the event project.

These classes extend DRF's ``BasePermission`` to provide role‑based
access control. Roles are defined via Django groups named ``admin``
and ``organizer``. Superusers bypass all group checks.
"""

from rest_framework.permissions import BasePermission


class IsSuperUser(BasePermission):
    """Allow access only to superusers."""

    def has_permission(self, request, view) -> bool:
        return bool(request.user and request.user.is_authenticated and request.user.is_superuser)


class IsAdmin(BasePermission):
    """Allow access to users belonging to the ``admin`` group."""

    def has_permission(self, request, view) -> bool:
        return bool(
            request.user and request.user.is_authenticated and request.user.groups.filter(name="admin").exists()
        )


class IsOrganizer(BasePermission):
    """Allow access to users belonging to the ``organizer`` group."""

    def has_permission(self, request, view) -> bool:
        return bool(
            request.user and request.user.is_authenticated and request.user.groups.filter(name="organizer").exists()
        )


class IsAdminOrSuperUser(BasePermission):
    """Allow access to users who are either admins or superusers."""

    def has_permission(self, request, view) -> bool:
        return bool(
            request.user
            and request.user.is_authenticated
            and (request.user.is_superuser or request.user.groups.filter(name="admin").exists())
        )


class IsAdminOrOrganizerOrSuperUser(BasePermission):
    """Allow access to admins, organizers or superusers."""

    def has_permission(self, request, view) -> bool:
        return bool(
            request.user
            and request.user.is_authenticated
            and (request.user.is_superuser or request.user.groups.filter(name__in=["admin", "organizer"]).exists())
        )


class IsOwnerOrAdminOrSuperUser(BasePermission):
    """Generic object‑level permission for ownership.

    Allows access to the object owner (``obj`` must be comparable to
    ``request.user``), admins or superusers.
    """

    def has_object_permission(self, request, view, obj) -> bool:
        return bool(
            request.user
            and request.user.is_authenticated
            and (request.user.is_superuser or request.user.groups.filter(name="admin").exists() or obj == request.user)
        )


class IsEventOwnerOrAdminOrSuperUser(BasePermission):
    """Object‑level permission for events.

    Allows the event's organizer to modify the event, in addition to
    admins and superusers.  Read‑only access (GET) is unrestricted
    beyond authentication.
    """

    def has_object_permission(self, request, view, obj) -> bool:
        # Allow safe methods (GET, HEAD, OPTIONS) if user is authenticated
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return bool(request.user and request.user.is_authenticated)
        return bool(
            request.user
            and request.user.is_authenticated
            and (
                request.user.is_superuser
                or request.user.groups.filter(name="admin").exists()
                or (
                    request.user.groups.filter(name="organizer").exists()
                    and getattr(obj, "organizer", None) == request.user
                )
            )
        )


class IsOwnerOfRegistrationOrAdminOrSuperUser(BasePermission):
    """Object‑level permission for registrations and payments.

    The owner of a registration (the user who made it) may view
    associated registrations and payments, but only admins and
    superusers may edit or delete them.
    """

    def has_object_permission(self, request, view, obj) -> bool:
        # Determine owner: registration.user for Registration and
        # payment.registration.user for Payment.
        owner = getattr(obj, "user", None)
        if owner is None and hasattr(obj, "registration"):
            owner = getattr(obj.registration, "user", None)
        # Allow read access to owner
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return bool(
                request.user
                and request.user.is_authenticated
                and (
                    request.user.is_superuser
                    or request.user.groups.filter(name="admin").exists()
                    or owner == request.user
                )
            )
        # Non‑safe methods allowed only for admin/superuser
        return bool(
            request.user
            and request.user.is_authenticated
            and (request.user.is_superuser or request.user.groups.filter(name="admin").exists())
        )
