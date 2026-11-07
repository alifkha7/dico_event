from django.urls import re_path

from .views import RegistrationViewSet

urlpatterns = [
    re_path(
        r"^registrations/?$",
        RegistrationViewSet.as_view({"get": "list", "post": "create"}),
        name="registration-list",
    ),
    re_path(
        r"^registrations/(?P<pk>[^/]+)/?$",
        RegistrationViewSet.as_view(
            {"get": "retrieve", "put": "update", "patch": "partial_update", "delete": "destroy"}
        ),
        name="registration-detail",
    ),
]
