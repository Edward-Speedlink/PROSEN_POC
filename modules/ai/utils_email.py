# utils/email.py
import smtplib
from email.message import EmailMessage
from config import EMAIL_SERVER, EMAIL_PORT, EMAIL_USERNAME, EMAIL_PASSWORD, CEO_EMAIL
import os

def send_email(subject, body, to=None, attachments=None, html=False):
    if to is None:
        to = CEO_EMAIL

    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From'] = EMAIL_USERNAME
    msg['To'] = to

    if html:
        msg.set_content("HTML email")
        msg.add_alternative(body, subtype='html')
    else:
        msg.set_content(body)

    if attachments:
        for path in attachments:
            if os.path.exists(path):
                with open(path, "rb") as f:
                    file_data = f.read()
                    filename = os.path.basename(path)
                msg.add_attachment(file_data, maintype='image', subtype='jpeg', filename=filename)

    try:
        with smtplib.SMTP(EMAIL_SERVER, EMAIL_PORT) as server:
            server.starttls()
            server.login(EMAIL_USERNAME, EMAIL_PASSWORD)
            server.send_message(msg)
        print(f"Email sent successfully to {to}")
    except Exception as e:
        print(f"Failed to send email: {e}")









# # utils_email.py
# import smtplib, os
# from email.message import EmailMessage

# def send_email(subject, body, to, attachments=None, html=False):
#     msg = EmailMessage()
#     msg['Subject'] = subject
#     msg['From'] = "Speedlink Hi-tech solutions limited"
#     msg['To'] = to

#     if html:
#         msg.set_content("This is a HTML email. Please view in HTML mode.")
#         msg.add_alternative(body, subtype='html')  # This sends HTML version
#     else:
#         msg.set_content(body)

#     if attachments:
#         for path in attachments:
#             if os.path.exists(path):
#                 with open(path, "rb") as f:
#                     file_data = f.read()
#                     filename = os.path.basename(path)
#                 msg.add_attachment(file_data, maintype='image', subtype='jpeg', filename=filename)

#     try:
#         with smtplib.SMTP('localhost') as s:
#             s.send_message(msg)
#         print(f"Email sent to {to}")
#     except Exception as e:
#         print(f"Failed to send email: {e}")
