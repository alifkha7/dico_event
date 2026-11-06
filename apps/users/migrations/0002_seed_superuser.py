from django.contrib.auth.hashers import make_password
from django.db import migrations


def seed_superuser(apps, schema_editor):
    User = apps.get_model("users", "User")
    if not User.objects.filter(username="Aras").exists():
        User.objects.create(
            username="Aras",
            email="aras@dicoevent.com",
            password=make_password("1234qwer!@#$"),
            is_staff=True,
            is_superuser=True,
            is_active=True,
        )


def remove_superuser(apps, schema_editor):
    User = apps.get_model("users", "User")
    User.objects.filter(username="Aras").delete()


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_superuser, reverse_code=remove_superuser),
    ]
