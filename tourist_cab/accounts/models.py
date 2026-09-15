from django.db import models
from django.utils import timezone


class Customer(models.Model):
    """A customer who signed in with Google — no password, session based."""
    name       = models.CharField(max_length=120)
    email      = models.EmailField(unique=True)
    photo_url  = models.URLField(blank=True)
    google_sub = models.CharField(max_length=64, unique=True)   # Google's unique user id
    phone      = models.CharField(max_length=20, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.name} <{self.email}>"
