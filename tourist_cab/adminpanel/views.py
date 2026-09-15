from functools import wraps
from datetime import date
import re

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.utils import timezone
from django.db.models import Count, Q

from bookings.models import Driver, Car, Booking, Attendance
from .forms import DriverForm


def _generate_driver_email(name, exclude_id=None):
    """name@touristcab.com — appends a number if that email is already taken."""
    base = re.sub(r"[^a-z0-9]", "", name.lower()) or "driver"
    email = f"{base}@touristcab.com"
    n = 1
    qs = Driver.objects.filter(email__iexact=email)
    if exclude_id:
        qs = qs.exclude(id=exclude_id)
    while qs.exists():
        n += 1
        email = f"{base}{n}@touristcab.com"
        qs = Driver.objects.filter(email__iexact=email)
        if exclude_id:
            qs = qs.exclude(id=exclude_id)
    return email


# ─────────────────────────────────────────────
# Auth
# ─────────────────────────────────────────────

def admin_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not (request.user.is_authenticated and request.user.is_staff):
            messages.warning(request, "Please login as admin to continue.")
            return redirect("admin_login")
        return view_func(request, *args, **kwargs)
    return wrapper


def admin_login(request):
    if request.user.is_authenticated and request.user.is_staff:
        return redirect("admin_dashboard")

    if request.method == "POST":
        email = request.POST.get("email", "").strip()
        password = request.POST.get("password", "")
        user = authenticate(request, username=email, password=password)
        if user and user.is_staff:
            login(request, user)
            return redirect("admin_dashboard")
        messages.error(request, "Invalid admin email or password.")

    return render(request, "adminpanel/login.html")


def admin_logout(request):
    logout(request)
    return redirect("admin_login")


# ─────────────────────────────────────────────
# Dashboard
# ─────────────────────────────────────────────

@admin_required
def dashboard(request):
    stats = {
        "total_bookings":     Booking.objects.count(),
        "waiting":            Booking.objects.filter(status="waiting").count(),
        "confirmed":          Booking.objects.filter(status="confirmed").count(),
        "completed":          Booking.objects.filter(status="completed").count(),
        "no_driver":          Booking.objects.filter(status="no_driver").count(),
        "total_drivers":      Driver.objects.count(),
        "on_duty_drivers":    Driver.objects.filter(is_on_duty=True).count(),
        "available_drivers":  Driver.objects.filter(is_available=True, is_on_duty=True).count(),
    }
    recent_bookings = Booking.objects.order_by("-created_at")[:10]
    return render(request, "adminpanel/dashboard.html", {"stats": stats, "recent_bookings": recent_bookings})


# ─────────────────────────────────────────────
# Drivers
# ─────────────────────────────────────────────

@admin_required
def driver_list(request):
    drivers = Driver.objects.all().order_by("-created_at")
    return render(request, "adminpanel/driver_list.html", {"drivers": drivers})


@admin_required
def driver_add(request):
    if request.method == "POST":
        form = DriverForm(request.POST, request.FILES)
        if form.is_valid():
            data = form.cleaned_data
            email = _generate_driver_email(data["name"])
            driver = Driver(
                name=data["name"], phone=data["phone"],
                email=email, car=data["car"], rate_per_ride=data["rate_per_ride"],
                is_active=data["is_active"],
            )
            if data.get("photo"):
                driver.photo = data["photo"]
            driver.set_password(data["name"])   # password = driver's name, as requested
            driver.save()
            messages.success(
                request,
                f"Driver {driver.name} created. Login email: {email} — Password: {data['name']}"
            )
            return redirect("admin_driver_list")
    else:
        form = DriverForm()
    return render(request, "adminpanel/driver_form.html", {"form": form, "title": "Add Driver"})


