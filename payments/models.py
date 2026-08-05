import uuid

from django.db import models

from registrations.models import Registration


class Payment(models.Model):
    """Payment for a registration."""

    id = models.UUIDField(default=uuid.uuid4, unique=True, primary_key=True, editable=False)
    registration = models.ForeignKey(Registration, on_delete=models.CASCADE)
    payment_method = models.CharField(max_length=50)
    payment_status = models.CharField(max_length=50)
    amount_paid = models.IntegerField()

    class Meta:
        db_table = "payments"

    def __str__(self) -> str:
        return f"{self.registration} - {self.payment_status}"
