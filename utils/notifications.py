from utils.email import send_email
from utils.whatsapp import whatsapp_service
from config import CEO_EMAIL, CEO_PHONE

class NotificationService:
    def __init__(self):
        pass
    
    def send_security_alert(self, subject, body, alert_type="PLATE", 
                           attachments=None, html=False, 
                           methods=['email', 'whatsapp']):
        """
        Send security alert via multiple channels
        
        Parameters:
        - subject: Alert subject
        - body: Alert body/details
        - alert_type: "PLATE", "FACE", or "GENERAL"
        - attachments: List of file paths
        - html: Whether email body is HTML
        - methods: List of notification methods ['email', 'whatsapp']
        """
        results = {
            'email_sent': False,
            'whatsapp_sent': False,
            'email_error': None,
            'whatsapp_error': None
        }
        
        # Send email
        if 'email' in methods and CEO_EMAIL:
            try:
                send_email(
                    subject=subject,
                    body=body,
                    to=CEO_EMAIL,
                    attachments=attachments,
                    html=html
                )
                results['email_sent'] = True
                print(f"✅ Email alert sent to {CEO_EMAIL}")
            except Exception as e:
                results['email_error'] = str(e)
                print(f"❌ Failed to send email: {e}")
        
        # Send WhatsApp
        if 'whatsapp' in methods and CEO_PHONE:
            try:
                whatsapp_service.send_alert_message(
                    to_phone=CEO_PHONE,
                    subject=subject,
                    details=body,
                    alert_type=alert_type
                )
                results['whatsapp_sent'] = True
            except Exception as e:
                results['whatsapp_error'] = str(e)
        
        return results

# Global instance
notification_service = NotificationService()