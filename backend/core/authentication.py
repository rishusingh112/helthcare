import datetime
import re
import jwt
from django.conf import settings
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.permissions import BasePermission
from core.models import User


def _parse_expire_delta(expire_str: str) -> datetime.timedelta:
    s = (expire_str or '30d').strip().lower()
    m = re.match(r'^(\d+)([dhms]?)$', s)
    if not m:
        return datetime.timedelta(days=30)
    val = int(m.group(1))
    unit = m.group(2) or 's'
    if unit == 'd':
        return datetime.timedelta(days=val)
    if unit == 'h':
        return datetime.timedelta(hours=val)
    if unit == 'm':
        return datetime.timedelta(minutes=val)
    return datetime.timedelta(seconds=val)


def generate_token(user_id: str) -> str:
    now = datetime.datetime.now(datetime.timezone.utc)
    exp = now + _parse_expire_delta(getattr(settings, 'JWT_EXPIRE', '30d'))
    payload = {
        'id': str(user_id),
        'iat': int(now.timestamp()),
        'exp': int(exp.timestamp()),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm='HS256')


class JWTAuthentication(BaseAuthentication):
    def authenticate(self, request):
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        if not auth_header.startswith('Bearer'):
            return None
        parts = auth_header.split(' ', 1)
        if len(parts) != 2 or not parts[1].strip():
            raise AuthenticationFailed('Not authorized, no token')

        token = parts[1].strip()
        try:
            decoded = jwt.decode(token, settings.JWT_SECRET, algorithms=['HS256'])
        except jwt.ExpiredSignatureError:
            raise AuthenticationFailed('Not authorized, token expired')
        except Exception:
            raise AuthenticationFailed('Not authorized, token failed')

        user_id = decoded.get('id') or decoded.get('_id')
        if not user_id:
            raise AuthenticationFailed('Not authorized, token failed')

        user = User.objects.filter(id=user_id).first()
        if not user or user.status == 'Inactive':
            raise AuthenticationFailed('User not found or inactive')

        return (user, token)

    def authenticate_header(self, request):
        return 'Bearer'


class IsAuthenticatedJWT(BasePermission):
    message = 'Not authorized, no token'

    def has_permission(self, request, view):
        return bool(request.user and getattr(request.user, 'is_authenticated', False))


def require_roles(*roles):
    class RolePermission(BasePermission):
        def has_permission(self, request, view):
            if not request.user or not getattr(request.user, 'is_authenticated', False):
                return False
            if request.user.role not in roles:
                self.message = f'User role {request.user.role} is not authorized to access this route'
                return False
            return True

    return RolePermission
