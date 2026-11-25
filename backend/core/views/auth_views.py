import datetime
import hashlib
import secrets
from django.conf import settings
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from core.models import User, Patient, Doctor, ApprovalRequest
from core.authentication import generate_token, IsAuthenticatedJWT
from core.serializers import serialize_user, serialize_patient, serialize_doctor
from core.utils import send_approval_email, send_password_reset_email, parse_flexible_datetime, log_audit


def _approval_extras(email_sent: bool, link: str) -> dict:
    if email_sent or not settings.DEBUG:
        return {}
    return {
        'approvalLink': link,
        'devNote': (
            'Email not sent (SMTP_USER/SMTP_PASS missing). Open approvalLink in a browser to approve, '
            'or add Gmail SMTP to backend/.env.'
        ),
    }


def _extract_patient_kwargs(data: dict) -> dict:
    dob = parse_flexible_datetime(data.get('dob')) or timezone.now()
    return {
        'first_name': data.get('firstName', ''),
        'last_name': data.get('lastName', ''),
        'dob': dob,
        'gender': data.get('gender', 'Other'),
        'contact_number': data.get('contactNumber', ''),
        'address': data.get('address'),
        'avatar': data.get('avatar'),
        'blood_group': data.get('bloodGroup'),
        'allergies': data.get('allergies') or [],
        'emergency_contact': data.get('emergencyContact') or {},
        'insurance_details': data.get('insuranceDetails') or {},
        'medical_history': data.get('medicalHistory') or [],
    }


def _extract_doctor_kwargs(data: dict) -> dict:
    kwargs = {
        'first_name': data.get('firstName', ''),
        'last_name': data.get('lastName', ''),
        'specialization': data.get('specialization', ''),
        'department': data.get('department'),
        'bio': data.get('bio'),
        'avatar': data.get('avatar'),
        'verification_document': data.get('verificationDocument'),
        'qualifications': data.get('qualifications') or [],
        'experience_years': int(data.get('experienceYears') or 0),
        'contact_number': data.get('contactNumber', ''),
        'consultation_fee': float(data.get('consultationFee') or 0),
        'is_available': data.get('isAvailable', True),
    }
    if data.get('availableDays') is not None:
        kwargs['available_days'] = data['availableDays']
    if data.get('availableTimeSlots') is not None:
        kwargs['available_time_slots'] = data['availableTimeSlots']
    return kwargs


class RegisterView(APIView):
    def post(self, request):
        data = request.data or {}
        email = str(data.get('email') or '').lower().strip()
        password = data.get('password') or ''
        role = data.get('role') or 'Patient'

        if User.objects.filter(email=email).exists():
            return Response({'message': 'User already exists'}, status=status.HTTP_400_BAD_REQUEST)

        profile_data = {k: v for k, v in data.items() if k not in ('email', 'password', 'role')}

        if role in ('Admin', 'Doctor'):
            if not email or not password:
                return Response({'message': 'email and password are required'}, status=status.HTTP_400_BAD_REQUEST)

            if role == 'Admin' and User.objects.filter(role='Admin', status='Active').exists():
                return Response(
                    {'message': 'An active Admin already exists. Request an admin reset to replace it.'},
                    status=status.HTTP_409_CONFLICT,
                )

            token = secrets.token_hex(32)
            approval = ApprovalRequest.objects.create(
                role=role,
                token=token,
                expires_at=timezone.now() + datetime.timedelta(hours=24),
                notify_email=settings.APPROVER_EMAIL,
                payload={'email': email, 'password': password, 'profileData': profile_data},
                requested_by=None,
            )

            mail_res = send_approval_email(
                to=settings.APPROVER_EMAIL,
                subject=f'Approve {role} creation',
                token=approval.token,
                intro=f'Approve creating a new {role} account for: {email}',
            )
            log_audit(request, 'REGISTER', 'User')
            return Response(
                {
                    'success': True,
                    'message': f'{role} creation request submitted for approval.',
                    'emailSent': mail_res['emailSent'],
                    **_approval_extras(mail_res['emailSent'], mail_res['link']),
                },
                status=status.HTTP_202_ACCEPTED,
            )

        if not email or not password:
            return Response({'message': 'email and password are required'}, status=status.HTTP_400_BAD_REQUEST)

        user = User(email=email, role=role)
        user.set_password(password)
        user.save()

        if role == 'Patient':
            Patient.objects.create(user=user, **_extract_patient_kwargs(profile_data))
        elif role == 'Doctor':
            Doctor.objects.create(user=user, **_extract_doctor_kwargs(profile_data))

        token = generate_token(user.id)
        log_audit(request, 'REGISTER', 'User', user=user)

        return Response(
            {
                'success': True,
                'token': token,
                'user': {
                    '_id': user.id,
                    'email': user.email,
                    'role': user.role,
                },
            },
            status=status.HTTP_201_CREATED,
        )


