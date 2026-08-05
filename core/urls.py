"""URL routing for the core app."""

from django.urls import path
from . import views

urlpatterns = [
    path('users/', views.UserListCreateView.as_view(), name='user-list'),
    path('users/<uuid:pk>/', views.UserDetailView.as_view(), name='user-detail'),
    path('groups/', views.GroupListCreateView.as_view(), name='group-list'),
    path('groups/<int:pk>/', views.GroupDetailView.as_view(), name='group-detail'),
    path('assign-roles/', views.AssignRoleView.as_view(), name='assign-roles'),
]
