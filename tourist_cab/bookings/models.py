from django.db import models
from django.utils import timezone
from datetime import timedelta


class Car(models.Model):
    name         = models.CharField(max_length=100)
    car_number   = models.CharField(max_length=20)
    rate_per_km  = models.DecimalField(max_digits=6, decimal_places=2)
    photo        = models.ImageField(upload_to="cars/", blank=True, null=True)

    def __str__(self):
        return f"{self.name} ({self.car_number})"


class Driver(models.Model):
    name         = models.CharField(max_length=100)
    phone        = models.CharField(max_length=20)   # WhatsApp number with country code
    photo        = models.ImageField(upload_to="drivers/", blank=True, null=True)
    car          = models.ForeignKey(Car, on_delete=models.SET_NULL, null=True, blank=True)
    is_available = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} — {self.phone}"


class Booking(models.Model):
    STATUS_CHOICES = [
        ("waiting",   "Waiting for driver"),
        ("confirmed", "Driver confirmed"),
        ("cancelled", "Auto-cancelled"),
        ("rejected",  "Driver rejected"),
        ("completed", "Completed"),
    ]

    # Customer
    name         = models.CharField(max_length=100)
    phone        = models.CharField(max_length=20)
    email        = models.EmailField(blank=True)

    # Route
    pickup       = models.TextField()
    drop         = models.TextField()
    pickup_lat   = models.FloatField(null=True, blank=True)
    pickup_lon   = models.FloatField(null=True, blank=True)
    drop_lat     = models.FloatField(null=True, blank=True)
    drop_lon     = models.FloatField(null=True, blank=True)
    distance_km  = models.FloatField(default=0)

    # Trip
    # models.py — Booking model-ல் date & time field இப்படி மாத்து
    date = models.DateField(null=True, blank=True)
    time = models.TimeField(null=True, blank=True)
    passengers   = models.IntegerField(default=1)
    luggage      = models.IntegerField(default=0)

    # Car & Fare
    car          = models.ForeignKey(Car, on_delete=models.SET_NULL, null=True, blank=True)
    total_fare   = models.DecimalField(max_digits=8, decimal_places=2, default=0)

    # Assignment
    driver       = models.ForeignKey(Driver, on_delete=models.SET_NULL, null=True, blank=True)
    status       = models.CharField(max_length=20, choices=STATUS_CHOICES, default="waiting")

    # Timestamps
    created_at   = models.DateTimeField(auto_now_add=True)
    updated_at   = models.DateTimeField(auto_now=True)

    # OTP
    otp_code     = models.CharField(max_length=6, blank=True)
    otp_verified = models.BooleanField(default=False)

    def is_expired(self):
        """Returns True if booking has been waiting > 10 minutes."""
        return (
            self.status == "waiting"
            and timezone.now() > self.created_at + timedelta(minutes=10)
        )

    def __str__(self):
        return f"#{self.id} {self.name} → {self.drop} [{self.status}]"