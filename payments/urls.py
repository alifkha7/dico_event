from django.urls import path

from . import views

urlpatterns = [
    path("payments/", views.PaymentListCreateView.as_view(), name="payment-list"),
    path("payments/<uuid:pk>/", views.PaymentDetailView.as_view(), name="payment-detail"),
]
