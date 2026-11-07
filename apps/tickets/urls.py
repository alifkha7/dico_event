from django.urls import re_path

from .views import TicketViewSet

urlpatterns = [
    re_path(r"^tickets/?$", TicketViewSet.as_view({"get": "list", "post": "create"}), name="ticket-list"),
    re_path(
        r"^tickets/(?P<pk>[^/]+)/?$",
        TicketViewSet.as_view({"get": "retrieve", "put": "update", "patch": "partial_update", "delete": "destroy"}),
        name="ticket-detail",
    ),
]