class LoginView(APIView):
    def post(self, request):
        data = request.data or {}
        email = str(data.get('email') or '').lower().strip()
        password = data.get('password') or ''

        user = User.objects.filter(email=email).first()
        if not user or not user.check_password(password):
            return Response({'message': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)

        if user.status == 'Inactive':
            return Response(
                {'message': 'Account is inactive. Please contact admin.'},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        user.last_login = timezone.now()
        user.save(update_fields=['last_login', 'updated_at'])

        token = generate_token(user.id)
        log_audit(request, 'LOGIN', 'User', user=user)

        return Response(
            {
                'success': True,
                'token': token,
                'user': {
                    '_id': user.id,
                    'email': user.email,
                    'role': user.role,
                },
            },
            status=status.HTTP_200_OK,
        )


class MeView(APIView):
    permission_classes = [IsAuthenticatedJWT]

    def get(self, request):
        user = request.user
        profile = None
        if user.role == 'Patient':
            pat = Patient.objects.filter(user=user).first()
            profile = serialize_patient(pat)
        elif user.role == 'Doctor':
            doc = Doctor.objects.filter(user=user).first()
            profile = serialize_doctor(doc)

        return Response(
            {
                'success': True,
                'data': {
                    'user': serialize_user(user),
                    'profile': profile,
                },
            },
            status=status.HTTP_200_OK,
        )


class ForgotPasswordView(APIView):
    def post(self, request):
        email = str((request.data or {}).get('email') or '').lower().strip()
        user = User.objects.filter(email=email).first()
        if not user:
            return Response({'message': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

        reset_token = secrets.token_hex(20)
        hashed = hashlib.sha256(reset_token.encode('utf-8')).hexdigest()
        user.reset_password_token = hashed
        user.reset_password_expire = timezone.now() + datetime.timedelta(minutes=10)
        user.save(update_fields=['reset_password_token', 'reset_password_expire', 'updated_at'])

        reset_url = f'{settings.FRONTEND_URL}/reset-password?token={reset_token}'
        mail_res = send_password_reset_email(to=user.email, reset_url=reset_url)

        if not mail_res['emailSent'] and not settings.DEBUG:
            user.reset_password_token = None
            user.reset_password_expire = None
            user.save(update_fields=['reset_password_token', 'reset_password_expire', 'updated_at'])
            return Response({'message': 'Email could not be sent'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({'success': True, 'message': 'Email sent'}, status=status.HTTP_200_OK)


class ResetPasswordView(APIView):
    def post(self, request):
        data = request.data or {}
        token = data.get('token') or ''
        password = data.get('password') or ''
        if not token or not password:
            return Response({'message': 'Invalid or expired token'}, status=status.HTTP_400_BAD_REQUEST)

        hashed = hashlib.sha256(token.encode('utf-8')).hexdigest()
        user = User.objects.filter(
            reset_password_token=hashed,
            reset_password_expire__gt=timezone.now(),
        ).first()
        if not user:
            return Response({'message': 'Invalid or expired token'}, status=status.HTTP_400_BAD_REQUEST)

        user.set_password(password)
        user.reset_password_token = None
        user.reset_password_expire = None
        user.save()

        return Response({'success': True, 'message': 'Password reset successful'}, status=status.HTTP_200_OK)
