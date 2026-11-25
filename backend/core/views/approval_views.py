import datetime
import secrets
from django.conf import settings
from django.http import HttpResponse
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from core.models import User, Doctor, ApprovalRequest
from core.authentication import IsAuthenticatedJWT, require_roles
from core.serializers import serialize_approval
from core.utils import send_approval_email
from core.views.auth_views import _extract_doctor_kwargs, _approval_extras


def _ensure_no_active_admin() -> bool:
    return not User.objects.filter(role='Admin', status='Active').exists()


class RequestAdminCreationView(APIView):
    def post(self, request):
        if not _ensure_no_active_admin():
            return Response(
                {
                    'success': False,
                    'message': 'An active Admin already exists. Request an admin reset to replace it.',
                },
                status=status.HTTP_409_CONFLICT,
            )

        data = request.data or {}
        email = str(data.get('email') or '').lower().strip()
        password = data.get('password') or ''
        if not email or not password:
            return Response({'success': False, 'message': 'email and password are required'}, status=status.HTTP_400_BAD_REQUEST)

        if User.objects.filter(email=email).exists():
            return Response({'success': False, 'message': 'User already exists'}, status=status.HTTP_400_BAD_REQUEST)

        token = secrets.token_hex(32)
        req_by = request.user if getattr(request.user, 'is_authenticated', False) else None
        approval = ApprovalRequest.objects.create(
            role='Admin',
            token=token,
            expires_at=timezone.now() + datetime.timedelta(hours=24),
            notify_email=settings.APPROVER_EMAIL,
            payload={'email': email, 'password': password},
            requested_by=req_by,
        )

        mail_res = send_approval_email(
            to=settings.APPROVER_EMAIL,
            subject='Approve Admin creation',
            token=approval.token,
            intro=f'Approve creating a new Admin account for: {email}',
        )

        return Response(
            {
                'success': True,
                'message': 'Admin creation request submitted for approval.',
                'emailSent': mail_res['emailSent'],
                **_approval_extras(mail_res['emailSent'], mail_res['link']),
            },
            status=status.HTTP_202_ACCEPTED,
        )


class RequestDoctorCreationView(APIView):
    def post(self, request):
        data = request.data or {}
        email = str(data.get('email') or '').lower().strip()
        password = data.get('password') or ''
        if not email or not password:
            return Response({'success': False, 'message': 'email and password are required'}, status=status.HTTP_400_BAD_REQUEST)

        if User.objects.filter(email=email).exists():
            return Response({'success': False, 'message': 'User already exists'}, status=status.HTTP_400_BAD_REQUEST)

        profile_data = {k: v for k, v in data.items() if k not in ('email', 'password')}
        token = secrets.token_hex(32)
        req_by = request.user if getattr(request.user, 'is_authenticated', False) else None
        approval = ApprovalRequest.objects.create(
            role='Doctor',
            token=token,
            expires_at=timezone.now() + datetime.timedelta(hours=24),
            notify_email=settings.APPROVER_EMAIL,
            payload={'email': email, 'password': password, 'profileData': profile_data},
            requested_by=req_by,
        )

        mail_res = send_approval_email(
            to=settings.APPROVER_EMAIL,
            subject='Approve Doctor creation',
            token=approval.token,
            intro=f'Approve creating a new Doctor account for: {email}',
        )

        return Response(
            {
                'success': True,
                'message': 'Doctor creation request submitted for approval.',
                'emailSent': mail_res['emailSent'],
                **_approval_extras(mail_res['emailSent'], mail_res['link']),
            },
            status=status.HTTP_202_ACCEPTED,
        )


class RequestAdminResetView(APIView):
    def post(self, request):
        data = request.data or {}
        email = str(data.get('email') or '').lower().strip()
        password = data.get('password') or ''
        if not email or not password:
            return Response({'success': False, 'message': 'email and password are required'}, status=status.HTTP_400_BAD_REQUEST)

        token = secrets.token_hex(32)
        req_by = request.user if getattr(request.user, 'is_authenticated', False) else None
        approval = ApprovalRequest.objects.create(
            role='AdminReset',
            token=token,
            expires_at=timezone.now() + datetime.timedelta(hours=24),
            notify_email=settings.APPROVER_EMAIL,
            payload={'email': email, 'password': password},
            requested_by=req_by,
        )

        mail_res = send_approval_email(
            to=settings.APPROVER_EMAIL,
            subject='Approve Admin reset',
            token=approval.token,
            intro=f'Approve resetting Admin. This will deactivate existing Admins and create a new Admin: {email}',
        )

        return Response(
            {
                'success': True,
                'message': 'Admin reset request submitted for approval.',
                'emailSent': mail_res['emailSent'],
                **_approval_extras(mail_res['emailSent'], mail_res['link']),
            },
            status=status.HTTP_202_ACCEPTED,
        )


