from twilio.rest import Client
from django.conf import settings


def send_whatsapp_booking(phone, data):
    """
    Booking confirm ஆனதும் customer-க்கு WhatsApp message அனுப்பு.
    data = {
        'name': ..., 'pickup': ..., 'drop': ...,
        'date': ..., 'time': ..., 'car': ..., 'driver': ...
    }
    """

    # Google Maps link — pickup location
    pickup_encoded = data['pickup'].replace(' ', '+')
    maps_link = f"https://www.google.com/maps/search/?api=1&query={pickup_encoded}"

    message = f"""✅ *TouristCab Booking Confirmed!*

👤 Name: {data['name']}
📍 Pickup: {data['pickup']}
🏁 Drop: {data['drop']}
📅 Date: {data['date']}
⏰ Time: {data['time']}
🚗 Car: {data.get('car', 'Assigned')}
👨‍✈️ Driver: {data.get('driver', 'Will be assigned soon')}

📌 Pickup Location:
{maps_link}

For support: Call/WhatsApp us anytime.
Thank you for choosing TouristCab! 🙏"""

    try:
        client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)

        client.messages.create(
            from_=settings.TWILIO_WHATSAPP_FROM,
            to=f'whatsapp:+91{phone}',
            body=message
        )
        return True

    except Exception as e:
        print(f"WhatsApp error: {e}")
        return False
