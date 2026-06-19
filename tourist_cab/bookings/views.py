import json
import random
import logging
from datetime import timedelta, datetime

import requests

from django.conf                    import settings
from django.http                    import JsonResponse, HttpResponse
from django.utils                   import timezone
from django.views.decorators.csrf   import csrf_exempt
from django.views.decorators.http   import require_POST, require_GET
from django.shortcuts               import render, get_object_or_404

from .models import Booking, Car, Driver

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# WhatsApp helpers — Meta Cloud API
# ─────────────────────────────────────────────

def to_e164_digits(phone: str) -> str:
    phone = phone.strip().replace(" ", "").replace("-", "")
    if phone.startswith("whatsapp:"):
        phone = phone[9:]
    phone = phone.lstrip("+")
    if len(phone) == 10 and phone.isdigit():
        return f"91{phone}"
    return phone


def _graph_url():
    return f"https://graph.facebook.com/{settings.META_WABA_VERSION}/{settings.META_PHONE_NUMBER_ID}/messages"


def _headers():
    token = settings.META_WHATSAPP_TOKEN
    if not token or not token.isascii():
        raise RuntimeError(
            "META_WHATSAPP_TOKEN is missing or invalid in your .env"
        )
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }


def send_whatsapp_text(to_phone: str, body: str):
    payload = {
        "messaging_product": "whatsapp",
        "to": to_e164_digits(to_phone),
        "type": "text",
        "text": {"body": body},
    }
    r = requests.post(_graph_url(), headers=_headers(), json=payload, timeout=10)
    r.raise_for_status()
    return r.json()


def send_whatsapp_template(to_phone: str, template_name: str, body_params=None,
                            button_params=None, language_code="en"):
    components = []
    if body_params:
        components.append({
            "type": "body",
            "parameters": [{"type": "text", "text": str(p)} for p in body_params],
        })
    if button_params:
        for idx, value in enumerate(button_params):
            components.append({
                "type": "button",
                "sub_type": "url",
                "index": str(idx),
                "parameters": [{"type": "text", "text": str(value)}],
            })

    payload = {
        "messaging_product": "whatsapp",
        "to": to_e164_digits(to_phone),
        "type": "template",
        "template": {"name": template_name, "language": {"code": language_code}},
    }
    if components:
        payload["template"]["components"] = components

    r = requests.post(_graph_url(), headers=_headers(), json=payload, timeout=10)
    r.raise_for_status()
    return r.json()


# ─────────────────────────────────────────────
# Pages
# ─────────────────────────────────────────────

def home(request):
    return render(request, "bookings/home.html")

def book_ride(request):
    cars = Car.objects.all()
    return render(request, "bookings/book_ride.html", {"cars": cars})

def airport_taxi(request):
    return render(request, "bookings/home.html")

def outstation(request):
    return render(request, "bookings/outstation.html")

def rentals(request):
    return render(request, "bookings/rentals.html")

def driver_partner(request):
    return render(request, "bookings/driver_partner.html")

def contact(request):
    return render(request, "bookings/contact.html")

def packages(request):
    return render(request, "bookings/packages.html")


# ─────────────────────────────────────────────
# OTP: Send
# ─────────────────────────────────────────────

@require_POST
@csrf_exempt
def send_otp(request):
    try:
        data  = json.loads(request.body)
        phone = data.get("phone", "").strip()
        if not phone:
            return JsonResponse({"ok": False, "error": "Phone number missing."})

        otp = str(random.randint(100000, 999999))
        request.session[f"otp_{phone}"] = {
            "code":    otp,
            "expires": (timezone.now() + timedelta(minutes=5)).isoformat(),
        }

        if settings.DEBUG:
            print(f"\n{'='*40}")
            print(f"OTP for {phone}: {otp}")
            print(f"{'='*40}\n")
            return JsonResponse({"ok": True})

        send_whatsapp_template(phone, settings.META_TEMPLATE_OTP, body_params=[otp])
        return JsonResponse({"ok": True})

    except requests.HTTPError:
        logger.exception("send_otp HTTP error")
        return JsonResponse({"ok": False, "error": "Couldn't send OTP right now. Please try again."})
    except Exception:
        logger.exception("send_otp error")
        return JsonResponse({"ok": False, "error": "Couldn't send OTP right now. Please try again."})


# ─────────────────────────────────────────────
# OTP: Verify
# ─────────────────────────────────────────────

@require_POST
@csrf_exempt
def verify_otp(request):
    try:
        data  = json.loads(request.body)
        phone = data.get("phone", "").strip()
        otp   = data.get("otp",   "").strip()

        session_data = request.session.get(f"otp_{phone}")
        if not session_data:
            return JsonResponse({"ok": False, "error": "OTP not sent or expired. Please resend."})

        expires = timezone.datetime.fromisoformat(session_data["expires"])
        if timezone.now() > expires:
            return JsonResponse({"ok": False, "error": "OTP expired. Please resend."})

        if session_data["code"] != otp:
            return JsonResponse({"ok": False, "error": "Wrong OTP. Please try again."})

        request.session[f"otp_verified_{phone}"] = True
        del request.session[f"otp_{phone}"]
        return JsonResponse({"ok": True})

    except Exception:
        logger.exception("verify_otp error")
        return JsonResponse({"ok": False, "error": "Verification failed. Please try again."})


