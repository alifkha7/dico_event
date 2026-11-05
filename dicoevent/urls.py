from django.contrib import admin
from django.urls import include, path, re_path

urlpatterns = [
    path("admin/", admin.site.urls),
    re_path(r"^silk/", include("silk.urls", namespace="silk")),
    re_path(r"^api/", include("api.urls")),
]
