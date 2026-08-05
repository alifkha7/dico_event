import uuid

from django.db import models

from events.models import Event


class Ticket(models.Model):
    """Ticket type for an event."""

    id = models.UUIDField(default=uuid.uuid4, unique=True, primary_key=True, editable=False)
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    price = models.IntegerField()
    sales_start = models.DateTimeField()
    sales_end = models.DateTimeField()
    quota = models.IntegerField()

    class Meta:
        db_table = "tickets"

    def __str__(self) -> str:
        return f"{self.event.name} - {self.name}"
