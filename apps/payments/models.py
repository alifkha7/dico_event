import uuid

from django.db import models

from apps.registrations.models import Registration

__all__ = ["Payment"]


class Payment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    registration = models.ForeignKey(Registration, on_delete=models.PROTECT, related_name="payments")
    payment_method = models.CharField(max_length=100)
    payment_status = models.CharField(max_length=100)
    amount_paid = models.IntegerField()

    class Meta:
        db_table = "payments"
        verbose_name = "Payment"
        verbose_name_plural = "Payments"

    @property
    def user(self):
        """Shortcut property to access the registrant's User instance."""
        return self.registration.user

    @property
    def user_id(self):
        """Shortcut property to access the registrant's user_id without chaining through registration."""
        return self.registration.user_id

    def __str__(self):
        return f"Payment {self.id} - {self.payment_status}"
