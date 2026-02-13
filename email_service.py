import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Email configuration
SMTP_SERVER = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
SMTP_PORT = int(os.getenv('SMTP_PORT', '587'))
SMTP_EMAIL = os.getenv('SMTP_EMAIL', '')
SMTP_PASSWORD = os.getenv('SMTP_PASSWORD', '')
COLLEGE_NAME = os.getenv('COLLEGE_NAME', 'College')
COLLEGE_EMAIL = os.getenv('COLLEGE_EMAIL', SMTP_EMAIL)

# Initialize email service
email_enabled = bool(SMTP_EMAIL and SMTP_PASSWORD)
if email_enabled:
    print('✅ Email service initialized')
else:
    print('⚠️  Email credentials not configured - Email disabled')

def send_email(to_email, subject, body_html):
    """Send email via SMTP"""
    if not email_enabled:
        print(f'📧 Email (disabled): To {to_email}: {subject}')
        return False
    
    try:
        msg = MIMEMultipart('alternative')
        msg['From'] = f"{COLLEGE_NAME} <{SMTP_EMAIL}>"
        msg['To'] = to_email
        msg['Subject'] = subject
        
        html_part = MIMEText(body_html, 'html')
        msg.attach(html_part)
        
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_EMAIL, SMTP_PASSWORD)
            server.send_message(msg)
        
        print(f'✅ Email sent to {to_email}: {subject}')
        return True
    except Exception as e:
        print(f'❌ Email failed to {to_email}: {e}')
        return False

def send_parent_approval_email(parent_email, student_name, request_type, leave_date, leave_time, reason, token):
    """Send approval request email to parent"""
    approval_url = f"http://192.168.18.104:8080/parent-approve.html?token={token}"
    
    subject = f"Permission Request from {student_name}"
    
    body = f"""
    <html>
    <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
        <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #ddd; border-radius: 8px;">
            <h2 style="color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px;">
                🎓 {COLLEGE_NAME}
            </h2>
            
            <h3 style="color: #e74c3c;">Permission Request</h3>
            
            <div style="background: #f8f9fa; padding: 15px; border-radius: 5px; margin: 20px 0;">
                <p><strong>Student:</strong> {student_name}</p>
                <p><strong>Request Type:</strong> <span style="color: {'#e74c3c' if request_type == 'emergency' else '#3498db'}; font-weight: bold;">{request_type.upper()}</span></p>
                <p><strong>Leave Date:</strong> {leave_date}</p>
                <p><strong>Leave Time:</strong> {leave_time}</p>
                <p><strong>Reason:</strong> {reason}</p>
            </div>
            
            <div style="text-align: center; margin: 30px 0;">
                <a href="{approval_url}" style="display: inline-block; padding: 15px 40px; background: #27ae60; color: white; text-decoration: none; border-radius: 5px; font-weight: bold; font-size: 16px;">
                    Click Here to Approve/Reject
                </a>
            </div>
            
            <p style="color: #7f8c8d; font-size: 12px; margin-top: 20px;">
                This link will expire in 24 hours. If you did not expect this email, please ignore it.
            </p>
            
            <hr style="border: none; border-top: 1px solid #ddd; margin: 20px 0;">
            
            <p style="color: #95a5a6; font-size: 11px; text-align: center;">
                {COLLEGE_NAME} - Automated Permission System<br>
                Do not reply to this email.
            </p>
        </div>
    </body>
    </html>
    """
    
    return send_email(parent_email, subject, body)

def send_approval_notification_email(email, student_name, leave_date, leave_time):
    """Send approval confirmation email"""
    subject = f"Permission APPROVED - {student_name}"
    
    body = f"""
    <html>
    <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
        <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #ddd; border-radius: 8px;">
            <h2 style="color: #27ae60;">✅ Permission APPROVED</h2>
            
            <div style="background: #d4edda; padding: 15px; border-radius: 5px; border-left: 4px solid #27ae60; margin: 20px 0;">
                <p><strong>Student:</strong> {student_name}</p>
                <p><strong>Leave Date:</strong> {leave_date}</p>
                <p><strong>Leave Time:</strong> {leave_time}</p>
                <p style="color: #155724; font-weight: bold; margin-top: 15px;">
                    ⚠️ Keep this email for gate pass verification
                </p>
            </div>
            
            <p style="color: #7f8c8d; font-size: 12px;">
                This approval expires after the leave time.
            </p>
        </div>
    </body>
    </html>
    """
    
    return send_email(email, subject, body)

def send_rejection_notification_email(email, student_name, rejected_by, reason=None):
    """Send rejection notification email"""
    subject = f"Permission REJECTED - {student_name}"
    
    reason_text = f"<p><strong>Reason:</strong> {reason}</p>" if reason else ""
    
    body = f"""
    <html>
    <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
        <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #ddd; border-radius: 8px;">
            <h2 style="color: #e74c3c;">❌ Permission REJECTED</h2>
            
            <div style="background: #f8d7da; padding: 15px; border-radius: 5px; border-left: 4px solid #e74c3c; margin: 20px 0;">
                <p><strong>Student:</strong> {student_name}</p>
                <p><strong>Rejected by:</strong> {rejected_by}</p>
                {reason_text}
            </div>
            
            <p style="color: #721c24;">
                Your permission request has been rejected. Please contact your {rejected_by.lower()} for more information.
            </p>
        </div>
    </body>
    </html>
    """
    
    return send_email(email, subject, body)

def send_cancellation_notification_email(email, student_name):
    """Send cancellation notification email"""
    subject = f"Permission Request CANCELLED - {student_name}"
    
    body = f"""
    <html>
    <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
        <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #ddd; border-radius: 8px;">
            <h2 style="color: #f39c12;">⚠️ Request CANCELLED</h2>
            
            <div style="background: #fff3cd; padding: 15px; border-radius: 5px; border-left: 4px solid #f39c12; margin: 20px 0;">
                <p><strong>Student:</strong> {student_name}</p>
                <p>The permission request has been cancelled by the student.</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    return send_email(email, subject, body)
