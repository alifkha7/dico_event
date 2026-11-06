from django.urls import re_path

from .views import (
    EventPostersListView,
    EventPosterUploadView,
    EventViewSet,
)

urlpatterns = [
    re_path(r"^events/?$", EventViewSet.as_view({"get": "list", "post": "create"}), name="event-list"),
    re_path(r"^events/upload/?$", EventPosterUploadView.as_view(), name="event-poster-upload"),
    re_path(
        r"^events/(?P<event_id>[^/]+)/upload-poster/?$",
        EventPosterUploadView.as_view(),
        name="event-upload-poster",
    ),
    re_path(r"^events/(?P<event_id>[^/]+)/posters?/?$", EventPostersListView.as_view(), name="event-posters-list"),
    re_path(r"^event-posters/?$", EventPostersListView.as_view(), name="event-posters-root-list"),
    re_path(
        r"^events/(?P<pk>[^/]+)/?$",
        EventViewSet.as_view({"get": "retrieve", "put": "update", "patch": "partial_update", "delete": "destroy"}),
        name="event-detail",
    ),
]
