from django import forms
from bookings.models import Driver, Car


class DriverForm(forms.Form):
    name          = forms.CharField(max_length=100, help_text="Login email & password are generated automatically from this name.")
    phone         = forms.CharField(max_length=20)
    car           = forms.ModelChoiceField(queryset=Car.objects.all(), required=False)
    rate_per_ride = forms.DecimalField(max_digits=8, decimal_places=2, initial=300)
    photo         = forms.ImageField(required=False)
    is_active     = forms.BooleanField(required=False, initial=True)
    reset_password = forms.BooleanField(
        required=False,
        label="Reset password back to driver's name",
        help_text="Only used when editing an existing driver.",
    )
