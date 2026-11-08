from apps.core.permissions import RoleOwnershipPermission, is_admin_user

__all__ = ["RegistrationViewSetPermission"]


class RegistrationViewSetPermission(RoleOwnershipPermission):
    """
    Declarative Role-Based Access Control and User ownership permission for RegistrationViewSet:
    - All actions require authentication (public_actions = ())
    - Admin and Superuser platform-wide access
    - Scoped listing: Users see own, Organizers see own + participants of owned events
    - Scoped retrieve: User owner, Organizer of parent event, or Admin/Superuser
    - User resource ownership enforced on mutations (user_id == request.user.id)
    - Organizers cannot modify or delete participants' registrations
    """

    public_actions = ()
    admin_only_actions = ()
    owner_field = "user_id"
    read_only_owner_roles = {"organizer"}
    read_only_owner_field = "ticket__event__organizer_id"

    def _check_payload_user_ownership(self, request) -> bool:
        if not hasattr(request, "data"):
            return True
        target_user = request.data.get("user_id") or request.data.get("user")
        if target_user:
            target_user_id = getattr(target_user, "id", target_user)
            if str(target_user_id) != str(request.user.id):
                return False
        return True

    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False

        if is_admin_user(request.user):
            return True

        action = getattr(view, "action", None)
        if action == "create":
            if not self._check_payload_user_ownership(request):
                return False

        return True

    def has_object_permission(self, request, view, obj):
        action = getattr(view, "action", None)
        if action in ["update", "partial_update"]:
            if not self._check_payload_user_ownership(request):
                return False

        return super().has_object_permission(request, view, obj)
