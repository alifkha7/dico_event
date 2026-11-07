import uuid

from django.db import models

from apps.events.models import Event, EventPoster
from apps.tickets.models import Ticket
from apps.users.models import User

__all__ = [
    "Event",
    "EventPoster",
    "Payment",
    "Registration",
    "Ticket",
]


class Registration(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name="registrations")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="registrations")

    class Meta:
        db_table = "registrations"
        verbose_name = "Registration"
        verbose_name_plural = "Registrations"

    @property
    def event(self):
        """Shortcut property to access the event associated with this registration's ticket."""
        return self.ticket.event

    def __str__(self):
        return f"Registration {self.id}"


class Payment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    registration = models.ForeignKey(Registration, on_delete=models.CASCADE, related_name="payments")
    payment_method = models.CharField(max_length=100)
    payment_status = models.CharField(max_length=100)
    amount_paid = models.IntegerField()

    class Meta:
        db_table = "payments"
        verbose_name = "Payment"
        verbose_name_plural = "Payments"

    @property
    def user_id(self):
        """Shortcut property to access the registrant's user_id without chaining through registration."""
        return self.registration.user_id

    def __str__(self):
        return f"Payment {self.id} - {self.payment_status}"
