import os
import random
import time
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.response import Response
from rest_framework import status

from core.models import MedicalRecord, Notification, Patient, Doctor
from core.authentication import IsAuthenticatedJWT, require_roles
from core.serializers import serialize_medical_record
from core.utils import log_audit


def _save_document_file(uploaded) -> str:
    ext = os.path.splitext(uploaded.name)[1].lower() or '.pdf'
    upload_dir = os.path.join(settings.MEDIA_ROOT, 'documents')
    os.makedirs(upload_dir, exist_ok=True)
    filename = f'{int(time.time() * 1000)}-{random.randint(100000, 999999999)}{ext}'
    filepath = os.path.join(upload_dir, filename)
    with open(filepath, 'wb+') as dest:
        for chunk in uploaded.chunks():
            dest.write(chunk)
    return f'/uploads/documents/{filename}'


class MedicalRecordCreateView(APIView):
    permission_classes = [IsAuthenticatedJWT, require_roles('Doctor', 'Admin')]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def post(self, request):
        data = request.data or {}
        patient_id = data.get('patientId')
        record_type = data.get('recordType')
        title = data.get('title')
        description = data.get('description')

        if not patient_id or not record_type or not title:
            return Response(
                {'message': 'patientId, recordType, and title are required'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        patient = Patient.objects.select_related('user').filter(id=patient_id).first()
        if not patient:
            return Response({'message': 'Patient not found'}, status=status.HTTP_404_NOT_FOUND)

        doctor_id = data.get('doctorId')
        if request.user.role == 'Doctor':
            doc = Doctor.objects.filter(user=request.user).first()
            if not doc:
                return Response({'message': 'Doctor profile not found'}, status=status.HTTP_404_NOT_FOUND)
            doctor_id = doc.id

        uploaded = request.FILES.get('file')
        file_url = _save_document_file(uploaded) if uploaded else (data.get('fileUrl') or None)

        record = MedicalRecord.objects.create(
            patient=patient,
            doctor_id=doctor_id or None,
            uploaded_by='Doctor',
            record_type=record_type,
            title=title,
            description=description,
            file_url=file_url,
        )

        if patient.user_id:
            Notification.objects.create(
                user=patient.user,
                title='New Medical Record',
                message=f'A new {record_type} has been added to your records.',
                type='MedicalRecord',
            )

        log_audit(request, 'CREATE', 'MedicalRecord')
        return Response({'success': True, 'data': serialize_medical_record(record)}, status=status.HTTP_201_CREATED)


class PatientRecordUploadView(APIView):
    permission_classes = [IsAuthenticatedJWT, require_roles('Patient')]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def post(self, request):
        patient = Patient.objects.filter(user=request.user).first()
        if not patient:
            return Response({'message': 'Patient profile not found'}, status=status.HTTP_404_NOT_FOUND)

        data = request.data or {}
        title = data.get('title')
        if not title:
            return Response({'message': 'title is required'}, status=status.HTTP_400_BAD_REQUEST)

        uploaded = request.FILES.get('file')
        file_url = _save_document_file(uploaded) if uploaded else (data.get('fileUrl') or None)

        record = MedicalRecord.objects.create(
            patient=patient,
            doctor=None,
            uploaded_by='Patient',
            record_type=data.get('recordType') or 'Lab Result',
            title=title,
            description=data.get('description'),
            file_url=file_url,
        )

        log_audit(request, 'CREATE', 'MedicalRecord')
        return Response({'success': True, 'data': serialize_medical_record(record)}, status=status.HTTP_201_CREATED)


class RecordByIdOrPatientView(APIView):
    permission_classes = [IsAuthenticatedJWT]

    def get(self, request, item_id):
        if request.user.role == 'Patient':
            own = Patient.objects.filter(user=request.user).first()
            if not own or own.id != item_id:
                return Response({'message': 'Not authorized to view these records'}, status=status.HTTP_403_FORBIDDEN)

        records = (
            MedicalRecord.objects.select_related('doctor')
            .filter(patient_id=item_id)
            .order_by('-created_at')
        )
        return Response(
            {'success': True, 'data': [serialize_medical_record(r, populate_doctor=True) for r in records]},
            status=status.HTTP_200_OK,
        )

    def delete(self, request, item_id):
        if request.user.role not in ('Doctor', 'Admin'):
            return Response(
                {'message': f'User role {request.user.role} is not authorized to access this route'},
                status=status.HTTP_403_FORBIDDEN,
            )
        record = MedicalRecord.objects.filter(id=item_id).first()
        if not record:
            return Response({'message': 'Record not found'}, status=status.HTTP_404_NOT_FOUND)
        record.delete()
        log_audit(request, 'DELETE', 'MedicalRecord')
        return Response({'success': True, 'message': 'Record deleted successfully'}, status=status.HTTP_200_OK)
