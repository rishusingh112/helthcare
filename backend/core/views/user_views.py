import math
from django.db.models import Q
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from core.models import User, Doctor, Patient
from core.authentication import IsAuthenticatedJWT, require_roles
from core.serializers import serialize_user, serialize_doctor, serialize_patient
from core.utils import parse_flexible_datetime, log_audit


def _update_doctor_fields(doc: Doctor, updates: dict):
    field_map = {
        'firstName': 'first_name',
        'lastName': 'last_name',
        'specialization': 'specialization',
        'department': 'department',
        'bio': 'bio',
        'avatar': 'avatar',
        'experienceYears': 'experience_years',
        'consultationFee': 'consultation_fee',
        'contactNumber': 'contact_number',
        'qualifications': 'qualifications',
        'isAvailable': 'is_available',
        'availableDays': 'available_days',
        'availableTimeSlots': 'available_time_slots',
    }
    for api_key, attr in field_map.items():
        if api_key in updates and updates[api_key] is not None:
            val = updates[api_key]
            if api_key == 'experienceYears':
                val = int(val)
            elif api_key == 'consultationFee':
                val = float(val)
            setattr(doc, attr, val)
    doc.save()
    return doc


def _update_patient_fields(pat: Patient, updates: dict):
    field_map = {
        'firstName': 'first_name',
        'lastName': 'last_name',
        'gender': 'gender',
        'contactNumber': 'contact_number',
        'address': 'address',
        'avatar': 'avatar',
        'bloodGroup': 'blood_group',
        'allergies': 'allergies',
        'emergencyContact': 'emergency_contact',
        'insuranceDetails': 'insurance_details',
        'medicalHistory': 'medical_history',
    }
    for api_key, attr in field_map.items():
        if api_key in updates and updates[api_key] is not None:
            setattr(pat, attr, updates[api_key])
    if updates.get('dob'):
        parsed_dob = parse_flexible_datetime(updates['dob'])
        if parsed_dob:
            pat.dob = parsed_dob
    pat.save()
    return pat


class UsersListView(APIView):
    permission_classes = [IsAuthenticatedJWT, require_roles('Admin')]

    def get(self, request):
        page = max(int(request.query_params.get('page') or 1), 1)
        limit = max(int(request.query_params.get('limit') or 10), 1)
        search = (request.query_params.get('search') or '').strip()

        qs = User.objects.all().order_by('-created_at')
        if search:
            qs = qs.filter(email__icontains=search)

        total = qs.count()
        start = (page - 1) * limit
        users = qs[start:start + limit]

        return Response(
            {
                'success': True,
                'count': len(users),
                'pagination': {
                    'page': page,
                    'limit': limit,
                    'total': total,
                    'pages': math.ceil(total / limit) if limit else 1,
                },
                'data': [serialize_user(u) for u in users],
            },
            status=status.HTTP_200_OK,
        )