# ─────────────────────────────────────────────
# Submit Booking
# FIX: _notify_drivers தனியா try/except — WhatsApp fail ஆனாலும் booking save ஆகும்
# ─────────────────────────────────────────────

@require_POST
@csrf_exempt
def submit_booking(request):
    try:
        data  = json.loads(request.body)
        phone = data.get("phone", "").strip()

        if not request.session.get(f"otp_verified_{phone}"):
            return JsonResponse({"ok": False, "error": "Phone not verified."})

        date_str = data.get("date", "").strip()
        time_str = data.get("time", "").strip()
        if not date_str:
            return JsonResponse({"ok": False, "error": "Please select a date."})
        if not time_str:
            return JsonResponse({"ok": False, "error": "Please select a time."})

        car = Car.objects.filter(id=data.get("car_id")).first()

        booking = Booking.objects.create(
            name        = data.get("name", ""),
            phone       = phone,
            email       = data.get("email", ""),
            pickup      = data.get("pickup", ""),
            drop        = data.get("drop", ""),
            pickup_lat  = data.get("pickup_lat") or None,
            pickup_lon  = data.get("pickup_lon") or None,
            drop_lat    = data.get("drop_lat")   or None,
            drop_lon    = data.get("drop_lon")   or None,
            distance_km = float(data.get("distance_km", 0)),
            date        = date_str,
            time        = time_str,
            passengers  = int(data.get("passengers", 1)),
            luggage     = int(data.get("luggage", 0)),
            car         = car,
            total_fare  = float(data.get("total_fare", 0)),
            status      = "waiting",
        )

        # FIX: WhatsApp fail ஆனாலும் booking confirm ஆகும்
        try:
            _notify_drivers(booking)
        except Exception:
            logger.exception(f"_notify_drivers failed for booking #{booking.id} — booking saved anyway")

        return JsonResponse({"ok": True, "booking_id": booking.id})

    except Exception:
        logger.exception("submit_booking error")
        return JsonResponse({
            "ok": False,
            "error": "Couldn't complete your booking. Please try again.",
        })


# ─────────────────────────────────────────────
# Notify drivers
# ─────────────────────────────────────────────

def _notify_drivers(booking: Booking):
    drivers = Driver.objects.filter(is_available=True)
    if not drivers.exists():
        logger.warning(f"No available drivers for booking #{booking.id}")
        return

    # FIX: time — string "10:00" or time object — both handle பண்ணு
    if hasattr(booking.time, 'strftime'):
        booking_time = booking.time.strftime("%I:%M %p")
    elif booking.time:
        try:
            booking_time = datetime.strptime(str(booking.time), "%H:%M").strftime("%I:%M %p")
        except ValueError:
            booking_time = str(booking.time)
    else:
        booking_time = "TBD"

    # FIX: date — string "2026-06-20" or date object — both handle பண்ணு
    if hasattr(booking.date, 'strftime'):
        date_str = booking.date.strftime('%d-%m-%Y')
    elif booking.date:
        try:
            from datetime import date as date_type
            date_str = datetime.strptime(str(booking.date), "%Y-%m-%d").strftime("%d-%m-%Y")
        except ValueError:
            date_str = str(booking.date)
    else:
        date_str = "TBD"

    body_params = [
        booking.name,
        booking.phone,
        booking.pickup,
        booking.drop,
        f"{booking.distance_km:.1f} km",
        f"{date_str} {booking_time}",
        f"{booking.passengers} pax / {booking.luggage} bags",
        f"₹{booking.total_fare}",
    ]

    for driver in drivers:
        try:
            button_params = [
                f"{booking.id}/accept/?driver_id={driver.id}",
                f"{booking.id}/reject/?driver_id={driver.id}",
            ]
            send_whatsapp_template(
                driver.phone,
                settings.META_TEMPLATE_DRIVER_REQUEST,
                body_params=body_params,
                button_params=button_params,
            )
            logger.info(f"Driver #{driver.id} ({driver.name}) notified for booking #{booking.id}")
        except Exception:
            logger.exception(f"Failed to notify driver #{driver.id} for booking #{booking.id}")


# ─────────────────────────────────────────────
# Status polling
# ─────────────────────────────────────────────

