from django.urls import include, re_path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)
from rest_framework.permissions import AllowAny

urlpatterns = [
    re_path(r"^schema/?$", SpectacularAPIView.as_view(permission_classes=[AllowAny]), name="schema"),
    re_path(
        r"^docs/?$", SpectacularSwaggerView.as_view(url_name="schema", permission_classes=[AllowAny]), name="swagger-ui"
    ),
    re_path(r"^redoc/?$", SpectacularRedocView.as_view(url_name="schema", permission_classes=[AllowAny]), name="redoc"),
    re_path(r"^", include("apps.users.urls")),
    re_path(r"^", include("apps.events.urls")),
    re_path(r"^", include("apps.tickets.urls")),
    re_path(r"^", include("apps.registrations.urls")),
    re_path(r"^", include("api.urls")),
]
