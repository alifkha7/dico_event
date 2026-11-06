from django.conf import settings
from django.contrib import admin
from django.urls import include, path, re_path

urlpatterns = [
    path("admin/", admin.site.urls),
    re_path(r"^api/", include("apps.core.urls")),
]

if getattr(settings, "ENABLE_SILK", False):
    urlpatterns.append(re_path(r"^silk/", include("silk.urls", namespace="silk")))
