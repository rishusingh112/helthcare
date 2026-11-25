import datetime
import smtplib
from email.message import EmailMessage
from urllib.parse import quote
from django.conf import settings
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime
from core.models import AuditLog


def is_smtp_configured() -> bool:
    return bool(settings.SMTP_USER and settings.SMTP_PASS)


def build_approval_link(token: str) -> str:
    frontend = (settings.FRONTEND_URL or 'http://localhost:5173').rstrip('/')
    if frontend:
        return f'{frontend}/approve?token={quote(token)}'
    base = (settings.APPROVAL_BASE_URL or 'http://localhost:5000').rstrip('/')
    return f'{base}/api/approvals/approve/{quote(token)}'


def _send_smtp_mail(to: str, subject: str, body: str) -> bool:
    if not is_smtp_configured():
        return False
    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From'] = settings.SMTP_FROM or settings.SMTP_USER
    msg['To'] = to
    msg.set_content(body)

    if settings.SMTP_SECURE:
        with smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10) as server:
            server.login(settings.SMTP_USER, settings.SMTP_PASS)
            server.send_message(msg)
    else:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10) as server:
            server.starttls()
            server.login(settings.SMTP_USER, settings.SMTP_PASS)
            server.send_message(msg)
    return True


def send_approval_email(to: str, subject: str, token: str, intro: str = '') -> dict:
    link = build_approval_link(token)
    if not is_smtp_configured():
        print(
            '[email] SMTP_USER / SMTP_PASS not set — approval email not sent. Copy this link for the approver:',
            link,
        )
        return {'link': link, 'emailSent': False}

    body = '\n'.join([
        intro or 'Approval requested.',
        '',
        f'Approve here: {link}',
        '',
        'If you did not request this, ignore this email.',
    ])
    try:
        _send_smtp_mail(to, subject, body)
        return {'link': link, 'emailSent': True}
    except Exception as exc:
        print(f'[email] Failed to send approval email: {exc}')
        return {'link': link, 'emailSent': False}


def send_password_reset_email(to: str, reset_url: str) -> dict:
    if not is_smtp_configured():
        print('[email] SMTP not configured. Password reset link:', reset_url)
        return {'emailSent': False}

    body = '\n'.join([
        'You requested a password reset.',
        '',
        'Please click the link below to reset your password:',
        reset_url,
        '',
        'If you did not request this, please ignore this email.',
    ])
    try:
        _send_smtp_mail(to, 'Password Reset Request', body)
        return {'emailSent': True}
    except Exception as exc:
        print(f'[email] Failed to send reset email: {exc}')
        return {'emailSent': False}


def parse_flexible_datetime(value) -> datetime.datetime | None:
    if value is None or value == '':
        return None
    if isinstance(value, datetime.datetime):
        dt = value
    elif isinstance(value, datetime.date):
        dt = datetime.datetime.combine(value, datetime.time.min)
    else:
        s = str(value).strip()
        dt = parse_datetime(s)
        if dt is None:
            d = parse_date(s[:10])
            if d is None:
                return None
            dt = datetime.datetime.combine(d, datetime.time.min)
    if timezone.is_naive(dt):
        dt = timezone.make_aware(dt, datetime.timezone.utc)
    return dt


def sanitize_body_for_audit(data):
    if not isinstance(data, dict):
        return {}
    cleaned = {}
    for k, v in data.items():
        if k.lower() in ('password', 'token', 'refreshtoken'):
            cleaned[k] = '***'
        else:
            cleaned[k] = v
    return cleaned


def log_audit(request, action: str, resource: str, user=None):
    try:
        ip = request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')[0].strip() or request.META.get('REMOTE_ADDR')
        body = {}
        try:
            body = sanitize_body_for_audit(request.data)
        except Exception:
            pass
        AuditLog.objects.create(
            user=user or (request.user if getattr(request.user, 'is_authenticated', False) else None),
            action=action,
            resource=resource,
            details={
                'method': request.method,
                'url': request.get_full_path(),
                'body': body,
                'query': dict(request.query_params) if hasattr(request, 'query_params') else {},
            },
            ip_address=ip,
        )
    except Exception as exc:
        print(f'Audit Log Error: {exc}')