@require_GET
def booking_status(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id)

    if booking.is_expired():
        booking.status = "cancelled"
        booking.save(update_fields=["status"])
        _notify_customer_cancelled(booking)

    response = {
        "ok":     True,
        "status": booking.status,
    }

    if booking.status == "confirmed" and booking.driver:
        d = booking.driver
        response.update({
            "driver_name":      d.name,
            "driver_phone":     d.phone,
            "car_name":         d.car.name        if d.car else "",
            "vehicle_number":   d.car.car_number  if d.car else "",
            "driver_photo_url": request.build_absolute_uri(d.photo.url) if d.photo else "",
            "car_photo_url":    request.build_absolute_uri(d.car.photo.url) if (d.car and d.car.photo) else "",
        })

    return JsonResponse(response)


# ─────────────────────────────────────────────
# Customer notifications
# ─────────────────────────────────────────────

def _notify_customer_cancelled(booking: Booking):
    try:
        send_whatsapp_text(
            booking.phone,
            f"🚖 TouristCab — Booking #{booking.id}\n\n"
            f"Sorry {booking.name}, no driver was available within 10 minutes.\n"
            f"Your booking has been *auto-cancelled*.\n\n"
            f"Our team will contact you shortly to reschedule. 🙏"
        )
    except Exception:
        logger.exception(f"Failed to notify customer of cancellation for booking #{booking.id}")


def _notify_customer_confirmed(booking: Booking):
    d = booking.driver
    car_info = f"{d.car.name} — {d.car.car_number}" if d.car else "details coming soon"
    try:
        send_whatsapp_template(
            booking.phone,
            settings.META_TEMPLATE_CUSTOMER_CONFIRMED,
            body_params=[
                booking.name,
                d.name,
                d.phone,
                car_info,
                booking.pickup,
                f"₹{booking.total_fare}",
            ],
        )
    except Exception:
        logger.exception(f"Failed to notify customer of confirmation for booking #{booking.id}")


# ─────────────────────────────────────────────
# Driver Action — Accept / Reject
# ─────────────────────────────────────────────

def driver_action(request, booking_id, action):
    booking = Booking.objects.filter(id=booking_id).first()
    if not booking:
        return HttpResponse("❌ Booking not found.", status=404)

    if booking.status != "waiting":
        return HttpResponse(
            f"⚠️ Booking #{booking_id} is already <b>{booking.status}</b>. No changes made.",
            content_type="text/html"
        )

    if action == "accept":
        driver_id = request.GET.get("driver_id")
        driver = None

        if driver_id:
            driver = Driver.objects.filter(id=driver_id, is_available=True).first()

        if not driver:
            driver = Driver.objects.filter(is_available=True).first()

        if not driver:
            return HttpResponse("❌ No available driver found.", status=400)

        booking.driver = driver
        booking.status = "confirmed"
        booking.save(update_fields=["driver", "status"])

        driver.is_available = False
        driver.save(update_fields=["is_available"])

        _notify_customer_confirmed(booking)
        logger.info(f"Booking #{booking_id} accepted by driver #{driver.id} ({driver.name})")

        return HttpResponse(f"""
            <html>
            <head><meta name="viewport" content="width=device-width, initial-scale=1"></head>
            <body style="font-family:sans-serif;text-align:center;padding:3rem;background:#f9f9f9;">
              <div style="max-width:400px;margin:auto;background:#fff;padding:2rem;border-radius:12px;box-shadow:0 2px 12px rgba(0,0,0,.08);">
                <h1 style="color:#22c55e;">✅ Ride Accepted!</h1>
                <p>Booking <b>#{booking_id}</b> confirmed.</p>
                <hr style="border:none;border-top:1px solid #eee;margin:1rem 0;">
                <p>👤 Customer : <b>{booking.name}</b></p>
                <p>📞 Phone    : {booking.phone}</p>
                <p>📍 Pickup   : {booking.pickup}</p>
                <p>🏁 Drop     : {booking.drop}</p>
                <p>💰 Fare     : ₹{booking.total_fare}</p>
              </div>
            </body></html>
        """, content_type="text/html")

    else:
        booking.status = "rejected"
        booking.save(update_fields=["status"])
        logger.info(f"Booking #{booking_id} rejected via driver link")

        return HttpResponse(f"""
            <html>
            <head><meta name="viewport" content="width=device-width, initial-scale=1"></head>
            <body style="font-family:sans-serif;text-align:center;padding:3rem;background:#f9f9f9;">
              <div style="max-width:400px;margin:auto;background:#fff;padding:2rem;border-radius:12px;box-shadow:0 2px 12px rgba(0,0,0,.08);">
                <h1 style="color:#ef4444;">❌ Ride Rejected</h1>
                <p>Booking <b>#{booking_id}</b> has been rejected.</p>
                <p style="color:#888;">The customer will be notified.</p>
              </div>
            </body></html>
        """, content_type="text/html")


# ─────────────────────────────────────────────
# Driver location
# ─────────────────────────────────────────────

def driver_location(request, booking_id):
    try:
        booking = Booking.objects.get(id=booking_id)
        driver  = booking.driver
        return JsonResponse({
            "ok":  True,
            "lat": float(driver.current_lat),
            "lon": float(driver.current_lon),
        })
    except Exception:
        return JsonResponse({"ok": False})