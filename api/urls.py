from django.urls import re_path

from .views import (
    PaymentViewSet,
    RegistrationViewSet,
    TicketViewSet,
)

urlpatterns = [
    re_path(r"^tickets/?$", TicketViewSet.as_view({"get": "list", "post": "create"}), name="ticket-list"),
    re_path(
        r"^tickets/(?P<pk>[^/]+)/?$",
        TicketViewSet.as_view({"get": "retrieve", "put": "update", "patch": "partial_update", "delete": "destroy"}),
        name="ticket-detail",
    ),
    re_path(
        r"^registrations/?$", RegistrationViewSet.as_view({"get": "list", "post": "create"}), name="registration-list"
    ),
    re_path(
        r"^registrations/(?P<pk>[^/]+)/?$",
        RegistrationViewSet.as_view(
            {"get": "retrieve", "put": "update", "patch": "partial_update", "delete": "destroy"}
        ),
        name="registration-detail",
    ),
    re_path(r"^payments/?$", PaymentViewSet.as_view({"get": "list", "post": "create"}), name="payment-list"),
    re_path(
        r"^payments/(?P<pk>[^/]+)/?$",
        PaymentViewSet.as_view({"get": "retrieve", "put": "update", "patch": "partial_update", "delete": "destroy"}),
        name="payment-detail",
    ),
]
