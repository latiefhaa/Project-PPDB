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
        print("\n=== Email Sending Diagnostic ===")
        print(f"To: {to_email}")
        print(f"From: {current_app.config['MAIL_USERNAME']}")
        print(f"SMTP Server: {current_app.config['MAIL_SERVER']}")
        print(f"Port: {current_app.config['MAIL_PORT']}")
        print(f"TLS: {current_app.config['MAIL_USE_TLS']}")
        
        msg = Message(
            subject,
            sender=current_app.config['MAIL_DEFAULT_SENDER'],
            recipients=[to_email],
            html=html_content
        )
        
        # Add Gmail-specific headers
        msg.extra_headers = {
            'X-Priority': '1',
            'X-MSMail-Priority': 'High',
            'Importance': 'High',
            'X-Mailer': 'PPDB Online System',
            'Precedence': 'Bulk',
            'Reply-To': current_app.config['MAIL_USERNAME'],
            'Organization': 'PPDB Online'
        }
        
        try:
            print("\nTrying to send via Flask-Mail...")
            mail.send(msg)
            print("Email sent successfully via Flask-Mail!")
            return True, "Email sent successfully"
            
        except Exception as flask_error:
            print(f"\nFlask-Mail Error: {str(flask_error)}")
            print("Trying direct SMTP...")
            
            try:
                with smtplib.SMTP(current_app.config['MAIL_SERVER'], 587) as server:
                    server.set_debuglevel(1)  # Enable debug output
                    server.ehlo()
                    server.starttls()
                    server.ehlo()
                    
                    print("\nAttempting SMTP login...")
                    server.login(
                        current_app.config['MAIL_USERNAME'],
                        current_app.config['MAIL_PASSWORD']
                    )
                    print("SMTP login successful!")
                    
                    message = MIMEMultipart('alternative')
                    message['Subject'] = subject
                    message['From'] = f"PPDB Online <{current_app.config['MAIL_USERNAME']}>"
                    message['To'] = to_email
                    message.attach(MIMEText(html_content, 'html'))
                    
                    print(f"\nSending email to {to_email}...")
                    server.sendmail(
                        current_app.config['MAIL_USERNAME'],
                        to_email,
                        message.as_string()
                    )
                    print("Email sent successfully via direct SMTP!")
                    return True, "Email sent via SMTP"
                    
            except Exception as smtp_error:
                print(f"\nSMTP Error: {str(smtp_error)}")
                print(f"Full traceback:\n{traceback.format_exc()}")
                return False, f"SMTP failed: {str(smtp_error)}"
                
    except Exception as e:
        print(f"\nFatal Error: {str(e)}")
        print(f"Full traceback:\n{traceback.format_exc()}")
        return False, str(e)