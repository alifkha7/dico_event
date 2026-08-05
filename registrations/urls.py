from django.urls import path
from . import views

urlpatterns = [
    path('registrations/', views.RegistrationListCreateView.as_view(), name='registration-list'),
    path('registrations/<uuid:pk>/', views.RegistrationDetailView.as_view(), name='registration-detail'),
]