@admin_required
def driver_edit(request, driver_id):
    driver = get_object_or_404(Driver, id=driver_id)
    if request.method == "POST":
        form = DriverForm(request.POST, request.FILES)
        if form.is_valid():
            data = form.cleaned_data
            name_changed = data["name"].strip().lower() != driver.name.strip().lower()
            driver.name = data["name"]
            driver.phone = data["phone"]
            driver.car = data["car"]
            driver.rate_per_ride = data["rate_per_ride"]
            driver.is_active = data["is_active"]
            if data.get("photo"):
                driver.photo = data["photo"]
            if name_changed:
                driver.email = _generate_driver_email(driver.name, exclude_id=driver.id)
            if data.get("reset_password"):
                driver.set_password(driver.name)
                messages.info(request, f"Password reset to: {driver.name}")
            driver.save()
            if name_changed:
                messages.success(request, f"Driver {driver.name} updated. New login email: {driver.email}")
            else:
                messages.success(request, f"Driver {driver.name} updated. Login email: {driver.email}")
            return redirect("admin_driver_list")
    else:
        form = DriverForm(initial={
            "name": driver.name, "phone": driver.phone,
            "car": driver.car, "rate_per_ride": driver.rate_per_ride, "is_active": driver.is_active,
        })
    return render(request, "adminpanel/driver_form.html", {"form": form, "title": f"Edit Driver — {driver.name}", "driver": driver})


@admin_required
def driver_toggle_active(request, driver_id):
    driver = get_object_or_404(Driver, id=driver_id)
    driver.is_active = not driver.is_active
    if not driver.is_active:
        driver.is_on_duty = False
        driver.is_available = False
    driver.save()
    messages.success(request, f"Driver {driver.name} is now {'active' if driver.is_active else 'deactivated'}.")
    return redirect("admin_driver_list")


# ─────────────────────────────────────────────
# Bookings
# ─────────────────────────────────────────────

@admin_required
def booking_list(request):
    status = request.GET.get("status", "")
    bookings = Booking.objects.all().order_by("-created_at")
    if status:
        bookings = bookings.filter(status=status)
    drivers = Driver.objects.filter(is_active=True)
    return render(request, "adminpanel/booking_list.html", {
        "bookings": bookings, "status": status, "drivers": drivers,
        "status_choices": Booking.STATUS_CHOICES,
    })


@admin_required
def booking_skip_to_next(request, booking_id):
    """Admin forces the current ride offer to move on to the next driver in queue."""
    booking = get_object_or_404(Booking, id=booking_id)
    if booking.driver:
        booking.rejected_by.add(booking.driver)
    next_driver = booking.assign_next_driver()
    if next_driver:
        messages.success(request, f"Booking #{booking.id} moved to driver {next_driver.name}.")
    else:
        messages.warning(request, f"Booking #{booking.id} — no more drivers available.")
    return redirect("admin_booking_list")


@admin_required
def booking_force_assign(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id)
    driver_id = request.POST.get("driver_id")
    driver = get_object_or_404(Driver, id=driver_id)
    booking.driver = driver
    booking.status = "waiting"
    booking.save(update_fields=["driver", "status"])
    messages.success(request, f"Booking #{booking.id} assigned to {driver.name}.")
    return redirect("admin_booking_list")


@admin_required
def booking_cancel(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id)
    booking.status = "cancelled"
    if booking.driver:
        booking.driver.is_available = True
        booking.driver.save(update_fields=["is_available"])
    booking.save(update_fields=["status"])
    messages.success(request, f"Booking #{booking.id} cancelled.")
    return redirect("admin_booking_list")


# ─────────────────────────────────────────────
# Attendance
# ─────────────────────────────────────────────

@admin_required
def attendance_report(request):
    records = Attendance.objects.select_related("driver").order_by("-check_in")[:200]
    return render(request, "adminpanel/attendance.html", {"records": records})


# ─────────────────────────────────────────────
# Salary
# ─────────────────────────────────────────────

@admin_required
def salary_report(request):
    today = timezone.localdate()
    month = int(request.GET.get("month", today.month))
    year = int(request.GET.get("year", today.year))

    rows = []
    for driver in Driver.objects.filter(is_active=True):
        completed = Booking.objects.filter(
            driver=driver, status="completed",
            created_at__year=year, created_at__month=month,
        ).count()
        salary = completed * float(driver.rate_per_ride)
        rows.append({"driver": driver, "rides": completed, "salary": salary})

    return render(request, "adminpanel/salary.html", {
        "rows": rows, "month": month, "year": year,
        "months": range(1, 13),
    })
