import uuid
from django.db import models
from core.models import User


class Event(models.Model):
    """An event that users can attend."""

    id = models.UUIDField(default=uuid.uuid4, unique=True, primary_key=True, editable=False)
    name = models.CharField(max_length=255)
    description = models.TextField()
    location = models.CharField(max_length=255)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    status = models.CharField(max_length=50)
    quota = models.IntegerField()
    category = models.CharField(max_length=100)
    organizer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='events')

    class Meta:
        db_table = 'events'

    def __str__(self) -> str:
        return self.name


class EventImage(models.Model):
    id = models.UUIDField(default=uuid.uuid4, unique=True, primary_key=True, editable=False)
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    image = models.ImageField()

    def __str__(self):
        return self.event.name

    class Meta:
        db_table = 'event_images'
