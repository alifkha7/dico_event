import uuid

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("registrations", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Payment",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("payment_method", models.CharField(max_length=100)),
                ("payment_status", models.CharField(max_length=100)),
                ("amount_paid", models.IntegerField()),
                (
                    "registration",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="payments",
                        to="registrations.registration",
                    ),
                ),
            ],
            options={
                "verbose_name": "Payment",
                "verbose_name_plural": "Payments",
                "db_table": "payments",
            },
        ),
    ]
