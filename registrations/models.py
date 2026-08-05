import uuid
from django.db import models
from core.models import User
from tickets.models import Ticket

class Registration(models.Model):
    """A user's registration for a ticket."""

    id = models.UUIDField(default=uuid.uuid4, unique=True, primary_key=True, editable=False)
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    is_reminder_sent = models.BooleanField(default=False)

    class Meta:
        db_table = 'registrations'

    def __str__(self) -> str:
        return f'{self.user.username} - {self.ticket}'