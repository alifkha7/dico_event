"""event_project URL Configuration

Routes API requests to the appropriate views. We separate public
endpoints (user creation and login) from protected endpoints using
namespaced includes. JWT token endpoints are provided via the
``rest_framework_simplejwt`` views.
"""

from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("core.urls")),
    path("api/", include("events.urls")),
    path("api/", include("tickets.urls")),
    path("api/", include("registrations.urls")),
    path("api/", include("payments.urls")),
    path("api/login/", TokenObtainPairView.as_view()),
    path("api/token/", TokenRefreshView.as_view()),
    # API Documentation
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/swagger/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/docs/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
]