class ApproveByTokenView(APIView):
    def get(self, request, token):
        approval = ApprovalRequest.objects.filter(token=token).first()
        if not approval:
            return HttpResponse('Approval request not found.', status=404, content_type='text/plain')

        if approval.status == 'Approved':
            return HttpResponse(
                'This request was already approved. The account is ready to use.',
                status=200,
                content_type='text/plain',
            )

        if approval.status != 'Pending':
            return HttpResponse(f'This request is already {approval.status}.', status=400, content_type='text/plain')

        if approval.expires_at < timezone.now():
            approval.status = 'Expired'
            approval.save(update_fields=['status', 'updated_at'])
            return HttpResponse('This approval link has expired.', status=400, content_type='text/plain')

        payload = approval.payload or {}
        email = str(payload.get('email') or '').lower().strip()
        password = payload.get('password') or ''

        if approval.role == 'Admin':
            if not _ensure_no_active_admin():
                return HttpResponse(
                    'An active Admin already exists. Use Admin Reset.',
                    status=409,
                    content_type='text/plain',
                )
            if not email or not password:
                return HttpResponse('Approval payload missing email/password.', status=400, content_type='text/plain')

            user = User(email=email, role='Admin', status='Active')
            user.set_password(password)
            user.save()
            approval.status = 'Approved'
            approval.save(update_fields=['status', 'updated_at'])
            return HttpResponse(f'Approved. Admin created: {user.email}', status=200, content_type='text/plain')

        if approval.role == 'Doctor':
            if not email or not password:
                return HttpResponse('Approval payload missing email/password.', status=400, content_type='text/plain')

            doctor_user = User(email=email, role='Doctor', status='Active')
            doctor_user.set_password(password)
            doctor_user.save()
            Doctor.objects.create(user=doctor_user, **_extract_doctor_kwargs(payload.get('profileData') or {}))

            approval.status = 'Approved'
            approval.save(update_fields=['status', 'updated_at'])
            return HttpResponse(f'Approved. Doctor created: {doctor_user.email}', status=200, content_type='text/plain')

        if approval.role == 'AdminReset':
            if not email or not password:
                return HttpResponse('Approval payload missing email/password.', status=400, content_type='text/plain')

            User.objects.filter(role='Admin', status='Active').update(status='Inactive')
            user = User(email=email, role='Admin', status='Active')
            user.set_password(password)
            user.save()
            approval.status = 'Approved'
            approval.save(update_fields=['status', 'updated_at'])
            return HttpResponse(
                f'Approved. Admin reset completed. New Admin: {user.email}',
                status=200,
                content_type='text/plain',
            )

        return HttpResponse('Unknown approval type.', status=400, content_type='text/plain')


class PendingApprovalsView(APIView):
    permission_classes = [IsAuthenticatedJWT, require_roles('Admin')]

    def get(self, request):
        approvals = ApprovalRequest.objects.filter(status='Pending').order_by('-created_at')
        return Response({'success': True, 'data': [serialize_approval(a) for a in approvals]}, status=status.HTTP_200_OK)


class ApproveRequestByIdView(APIView):
    permission_classes = [IsAuthenticatedJWT, require_roles('Admin')]

    def post(self, request, approval_id):
        approval = ApprovalRequest.objects.filter(id=approval_id).first()
        if not approval:
            return Response({'success': False, 'message': 'Approval request not found.'}, status=status.HTTP_404_NOT_FOUND)

        if approval.status != 'Pending':
            return Response(
                {'success': False, 'message': f'Request is already {approval.status}.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        payload = approval.payload or {}
        email = str(payload.get('email') or '').lower().strip()
        password = payload.get('password') or ''

        if approval.role == 'Admin':
            if not _ensure_no_active_admin():
                return Response({'success': False, 'message': 'An active Admin already exists.'}, status=status.HTTP_409_CONFLICT)
            user = User(email=email, role='Admin', status='Active')
            user.set_password(password)
            user.save()
            approval.status = 'Approved'
            approval.save(update_fields=['status', 'updated_at'])
            return Response({'success': True, 'message': f'Approved. Admin created: {user.email}'}, status=status.HTTP_200_OK)

        if approval.role == 'Doctor':
            doctor_user = User(email=email, role='Doctor', status='Active')
            doctor_user.set_password(password)
            doctor_user.save()
            Doctor.objects.create(user=doctor_user, **_extract_doctor_kwargs(payload.get('profileData') or {}))
            approval.status = 'Approved'
            approval.save(update_fields=['status', 'updated_at'])
            return Response({'success': True, 'message': f'Approved. Doctor created: {doctor_user.email}'}, status=status.HTTP_200_OK)

        return Response({'success': False, 'message': 'Unsupported role or action.'}, status=status.HTTP_400_BAD_REQUEST)


class RejectRequestByIdView(APIView):
    permission_classes = [IsAuthenticatedJWT, require_roles('Admin')]

    def post(self, request, approval_id):
        approval = ApprovalRequest.objects.filter(id=approval_id).first()
        if not approval:
            return Response({'success': False, 'message': 'Approval request not found.'}, status=status.HTTP_404_NOT_FOUND)

        if approval.status != 'Pending':
            return Response(
                {'success': False, 'message': f'Request is already {approval.status}.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        approval.status = 'Rejected'
        approval.save(update_fields=['status', 'updated_at'])
        return Response({'success': True, 'message': 'Request rejected successfully.'}, status=status.HTTP_200_OK)
