from flask import current_app
from flask_mail import Message
from app import mail
import traceback
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import time

def send_email(to_email, subject, html_content):
    try:
        print(f"\n=== Sending email to: {to_email} ===")
        print("Attempting primary method (Flask-Mail)...")
        
        # Method 1: Flask-Mail
        msg = Message(
            subject,
            sender=('PPDB Online', current_app.config['MAIL_USERNAME']),  # Explicit sender
            recipients=[to_email]
        )
        msg.html = html_content
        
        # Add headers untuk menghindari spam filter
        msg.extra_headers = {
            'X-Priority': '1',
            'X-MSMail-Priority': 'High',
            'Importance': 'High',
            'X-Mailer': 'PPDB Online System'
        }
        
        # Retry mechanism
        max_retries = 3
        retry_delay = 2  # seconds
        
        for attempt in range(max_retries):
            try:
                mail.send(msg)
                print(f"Email successfully sent to {to_email}!")
                return True, "Email sent successfully"
            except Exception as retry_error:
                print(f"Attempt {attempt + 1} failed: {str(retry_error)}")
                if attempt < max_retries - 1:
                    print(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                    continue
                
                # If Flask-Mail fails, try direct SMTP
                print("\nTrying direct SMTP method...")
                try:
                    smtp = smtplib.SMTP(current_app.config['MAIL_SERVER'], 
                                      current_app.config['MAIL_PORT'])
                    smtp.starttls()
                    smtp.login(current_app.config['MAIL_USERNAME'],
                             current_app.config['MAIL_PASSWORD'])
                    
                    message = MIMEMultipart('alternative')
                    message['Subject'] = subject
                    message['From'] = current_app.config['MAIL_USERNAME']
                    message['To'] = to_email
                    message.attach(MIMEText(html_content, 'html'))
                    
                    smtp.send_message(message)
                    smtp.quit()
                    print("Email sent successfully via direct SMTP!")
                    return True, "Email sent via SMTP"
                    
                except Exception as smtp_error:
                    error_msg = f"Both email methods failed: {str(smtp_error)}"
                    print(error_msg)
                    return False, error_msg

    except Exception as e:
        error_trace = traceback.format_exc()
        print(f"\nFatal error in send_email:")
        print(f"Error: {str(e)}")
        print(f"Traceback:\n{error_trace}")
        return False, str(e)