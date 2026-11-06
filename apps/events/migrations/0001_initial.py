import uuid

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("users", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Event",
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
                ("name", models.CharField(max_length=255)),
                ("description", models.TextField()),
                ("location", models.CharField(max_length=255)),
                ("start_time", models.DateTimeField()),
                ("end_time", models.DateTimeField()),
                ("status", models.CharField(max_length=50)),
                ("quota", models.IntegerField()),
                ("category", models.CharField(max_length=100)),
                (
                    "organizer",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="events",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Event",
                "verbose_name_plural": "Events",
                "db_table": "events",
                "indexes": [
                    models.Index(fields=["start_time"], name="events_start_t_4e5265_idx"),
                    models.Index(fields=["status"], name="events_status_8890b6_idx"),
                    models.Index(fields=["category"], name="events_categor_a7129c_idx"),
                ],
            },
        ),
        migrations.CreateModel(
            name="EventPoster",
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
                ("image", models.CharField(max_length=500)),
                (
                    "event",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="posters",
                        to="events.event",
                    ),
                ),
            ],
            options={
                "verbose_name": "Event Poster",
                "verbose_name_plural": "Event Posters",
                "db_table": "event_posters",
            },
        ),
    ]
