from apps.core.permissions import RoleOwnershipPermission, is_admin_user
from apps.registrations.models import Registration

__all__ = ["PaymentViewSetPermission"]


class PaymentViewSetPermission(RoleOwnershipPermission):
    """
    Declarative Role-Based Access Control and User ownership permission for PaymentViewSet:
    - All actions require authentication (public_actions = ())
    - Admin and Superuser platform-wide access
    - Scoped listing: Users see own, Organizers see own + participant payments of owned events
    - Scoped retrieve: User owner, Organizer of parent event, or Admin/Superuser
    - User resource ownership enforced on mutations (registration.user_id == request.user.id)
    - Organizers cannot modify or delete participants' payments
    """

    public_actions = ()
    admin_only_actions = ()
    owner_field = "registration__user_id"
    read_only_owner_roles = {"organizer"}
    read_only_owner_field = "registration__ticket__event__organizer_id"

    def _check_payload_registration_ownership(self, request) -> bool:
        if not hasattr(request, "data"):
            return True
        target_reg = request.data.get("registration_id") or request.data.get("registration")
        if target_reg:
            target_reg_id = getattr(target_reg, "id", target_reg)
            try:
                reg = Registration.objects.select_related("user").get(id=target_reg_id)
                if str(reg.user_id) != str(request.user.id):
                    return False
            except (Registration.DoesNotExist, ValueError):
                pass
        return True

    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False

        if is_admin_user(request.user):
            return True

        action = getattr(view, "action", None)
        if action == "create":
            if not self._check_payload_registration_ownership(request):
                return False

        return True

    def has_object_permission(self, request, view, obj):
        action = getattr(view, "action", None)
        if action in ["update", "partial_update"]:
            if not self._check_payload_registration_ownership(request):
                return False

        return super().has_object_permission(request, view, obj)
