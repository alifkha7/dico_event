"""Models for the core app.

Defines a custom ``User`` model based off Django's ``AbstractUser``
with a UUID primary key. This provides compatibility with other
applications that expect UUIDs instead of auto-incrementing integers.
"""

import uuid
from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Custom user model using a UUID primary key."""

    id = models.UUIDField(default=uuid.uuid4, unique=True, primary_key=True, editable=False)

    class Meta:
        db_table = 'users'

    def __str__(self) -> str:
        return self.username
