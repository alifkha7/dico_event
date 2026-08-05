from django.urls import path
from . import views

urlpatterns = [
    path('tickets/', views.TicketListCreateView.as_view(), name='ticket-list'),
    path('tickets/<uuid:pk>/', views.TicketDetailView.as_view(), name='ticket-detail'),
]