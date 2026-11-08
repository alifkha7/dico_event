import uuid

from django.db import models

from apps.tickets.models import Ticket
from apps.users.models import User


class Registration(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ticket = models.ForeignKey(Ticket, on_delete=models.PROTECT, related_name="registrations")
    user = models.ForeignKey(User, on_delete=models.PROTECT, related_name="registrations")

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
