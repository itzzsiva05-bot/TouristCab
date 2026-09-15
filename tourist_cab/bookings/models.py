from django.db import models
from django.utils import timezone
from django.contrib.auth.hashers import make_password, check_password
from datetime import timedelta


class Car(models.Model):
    name             = models.CharField(max_length=100)
    car_number       = models.CharField(max_length=20)
    rate_per_km      = models.DecimalField(max_digits=6, decimal_places=2)
    rate_per_km_pax2 = models.DecimalField(
        max_digits=6, decimal_places=2, null=True, blank=True,
        help_text="Optional — per-km rate when 2 passengers are selected (e.g. for bikes). "
                   "Leave blank to always charge rate_per_km regardless of passenger count."
    )
    base_fare        = models.DecimalField(max_digits=6, decimal_places=2, default=80)
    driver_allowance = models.DecimalField(max_digits=6, decimal_places=2, default=50)
    max_passengers   = models.PositiveSmallIntegerField(default=4)
    photo            = models.ImageField(upload_to="cars/", blank=True, null=True)

    def __str__(self):
        return f"{self.name} ({self.car_number})"


class Driver(models.Model):
    name          = models.CharField(max_length=100)
    phone         = models.CharField(max_length=20)   # WhatsApp number with country code
    email         = models.EmailField(unique=True, null=True, blank=True)   # login id (admin sets this)
    password      = models.CharField(max_length=128, blank=True)            # hashed, set by admin
    photo         = models.ImageField(upload_to="drivers/", blank=True, null=True)
    car           = models.ForeignKey(Car, on_delete=models.SET_NULL, null=True, blank=True)
    is_available  = models.BooleanField(default=True)     # free to receive a new ride
    is_active     = models.BooleanField(default=True)     # admin can disable/deactivate a driver
    is_on_duty    = models.BooleanField(default=False)     # attendance: currently checked-in
    current_lat   = models.FloatField(null=True, blank=True)
    current_lon   = models.FloatField(null=True, blank=True)
    rate_per_ride = models.DecimalField(max_digits=8, decimal_places=2, default=300)   # used for salary calc
    created_at    = models.DateTimeField(default=timezone.now)

    def set_password(self, raw_password):
        self.password = make_password(raw_password)

    def check_password(self, raw_password):
        if not self.password:
            return False
        return check_password(raw_password, self.password)

    def __str__(self):
        return f"{self.name} — {self.phone}"


class Attendance(models.Model):
    """One row per check-in. check_out is filled when the driver punches out."""
    driver     = models.ForeignKey(Driver, on_delete=models.CASCADE, related_name="attendance_records")
    date       = models.DateField(default=timezone.localdate)
    check_in   = models.DateTimeField(auto_now_add=True)
    check_out  = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-check_in"]

    def hours_worked(self):
        end = self.check_out or timezone.now()
        return round((end - self.check_in).total_seconds() / 3600, 2)

    def __str__(self):
        return f"{self.driver.name} — {self.date}"


class Booking(models.Model):
    STATUS_CHOICES = [
        ("waiting",   "Waiting for driver"),
        ("confirmed", "Driver confirmed"),
        ("cancelled", "Auto-cancelled"),
        ("rejected",  "Driver rejected"),
        ("no_driver", "No driver available"),
        ("completed", "Completed"),
    ]

    PAYMENT_CHOICES = [
        ("cash", "Cash"),
        ("upi",  "UPI"),
        ("card", "Card"),
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
    payment_method = models.CharField(max_length=10, choices=PAYMENT_CHOICES, default="cash")

    # Assignment — booking.driver is the driver the ride is CURRENTLY offered to
    # (or who finally accepted it, once status == "confirmed").
    driver       = models.ForeignKey(Driver, on_delete=models.SET_NULL, null=True, blank=True, related_name="bookings")
    rejected_by  = models.ManyToManyField(Driver, blank=True, related_name="rejected_bookings")
    status       = models.CharField(max_length=20, choices=STATUS_CHOICES, default="waiting")

    # Linked to the logged-in Customer (Google login) who made this booking, if any.
    customer     = models.ForeignKey("accounts.Customer", on_delete=models.SET_NULL, null=True, blank=True, related_name="bookings")

    # Timestamps
    created_at   = models.DateTimeField(auto_now_add=True)
    updated_at   = models.DateTimeField(auto_now=True)

    # OTP
    otp_code     = models.CharField(max_length=6, blank=True)
    otp_verified = models.BooleanField(default=False)

    def next_available_driver(self):
        """First on-duty, available driver who hasn't already rejected this ride."""
        return (
            Driver.objects.filter(is_active=True, is_on_duty=True, is_available=True)
            .exclude(id__in=self.rejected_by.values_list("id", flat=True))
            .order_by("id")
            .first()
        )

    def assign_next_driver(self):
        """Offer this ride to the next eligible driver, one at a time.
        Returns the driver offered, or None if nobody is left (booking marked no_driver)."""
        driver = self.next_available_driver()
        if driver:
            self.driver = driver
            self.status = "waiting"
            self.save(update_fields=["driver", "status"])
        else:
            self.driver = None
            self.status = "no_driver"
            self.save(update_fields=["driver", "status"])
        return driver

    def is_expired(self):
        """Returns True if booking has been waiting > 10 minutes."""
        return (
            self.status == "waiting"
            and timezone.now() > self.created_at + timedelta(minutes=10)
        )

    def __str__(self):
        return f"#{self.id} {self.name} → {self.drop} [{self.status}]"