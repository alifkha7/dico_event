import uuid

from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)

    class Meta:
        db_table = "users"
        verbose_name = "User"
        verbose_name_plural = "Users"

    def __str__(self):
        return self.username


class Event(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    description = models.TextField()
    location = models.CharField(max_length=255)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    status = models.CharField(max_length=50)
    quota = models.IntegerField()
    category = models.CharField(max_length=100)
    organizer = models.ForeignKey(User, on_delete=models.CASCADE, related_name="events")

    class Meta:
        db_table = "events"
        verbose_name = "Event"
        verbose_name_plural = "Events"
        indexes = [
            models.Index(fields=["start_time"]),
            models.Index(fields=["status"]),
            models.Index(fields=["category"]),
        ]

    def __str__(self):
        return self.name


class Ticket(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="tickets")
    name = models.CharField(max_length=255)
    price = models.IntegerField()
    sales_start = models.DateTimeField()
    sales_end = models.DateTimeField()
    quota = models.IntegerField()

    class Meta:
        db_table = "tickets"
        verbose_name = "Ticket"
        verbose_name_plural = "Tickets"

    def __str__(self):
        return self.name


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


class EventPoster(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="posters")
    image = models.CharField(max_length=500)

    class Meta:
        db_table = "event_posters"
        verbose_name = "Event Poster"
        verbose_name_plural = "Event Posters"

    def __str__(self):
        return f"Poster for {self.event.name}: {self.image}"
