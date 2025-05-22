import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import current_app

def send_email(to_email, subject, html_content):
    try:
        # Email settings
        smtp_server = "smtp.gmail.com"
        smtp_port = 587
        sender_email = current_app.config['MAIL_USERNAME']
        sender_password = current_app.config['MAIL_PASSWORD']

        # Create message
        message = MIMEMultipart('alternative')
        message['Subject'] = subject
        message['From'] = sender_email
        message['To'] = to_email

        # Add HTML content
        html_part = MIMEText(html_content, 'html')
        message.attach(html_part)

        # Create SMTP session
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.send_message(message)
            
        return True, "Email sent successfully"

    except Exception as e:
        print(f"Failed to send email: {str(e)}")
        return False, str(e)