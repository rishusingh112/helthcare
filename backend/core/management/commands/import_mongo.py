import datetime
import os
import bson
from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone
from core.models import (
    User, Doctor, Patient, Appointment, Prescription,
    MedicalRecord, Message, Notification, ApprovalRequest,
    AuditLog, FAQ, Review, Service,
)


def _oid(val):
    return str(val) if val is not None else None


def _dt(val):
    if val is None:
        return timezone.now()
    if isinstance(val, datetime.datetime):
        if timezone.is_naive(val):
            return timezone.make_aware(val, datetime.timezone.utc)
        return val
    return timezone.now()


def _clean_json(val):
    if isinstance(val, bson.ObjectId):
        return str(val)
    if isinstance(val, datetime.datetime):
        return val.isoformat()
    if isinstance(val, list):
        return [_clean_json(x) for x in val]
    if isinstance(val, dict):
        return {k: _clean_json(v) for k, v in val.items()}
    return val


def _read_bson_docs(backup_dir: str, name: str):
    path = os.path.join(backup_dir, f'{name}.bson')
    if not os.path.exists(path):
        return []
    with open(path, 'rb') as f:
        return bson.decode_all(f.read())


class Command(BaseCommand):
    help = 'Import BSON documents from mongo_backup/healthcare_workflow into PostgreSQL'

    def add_arguments(self, parser):
        parser.add_argument(
            '--path',
            default=os.path.join(settings.BASE_DIR.parent, 'mongo_backup', 'healthcare_workflow'),
            help='Path to mongo_backup/healthcare_workflow directory',
        )

    def handle(self, *args, **options):
        backup_dir = options['path']
        if not os.path.isdir(backup_dir):
            self.stderr.write(self.style.ERROR(f'Backup directory not found: {backup_dir}'))
            return

        for doc in _read_bson_docs(backup_dir, 'users'):
            uid = _oid(doc['_id'])
            User.objects.update_or_create(
                id=uid,
                defaults={
                    'email': doc['email'].lower().strip(),
                    'password': doc['password'],
                    'avatar': doc.get('avatar'),
                    'role': doc['role'],
                    'status': doc.get('status', 'Active'),
                    'last_login': _dt(doc['lastLogin']) if doc.get('lastLogin') else None,
                    'refresh_token': doc.get('refreshToken'),
                    'created_at': _dt(doc.get('createdAt')),
                },
            )

        for doc in _read_bson_docs(backup_dir, 'doctors'):
            uid = _oid(doc.get('userId'))
            if not User.objects.filter(id=uid).exists():
                continue
            Doctor.objects.update_or_create(
                id=_oid(doc['_id']),
                defaults={
                    'user_id': uid,
                    'first_name': doc.get('firstName', ''),
                    'last_name': doc.get('lastName', ''),
                    'specialization': doc.get('specialization', ''),
                    'department': doc.get('department'),
                    'bio': doc.get('bio'),
                    'avatar': doc.get('avatar'),
                    'verification_document': doc.get('verificationDocument'),
                    'qualifications': doc.get('qualifications') or [],
                    'experience_years': int(doc.get('experienceYears') or 0),
                    'contact_number': doc.get('contactNumber', ''),
                    'consultation_fee': float(doc.get('consultationFee') or 0),
                    'is_available': doc.get('isAvailable', True),
                    'available_days': doc.get('availableDays') or ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday'],
                    'available_time_slots': doc.get('availableTimeSlots') or ['09:00 AM', '10:00 AM', '11:00 AM', '01:00 PM', '02:00 PM', '03:00 PM', '04:00 PM'],
                    'average_rating': float(doc.get('averageRating') or 0),
                    'total_reviews': int(doc.get('totalReviews') or 0),
                    'created_at': _dt(doc.get('createdAt')),
                },
            )

        for doc in _read_bson_docs(backup_dir, 'patients'):
            uid = _oid(doc.get('userId'))
            if not User.objects.filter(id=uid).exists():
                continue
            Patient.objects.update_or_create(
                id=_oid(doc['_id']),
                defaults={
                    'user_id': uid,
                    'first_name': doc.get('firstName', ''),
                    'last_name': doc.get('lastName', ''),
                    'dob': _dt(doc.get('dob')),
                    'gender': doc.get('gender', 'Other'),
                    'contact_number': doc.get('contactNumber', ''),
                    'address': doc.get('address'),
                    'avatar': doc.get('avatar'),
                    'blood_group': doc.get('bloodGroup'),
                    'allergies': doc.get('allergies') or [],
                    'emergency_contact': doc.get('emergencyContact') or {},
                    'insurance_details': doc.get('insuranceDetails') or {},
                    'medical_history': doc.get('medicalHistory') or [],
                    'created_at': _dt(doc.get('createdAt')),
                },
            )

        for doc in _read_bson_docs(backup_dir, 'appointments'):
            pid, did = _oid(doc.get('patientId')), _oid(doc.get('doctorId'))
            if not (Patient.objects.filter(id=pid).exists() and Doctor.objects.filter(id=did).exists()):
                continue
            Appointment.objects.update_or_create(
                id=_oid(doc['_id']),
                defaults={
                    'patient_id': pid,
                    'doctor_id': did,
                    'date': _dt(doc.get('date')),
                    'time_slot': doc.get('timeSlot', ''),
                    'type': doc.get('type', 'In-Person'),
                    'status': doc.get('status', 'Pending'),
                    'reason': doc.get('reason', ''),
                    'notes': doc.get('notes'),
                    'cancel_reason': doc.get('cancelReason'),
                    'attachments': doc.get('attachments') or [],
                    'created_at': _dt(doc.get('createdAt')),
                },
            )

        for doc in _read_bson_docs(backup_dir, 'prescriptions'):
            aid, pid, did = _oid(doc.get('appointmentId')), _oid(doc.get('patientId')), _oid(doc.get('doctorId'))
            if not (Appointment.objects.filter(id=aid).exists() and Patient.objects.filter(id=pid).exists() and Doctor.objects.filter(id=did).exists()):
                continue
            Prescription.objects.update_or_create(
                id=_oid(doc['_id']),
                defaults={
                    'appointment_id': aid,
                    'patient_id': pid,
                    'doctor_id': did,
                    'medications': _clean_json(doc.get('medications') or []),
                    'instructions': doc.get('instructions'),
                    'date': _dt(doc.get('date')),
                    'created_at': _dt(doc.get('createdAt')),
                },
            )

        for doc in _read_bson_docs(backup_dir, 'medicalrecords'):
            pid = _oid(doc.get('patientId'))
            did = _oid(doc.get('doctorId')) if doc.get('doctorId') and Doctor.objects.filter(id=_oid(doc.get('doctorId'))).exists() else None
            if not Patient.objects.filter(id=pid).exists():
                continue
            MedicalRecord.objects.update_or_create(
                id=_oid(doc['_id']),
                defaults={
                    'patient_id': pid,
                    'doctor_id': did,
                    'uploaded_by': doc.get('uploadedBy', 'Doctor'),
                    'record_type': doc.get('recordType', 'Other'),
                    'title': doc.get('title', ''),
                    'description': doc.get('description'),
                    'file_url': doc.get('fileUrl'),
                    'date': _dt(doc.get('date')),
                    'created_at': _dt(doc.get('createdAt')),
                },
            )

        for doc in _read_bson_docs(backup_dir, 'messages'):
            sid = _oid(doc.get('senderId'))
            if not User.objects.filter(id=sid).exists():
                continue
            Message.objects.update_or_create(
                id=_oid(doc['_id']),
                defaults={
                    'conversation_id': doc.get('conversationId', ''),
                    'sender_id': sid,
                    'sender_role': doc.get('senderRole', 'Patient'),
                    'text': doc.get('text'),
                    'attachment': _clean_json(doc.get('attachment')),
                    'is_call_log': bool(doc.get('isCallLog', False)),
                    'read_at': _dt(doc['readAt']) if doc.get('readAt') else None,
                    'created_at': _dt(doc.get('createdAt')),
                },
            )

        for doc in _read_bson_docs(backup_dir, 'notifications'):
            uid = _oid(doc.get('userId'))
            if not User.objects.filter(id=uid).exists():
                continue
            Notification.objects.update_or_create(
                id=_oid(doc['_id']),
                defaults={
                    'user_id': uid,
                    'title': doc.get('title', ''),
                    'message': doc.get('message', ''),
                    'type': doc.get('type', 'System'),
                    'is_read': bool(doc.get('isRead', False)),
                    'link': doc.get('link'),
                    'created_at': _dt(doc.get('createdAt')),
                },
            )

        for doc in _read_bson_docs(backup_dir, 'approvalrequests'):
            req_by = _oid(doc.get('requestedBy'))
            if req_by and not User.objects.filter(id=req_by).exists():
                req_by = None
            ApprovalRequest.objects.update_or_create(
                id=_oid(doc['_id']),
                defaults={
                    'role': doc['role'],
                    'status': doc.get('status', 'Pending'),
                    'token': doc['token'],
                    'expires_at': _dt(doc.get('expiresAt')),
                    'notify_email': doc.get('notifyEmail', ''),
                    'payload': _clean_json(doc.get('payload') or {}),
                    'requested_by_id': req_by,
                    'created_at': _dt(doc.get('createdAt')),
                },
            )

        for doc in _read_bson_docs(backup_dir, 'faqs'):
            FAQ.objects.update_or_create(
                id=_oid(doc['_id']),
                defaults={
                    'question': doc.get('question', ''),
                    'answer': doc.get('answer', ''),
                    'order': int(doc.get('order') or 0),
                    'is_active': bool(doc.get('isActive', True)),
                    'created_at': _dt(doc.get('createdAt')),
                },
            )

        for doc in _read_bson_docs(backup_dir, 'reviews'):
            aid, pid, did = _oid(doc.get('appointmentId')), _oid(doc.get('patientId')), _oid(doc.get('doctorId'))
            if not (Appointment.objects.filter(id=aid).exists() and Patient.objects.filter(id=pid).exists() and Doctor.objects.filter(id=did).exists()):
                continue
            Review.objects.update_or_create(
                id=_oid(doc['_id']),
                defaults={
                    'patient_id': pid,
                    'doctor_id': did,
                    'appointment_id': aid,
                    'rating': int(doc.get('rating') or 5),
                    'comment': doc.get('comment', ''),
                    'status': doc.get('status', 'approved'),
                    'created_at': _dt(doc.get('createdAt')),
                },
            )

        for doc in _read_bson_docs(backup_dir, 'services'):
            Service.objects.update_or_create(
                id=_oid(doc['_id']),
                defaults={
                    'title': doc.get('title', ''),
                    'description': doc.get('description', ''),
                    'tags': doc.get('tags') or [],
                    'image': doc.get('image') or '',
                    'icon_name': doc.get('iconName') or 'Stethoscope',
                    'created_at': _dt(doc.get('createdAt')),
                },
            )

        for doc in _read_bson_docs(backup_dir, 'auditlogs'):
            uid = _oid(doc.get('userId'))
            if uid and not User.objects.filter(id=uid).exists():
                uid = None
            AuditLog.objects.update_or_create(
                id=_oid(doc['_id']),
                defaults={
                    'user_id': uid,
                    'action': doc.get('action', ''),
                    'resource': doc.get('resource', ''),
                    'details': _clean_json(doc.get('details')),
                    'ip_address': doc.get('ipAddress'),
                    'created_at': _dt(doc.get('createdAt')),
                },
            )

        self.stdout.write(self.style.SUCCESS('MongoDB BSON backup imported into PostgreSQL successfully!'))