class UserStatusUpdateView(APIView):
    permission_classes = [IsAuthenticatedJWT, require_roles('Admin')]

    def put(self, request, user_id):
        user = User.objects.filter(id=user_id).first()
        if not user:
            return Response({'message': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

        new_status = (request.data or {}).get('status')
        if new_status not in ('Active', 'Inactive'):
            return Response({'message': 'Invalid status'}, status=status.HTTP_400_BAD_REQUEST)

        user.status = new_status
        user.save(update_fields=['status', 'updated_at'])
        log_audit(request, 'UPDATE_STATUS', 'User')

        return Response({'success': True, 'data': serialize_user(user)}, status=status.HTTP_200_OK)


class DoctorsListView(APIView):
    permission_classes = [IsAuthenticatedJWT]

    def get(self, request):
        page = max(int(request.query_params.get('page') or 1), 1)
        limit = max(int(request.query_params.get('limit') or 10), 1)
        search = (request.query_params.get('search') or '').strip()

        qs = Doctor.objects.select_related('user').all().order_by('-created_at')
        if search:
            qs = qs.filter(
                Q(first_name__icontains=search)
                | Q(last_name__icontains=search)
                | Q(specialization__icontains=search)
            )

        total = qs.count()
        start = (page - 1) * limit
        doctors = qs[start:start + limit]

        return Response(
            {
                'success': True,
                'count': len(doctors),
                'pagination': {
                    'page': page,
                    'limit': limit,
                    'total': total,
                    'pages': math.ceil(total / limit) if limit else 1,
                },
                'data': [
                    serialize_doctor(d, populate_user=True, user_fields=['email', 'status', 'avatar'])
                    for d in doctors
                ],
            },
            status=status.HTTP_200_OK,
        )


class PatientsListView(APIView):
    permission_classes = [IsAuthenticatedJWT, require_roles('Admin', 'Doctor')]

    def get(self, request):
        page = max(int(request.query_params.get('page') or 1), 1)
        limit = max(int(request.query_params.get('limit') or 10), 1)
        search = (request.query_params.get('search') or '').strip()

        qs = Patient.objects.select_related('user').all().order_by('-created_at')
        if search:
            qs = qs.filter(Q(first_name__icontains=search) | Q(last_name__icontains=search))

        total = qs.count()
        start = (page - 1) * limit
        patients = qs[start:start + limit]

        return Response(
            {
                'success': True,
                'count': len(patients),
                'pagination': {
                    'page': page,
                    'limit': limit,
                    'total': total,
                    'pages': math.ceil(total / limit) if limit else 1,
                },
                'data': [
                    serialize_patient(p, populate_user=True, user_fields=['email', 'status', 'avatar'])
                    for p in patients
                ],
            },
            status=status.HTTP_200_OK,
        )


class DoctorProfileUpdateView(APIView):
    permission_classes = [IsAuthenticatedJWT, require_roles('Doctor')]

    def put(self, request):
        doc = Doctor.objects.filter(user=request.user).first()
        if not doc:
            return Response({'message': 'Doctor profile not found'}, status=status.HTTP_404_NOT_FOUND)

        data = request.data or {}
        _update_doctor_fields(doc, data)
        if data.get('avatar'):
            request.user.avatar = data['avatar']
            request.user.save(update_fields=['avatar', 'updated_at'])

        log_audit(request, 'UPDATE_PROFILE', 'User')
        return Response({'success': True, 'data': serialize_doctor(doc)}, status=status.HTTP_200_OK)


class PatientProfileUpdateView(APIView):
    permission_classes = [IsAuthenticatedJWT, require_roles('Patient')]

    def put(self, request):
        pat = Patient.objects.filter(user=request.user).first()
        if not pat:
            return Response({'message': 'Patient profile not found'}, status=status.HTTP_404_NOT_FOUND)

        data = request.data or {}
        _update_patient_fields(pat, data)
        if data.get('avatar'):
            request.user.avatar = data['avatar']
            request.user.save(update_fields=['avatar', 'updated_at'])

        log_audit(request, 'UPDATE_PROFILE', 'User')
        return Response({'success': True, 'data': serialize_patient(pat)}, status=status.HTTP_200_OK)


class AdminUserProfileView(APIView):
    permission_classes = [IsAuthenticatedJWT, require_roles('Admin')]

    def get(self, request, user_id):
        user = User.objects.filter(id=user_id).first()
        if not user:
            return Response({'message': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

        profile = None
        if user.role == 'Doctor':
            profile = serialize_doctor(Doctor.objects.filter(user=user).first())
        elif user.role == 'Patient':
            profile = serialize_patient(Patient.objects.filter(user=user).first())

        return Response(
            {'success': True, 'data': {'user': serialize_user(user), 'profile': profile}},
            status=status.HTTP_200_OK,
        )

    def put(self, request, user_id):
        user = User.objects.filter(id=user_id).first()
        if not user:
            return Response({'message': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

        data = request.data or {}
        if data.get('email'):
            user.email = data['email']
        if data.get('status'):
            user.status = data['status']
        if 'avatar' in data and data['avatar'] is not None:
            user.avatar = data['avatar']
        user.save()

        updated_profile = None
        profile_data = data.get('profile')
        if user.role == 'Doctor' and isinstance(profile_data, dict):
            doc = Doctor.objects.filter(user=user).first()
            if doc:
                updated_profile = serialize_doctor(_update_doctor_fields(doc, profile_data))
        elif user.role == 'Patient' and isinstance(profile_data, dict):
            pat = Patient.objects.filter(user=user).first()
            if pat:
                updated_profile = serialize_patient(_update_patient_fields(pat, profile_data))

        log_audit(request, 'UPDATE_PROFILE', 'User')
        return Response(
            {'success': True, 'data': {'user': serialize_user(user), 'profile': updated_profile}},
            status=status.HTTP_200_OK,
        )


class UserDeleteView(APIView):
    permission_classes = [IsAuthenticatedJWT, require_roles('Admin')]

    def delete(self, request, user_id):
        user = User.objects.filter(id=user_id).first()
        if not user:
            return Response({'message': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

        user.delete()
        log_audit(request, 'DELETE', 'User')
        return Response({'success': True, 'message': 'User deleted'}, status=status.HTTP_200_OK)
