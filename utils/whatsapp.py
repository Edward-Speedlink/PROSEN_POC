import requests
import os
from config import WHATSAPP_PHONE_NUMBER_ID, WHATSAPP_TOKEN, CEO_PHONE

class WhatsAppService:
    def __init__(self):
        self.phone_number_id = WHATSAPP_PHONE_NUMBER_ID
        self.token = WHATSAPP_TOKEN
        self.base_url = f"https://graph.facebook.com/v17.0/{self.phone_number_id}/messages"
        
    def send_message(self, to_phone, message):
        """
        Send WhatsApp message to a phone number
        Phone number should be in format: 1234567890 (without country code prefix)
        """
        try:
            headers = {
                'Authorization': f'Bearer {self.token}',
                'Content-Type': 'application/json'
            }
            
            # Format phone number (add country code if needed)
            # Assuming Indian numbers - adjust as needed
            if not to_phone.startswith('91') and len(to_phone) == 10:
                to_phone = '91' + to_phone
            
            payload = {
                "messaging_product": "whatsapp",
                "to": to_phone,
                "type": "text",
                "text": {
                    "body": message
                }
            }
            
            response = requests.post(self.base_url, json=payload, headers=headers)
            
            if response.status_code == 200:
                print(f"✅ WhatsApp message sent to {to_phone}")
                return True
            else:
                print(f"❌ WhatsApp API error: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Error sending WhatsApp message: {str(e)}")
            return False
    
    def send_alert_message(self, to_phone, subject, details, alert_type="PLATE"):
        """
        Send formatted alert message via WhatsApp
        """
        if alert_type == "PLATE":
            message = f"""🚨 *SECURITY ALERT - License Plate Match*

*{subject}*

📋 *Details:*
{details}

📍 *Action Required:*
• Review attached evidence
• Check live feed
• Take appropriate action

_This is an automated alert from your security system_"""
        
        elif alert_type == "FACE":
            message = f"""👤 *SECURITY ALERT - Face Recognition Match*

*{subject}*

📋 *Details:*
{details}

📍 *Action Required:*
• Verify identity
• Review security footage
• Take appropriate action

_This is an automated alert from your security system_"""
        
        else:
            message = f"""🔔 *SECURITY ALERT*

*{subject}*

📋 *Details:*
{details}

_This is an automated alert from your security system_"""
        
        return self.send_message(to_phone, message)

# Create global instance
whatsapp_service = WhatsAppService()