from django.urls import re_path
from .views import (
    CustomTokenObtainPairView,
    CustomTokenRefreshView,
    UserViewSet,
    GroupViewSet,
    AssignRoleView,
)

urlpatterns = [
    re_path(r'^login/?$', CustomTokenObtainPairView.as_view(), name='login'),
    re_path(r'^token/?$', CustomTokenRefreshView.as_view(), name='token_refresh'),
    re_path(
        r'^users/?$',
        UserViewSet.as_view({'get': 'list', 'post': 'create'}),
        name='user-list'
    ),
    re_path(
        r'^users/(?P<pk>[^/]+)/?$',
        UserViewSet.as_view({
            'get': 'retrieve',
            'put': 'update',
            'patch': 'partial_update',
            'delete': 'destroy'
        }),
        name='user-detail'
    ),
    re_path(
        r'^groups/?$',
        GroupViewSet.as_view({'get': 'list', 'post': 'create'}),
        name='group-list'
    ),
    re_path(
        r'^groups/(?P<pk>[^/]+)/?$',
        GroupViewSet.as_view({
            'get': 'retrieve',
            'put': 'update',
            'patch': 'partial_update',
            'delete': 'destroy'
        }),
        name='group-detail'
    ),
    re_path(r'^assign-roles/?$', AssignRoleView.as_view(), name='assign-roles'),
]
