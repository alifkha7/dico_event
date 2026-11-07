from apps.core.permissions import RoleOwnershipPermission, is_admin_user

__all__ = ["TicketViewSetPermission"]


class TicketViewSetPermission(RoleOwnershipPermission):
    """
    Declarative Role-Based Access Control and Organizer ownership permission for TicketViewSet:
    - Public list and retrieve per ADR-0001
    - Superuser and Admin platform-wide bypass
    - Organizer role required on create
    - Organizer resource ownership enforced via event.organizer_id on create/update/destroy
    - Prevents Organizers from creating or reassigning tickets to events owned by other Organizers
    """

    public_actions = ("list", "retrieve")
    allowed_create_roles = {"organizer"}
    owner_roles = {"organizer"}
    owner_field = "event__organizer_id"

    def _check_payload_event_ownership(self, request) -> bool:
        if not hasattr(request, "data"):
            return True
        event_id = request.data.get("event_id") or request.data.get("event")
        if event_id:
            from apps.events.models import Event

            event = Event.objects.filter(id=event_id).first()
            if event and str(event.organizer_id) != str(request.user.id):
                return False
        return True

    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False

        if is_admin_user(request.user):
            return True

        action = getattr(view, "action", None)
        if action == "create":
            if not self._check_payload_event_ownership(request):
                return False

        return True

    def has_object_permission(self, request, view, obj):
        if not super().has_object_permission(request, view, obj):
            return False

        if is_admin_user(request.user):
            return True

        action = getattr(view, "action", None)
        if action in ["update", "partial_update"]:
            if not self._check_payload_event_ownership(request):
                return False

        return True
