from django.contrib import admin
from django.conf    import settings

from .models        import Car, Driver, Booking
from .views          import send_whatsapp_template, send_whatsapp_text, _notify_customer_confirmed


# ── Car Admin ──────────────────────────────────────────────────────────────────

@admin.register(Car)
class CarAdmin(admin.ModelAdmin):
    list_display  = ("name", "car_number", "rate_per_km")
    search_fields = ("name", "car_number")


# ── Driver Admin ───────────────────────────────────────────────────────────────

@admin.register(Driver)
class DriverAdmin(admin.ModelAdmin):
    list_display  = ("name", "phone", "is_available")
    list_filter   = ("is_available",)
    search_fields = ("name", "phone")
    list_editable = ("is_available",)

    def save_model(self, request, obj, form, change):
        is_new = obj.pk is None
        super().save_model(request, obj, form, change)

        # புதுசா add ஆன driver-க்கு welcome message (Meta template)
        if is_new:
            try:
                send_whatsapp_template(
                    to_phone      = obj.phone,
                    template_name = settings.META_TEMPLATE_DRIVER_WELCOME,
                    body_params   = [obj.name],
                )
            except Exception as e:
                self.message_user(
                    request,
                    f"⚠️ Driver saved, but WhatsApp welcome failed: {e}",
                    level="warning",
                )


# ── Booking Admin ──────────────────────────────────────────────────────────────

@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):

    # ── Display helpers ────────────────────────────────────────────────────────

    @admin.display(description="Driver name")
    def driver_name(self, obj):
        return obj.driver.name if obj.driver else "—"

    @admin.display(description="Driver phone")
    def driver_phone(self, obj):
        return obj.driver.phone if obj.driver else "—"

    @admin.display(description="Vehicle")
    def vehicle_number(self, obj):
        return obj.car.car_number if obj.car else "—"

    # ── List view ──────────────────────────────────────────────────────────────

    list_display = (
        "id", "name", "phone",
        "pickup", "drop", "date", "time",
        "driver_name", "driver_phone",
        "total_fare", "status", "created_at",
    )
    list_filter   = ("status", "date")
    search_fields = ("name", "phone", "pickup", "drop")
    raw_id_fields = ("driver", "car")
    # FIX: status நீக்கினோம் list_editable-ல் இருந்து — neraya raw status change panna
    # driver unavailable-ஆவது, customer-க்கு WhatsApp போவது மாதிரி side-effects miss ஆகும்.
    # அதுக்கு பதிலா கீழே இருக்கற accept_bookings / reject_bookings actions-ஐ use பண்ணுங்க.

    readonly_fields = ("created_at",)

    actions = ["accept_bookings", "reject_bookings"]

    # FIX: date & time — optional in admin (null=True in model-ல் போட்டிருந்தா)
    # இல்லன்னா இங்கே required=False பண்றோம் → IntegrityError போகும்
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        for field in ("date", "time"):
            if field in form.base_fields:
                form.base_fields[field].required = False
        return form

    fieldsets = (
        ("Customer Details", {
            "fields": ("name", "phone", "email"),
        }),
        ("Trip Details", {
            "fields": ("pickup", "drop", "distance_km", "date", "time", "passengers", "luggage"),
        }),
        ("Assignment", {
            "fields": ("driver", "car"),
        }),
        ("Fare & Status", {
            "fields": ("total_fare", "status"),
        }),
        ("Tracking", {
            "fields": ("created_at",),
        }),
    )

    # ── Save hook — driver assign ஆனதும் WhatsApp அனுப்பு ─────────────────────

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)

        # Admin-ல் driver assign பண்ணி status "waiting"-ஆ இருக்கும்போது மட்டும்
        if change and obj.driver and obj.status == "waiting":
            base_url   = getattr(settings, "SITE_URL", "http://127.0.0.1:8000")
            accept_url = f"{base_url}/bookings/driver-action/{obj.id}/accept/?driver_id={obj.driver.id}"
            reject_url = f"{base_url}/bookings/driver-action/{obj.id}/reject/?driver_id={obj.driver.id}"

            # Date / time — None-ஆ இருந்தா safe fallback
            date_str = obj.date.strftime("%d-%m-%Y") if obj.date else "TBD"
            time_str = obj.time.strftime("%I:%M %p")  if obj.time else "TBD"

            body_params = [
                obj.name,
                obj.phone,
                obj.pickup,
                obj.drop,
                f"{obj.distance_km:.1f} km",
                f"{date_str} {time_str}",
                f"{obj.passengers} pax / {obj.luggage} bags",
                f"₹{obj.total_fare}",
            ]
            button_params = [
                f"{obj.id}/accept/?driver_id={obj.driver.id}",
                f"{obj.id}/reject/?driver_id={obj.driver.id}",
            ]

            try:
                send_whatsapp_template(
                    to_phone      = obj.driver.phone,
                    template_name = settings.META_TEMPLATE_DRIVER_REQUEST,
                    body_params   = body_params,
                    button_params = button_params,
                )
                self.message_user(
                    request,
                    f"✅ WhatsApp sent to driver {obj.driver.name} ({obj.driver.phone})",
                )
            except Exception as e:
                self.message_user(
                    request,
                    f"⚠️ Booking saved, but WhatsApp to driver failed: {e}",
                    level="warning",
                )

    # ── Admin actions — Accept / Reject directly from the admin panel ─────────
    # Staff workflow:
    #   1. Open the booking, assign a "driver" in the Assignment section, Save.
    #      (this fires the WhatsApp request to that driver, same as before)
    #   2. If you don't want to wait for the driver to tap Accept on WhatsApp,
    #      select the booking's checkbox in the list view and run "Accept
    #      selected booking(s)" below — this confirms it immediately, marks
    #      the driver unavailable, and sends the customer their confirmation
    #      WhatsApp, exactly like the driver_action() view does.

    @admin.action(description="✅ Accept selected booking(s) — confirm with assigned driver")
    def accept_bookings(self, request, queryset):
        confirmed, skipped_no_driver, skipped_status = 0, 0, 0

        for booking in queryset:
            if booking.status != "waiting":
                skipped_status += 1
                continue

            if not booking.driver:
                skipped_no_driver += 1
                continue

            driver = booking.driver
            booking.status = "confirmed"
            booking.save(update_fields=["status"])

            driver.is_available = False
            driver.save(update_fields=["is_available"])

            try:
                _notify_customer_confirmed(booking)
            except Exception as e:
                self.message_user(
                    request,
                    f"⚠️ Booking #{booking.id} confirmed, but customer WhatsApp failed: {e}",
                    level="warning",
                )

            confirmed += 1

        if confirmed:
            self.message_user(request, f"✅ {confirmed} booking(s) confirmed & customer notified.")
        if skipped_no_driver:
            self.message_user(
                request,
                f"⚠️ {skipped_no_driver} booking(s) skipped — assign a driver first (Assignment section), then save before accepting.",
                level="warning",
            )
        if skipped_status:
            self.message_user(
                request,
                f"⏭️ {skipped_status} booking(s) skipped — not in 'waiting' status.",
                level="warning",
            )

    @admin.action(description="❌ Reject selected booking(s)")
    def reject_bookings(self, request, queryset):
        updated = queryset.filter(status="waiting").update(status="rejected")
        skipped = queryset.count() - updated
        self.message_user(request, f"❌ {updated} booking(s) rejected.")
        if skipped:
            self.message_user(
                request,
                f"⏭️ {skipped} booking(s) skipped — not in 'waiting' status.",
                level="warning",
            )