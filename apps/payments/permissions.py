from apps.core.permissions import RoleOwnershipPermission, is_admin_user
from apps.registrations.models import Registration

__all__ = ["PaymentViewSetPermission"]


class PaymentViewSetPermission(RoleOwnershipPermission):
    """
    Declarative Role-Based Access Control and User ownership permission for PaymentViewSet:
    - Unauthenticated detail retrieve per ADR-0001
    - Admin and Superuser platform-wide access
    - Admin or Superuser only for listing
    - User resource ownership enforced on mutations (registration.user_id == request.user.id)
    - Non-admin Users cannot create or reassign a Payment for another User's Registration
    """

    public_actions = ("retrieve",)
    admin_only_actions = ("list",)
    owner_field = "registration__user_id"

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
        if not super().has_object_permission(request, view, obj):
            return False

        if is_admin_user(request.user):
            return True

        action = getattr(view, "action", None)
        if action in ["update", "partial_update"]:
            if not self._check_payload_registration_ownership(request):
                return False

        return True
