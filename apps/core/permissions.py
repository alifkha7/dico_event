from rest_framework import permissions


def get_user_role_names(user):
    """
    Return a set of lowercase group/role names for user.
    Uses user._prefetched_objects_cache if groups were prefetched,
    and caches on user._cached_role_names and user._cached_group_names_lower.
    """
    if not user or not getattr(user, "is_authenticated", False):
        return set()

    cached = getattr(user, "_cached_role_names", None)
    if cached is not None:
        return cached

    cached = getattr(user, "_cached_group_names_lower", None)
    if cached is not None:
        user._cached_role_names = cached
        return cached

    prefetched_cache = getattr(user, "_prefetched_objects_cache", {})
    if "groups" in prefetched_cache:
        names = {g.name.lower() for g in prefetched_cache["groups"]}
    else:
        names = {name.lower() for name in user.groups.values_list("name", flat=True)}

    user._cached_role_names = names
    user._cached_group_names_lower = names
    return names


def is_admin_user(user):
    """Check if user is a Superuser or assigned to an 'admin' Group (case-insensitive)."""
    if not user or not getattr(user, "is_authenticated", False):
        return False
    if getattr(user, "is_superuser", False):
        return True
    return "admin" in get_user_role_names(user)


def is_organizer_user(user):
    """Check if user is assigned to an 'organizer' Group (case-insensitive)."""
    if not user or not getattr(user, "is_authenticated", False):
        return False
    return "organizer" in get_user_role_names(user)


class IsSuperuser(permissions.BasePermission):
    """Allows access only to superusers."""

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_superuser)


class IsAdminOrSuperuser(permissions.BasePermission):
    """Allows access to Superusers or Users assigned to the admin Group."""

    def has_permission(self, request, view):
        return bool(is_admin_user(request.user))


def _resolve_object_owner_id(obj, owner_field):
    if not owner_field:
        return None
    val = obj
    for part in owner_field.replace("__", ".").split("."):
        if val is None:
            return None
        val = getattr(val, part, None)
    if val is not None and hasattr(val, "id"):
        val = val.id
    return val


class RoleOwnershipPermission(permissions.BasePermission):
    """
    Declarative Role-Based Access Control and Resource Ownership permission base class.

    Enforces:
    - ADR-0001 unauthenticated GET on retrieve (and configured public_actions)
    - Full bypass for Superuser and Admin actors
    - Group-scoped permissions and declarative resource ownership verification
    """

    public_actions = ()
    admin_only_actions = ()
    allowed_create_roles = None
    owner_field = None
    owner_roles = None
    disallow_owner_actions = ()

    def is_public_action(self, request, view):
        action = getattr(view, "action", None)
        if action in self.public_actions:
            return True
        return False

    def has_permission(self, request, view):
        if self.is_public_action(request, view):
            return True

        if not request.user or not request.user.is_authenticated:
            return False

        if is_admin_user(request.user):
            return True

        action = getattr(view, "action", None)
        if action in self.admin_only_actions:
            return False

        if action == "create" and self.allowed_create_roles:
            user_roles = get_user_role_names(request.user)
            if not (self.allowed_create_roles & user_roles):
                return False

        if action in ["update", "partial_update", "destroy"]:
            required_roles = self.owner_roles or self.allowed_create_roles
            if required_roles:
                user_roles = get_user_role_names(request.user)
                if not (required_roles & user_roles):
                    return False

        return True

    def has_object_permission(self, request, view, obj):
        if self.is_public_action(request, view):
            return True

        if not request.user or not request.user.is_authenticated:
            return False

        if is_admin_user(request.user):
            return True

        action = getattr(view, "action", None)
        if action in self.disallow_owner_actions:
            return False

        if self.owner_roles:
            user_roles = get_user_role_names(request.user)
            if not (self.owner_roles & user_roles):
                return False

        owner_id = _resolve_object_owner_id(obj, self.owner_field)
        if owner_id is not None:
            return str(owner_id) == str(request.user.id)

        return False
