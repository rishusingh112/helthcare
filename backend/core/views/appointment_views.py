import datetime
import re
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from core.models import Appointment, Prescription, Patient, Doctor, Notification
from core.authentication import IsAuthenticatedJWT, require_roles
from core.serializers import serialize_appointment, serialize_prescription
from core.utils import parse_flexible_datetime, log_audit


DEFAULT_SLOTS = ['09:00 AM', '10:00 AM', '11:00 AM', '01:00 PM', '02:00 PM', '03:00 PM', '04:00 PM']


class AppointmentsView(APIView):
    permission_classes = [IsAuthenticatedJWT]

    def get(self, request):
        user = request.user
        qs = Appointment.objects.select_related('patient', 'patient__user', 'doctor', 'doctor__user')

        if user.role == 'Admin':
            appointments = qs.all().order_by('-date')
        elif user.role == 'Patient':
            pid = request.query_params.get('patientId')
            if not pid:
                pat = Patient.objects.filter(user=user).first()
                if not pat:
                    return Response({'message': 'Patient profile not found'}, status=status.HTTP_404_NOT_FOUND)
                pid = pat.id
            appointments = qs.filter(patient_id=pid).order_by('-date')
        elif user.role == 'Doctor':
            did = request.query_params.get('doctorId')
            if not did:
                doc = Doctor.objects.filter(user=user).first()
                if not doc:
                    return Response({'message': 'Doctor profile not found'}, status=status.HTTP_404_NOT_FOUND)
                did = doc.id
            appointments = qs.filter(doctor_id=did).order_by('-date')
        else:
            appointments = []

        return Response(
            {'success': True, 'data': [serialize_appointment(a, populate=True) for a in appointments]},
            status=status.HTTP_200_OK,
        )

    def post(self, request):
        if request.user.role not in ('Patient', 'Admin'):
            return Response(
                {'message': f'User role {request.user.role} is not authorized to access this route'},
                status=status.HTTP_403_FORBIDDEN,
            )

        data = request.data or {}
        patient_id = data.get('patientId')
        doctor_id = data.get('doctorId')
        date_raw = data.get('date')
        time_slot = data.get('timeSlot')
        reason = data.get('reason')
        notes = data.get('notes')
        appt_type = data.get('type') or 'In-Person'

        if request.user.role == 'Patient':
            pat = Patient.objects.filter(user=request.user).first()
            if not pat:
                return Response({'message': 'Patient profile not found'}, status=status.HTTP_404_NOT_FOUND)
            patient_id = pat.id

        if not patient_id or not doctor_id or not date_raw or not time_slot or not reason:
            return Response(
                {'message': 'doctorId, date, timeSlot, and reason are required'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        selected_dt = parse_flexible_datetime(date_raw)
        if not selected_dt:
            return Response({'message': 'Invalid date format'}, status=status.HTTP_400_BAD_REQUEST)

        today = datetime.date.today()
        if selected_dt.date() < today:
            return Response({'message': 'Cannot book an appointment in the past'}, status=status.HTTP_400_BAD_REQUEST)

        existing = Appointment.objects.filter(
            doctor_id=doctor_id,
            date__date=selected_dt.date(),
            time_slot=time_slot,
        ).exclude(status='Cancelled').exists()
        if existing:
            return Response(
                {'message': 'Time slot is already booked for this doctor.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        patient = Patient.objects.select_related('user').filter(id=patient_id).first()
        doctor = Doctor.objects.filter(id=doctor_id).first()
        if not patient or not doctor:
            return Response({'message': 'Patient or Doctor not found'}, status=status.HTTP_404_NOT_FOUND)

        appointment = Appointment.objects.create(
            patient=patient,
            doctor=doctor,
            date=selected_dt,
            time_slot=time_slot,
            reason=reason,
            notes=notes,
            type=appt_type,
        )

        if patient.user_id:
            Notification.objects.create(
                user=patient.user,
                title='Appointment booked',
                message=f'Your appointment on {selected_dt.strftime("%Y-%m-%d")} at {time_slot} is pending confirmation.',
                type='Appointment',
            )

        log_audit(request, 'CREATE', 'Appointment')
        return Response({'success': True, 'data': serialize_appointment(appointment)}, status=status.HTTP_201_CREATED)


class AppointmentStatusView(APIView):
    permission_classes = [IsAuthenticatedJWT, require_roles('Doctor', 'Admin')]

    def put(self, request, appointment_id):
        appointment = Appointment.objects.filter(id=appointment_id).first()
        if not appointment:
            return Response({'message': 'Appointment not found'}, status=status.HTTP_404_NOT_FOUND)

        new_status = (request.data or {}).get('status')
        if new_status not in ('Pending', 'Confirmed', 'Completed', 'Cancelled'):
            return Response({'message': 'Invalid status'}, status=status.HTTP_400_BAD_REQUEST)

        appointment.status = new_status
        appointment.save(update_fields=['status', 'updated_at'])
        log_audit(request, 'UPDATE_STATUS', 'Appointment')

        return Response({'success': True, 'data': serialize_appointment(appointment)}, status=status.HTTP_200_OK)


class AppointmentCancelView(APIView):
    permission_classes = [IsAuthenticatedJWT]

    def delete(self, request, appointment_id):
        appointment = Appointment.objects.filter(id=appointment_id).first()
        if not appointment:
            return Response({'message': 'Appointment not found'}, status=status.HTTP_404_NOT_FOUND)

        cancel_reason = (request.data or {}).get('cancelReason') or 'Cancelled by user'
        appointment.status = 'Cancelled'
        appointment.cancel_reason = cancel_reason
        appointment.save(update_fields=['status', 'cancel_reason', 'updated_at'])
        log_audit(request, 'CANCEL', 'Appointment')

        return Response({'success': True, 'data': serialize_appointment(appointment)}, status=status.HTTP_200_OK)


class AppointmentRescheduleView(APIView):
    permission_classes = [IsAuthenticatedJWT]

    def put(self, request, appointment_id):
        appointment = Appointment.objects.filter(id=appointment_id).first()
        if not appointment:
            return Response({'message': 'Appointment not found'}, status=status.HTTP_404_NOT_FOUND)

        data = request.data or {}
        date_raw = data.get('date')
        time_slot = data.get('timeSlot')
        selected_dt = parse_flexible_datetime(date_raw)
        if not selected_dt or not time_slot:
            return Response({'message': 'Date and timeSlot are required'}, status=status.HTTP_400_BAD_REQUEST)

        existing = Appointment.objects.filter(
            doctor_id=appointment.doctor_id,
            date__date=selected_dt.date(),
            time_slot=time_slot,
        ).exclude(status='Cancelled').exclude(id=appointment.id).exists()
        if existing:
            return Response({'message': 'Time slot is already booked.'}, status=status.HTTP_400_BAD_REQUEST)

        appointment.date = selected_dt
        appointment.time_slot = time_slot
        appointment.status = 'Pending'
        appointment.save(update_fields=['date', 'time_slot', 'status', 'updated_at'])
        log_audit(request, 'RESCHEDULE', 'Appointment')

        return Response({'success': True, 'data': serialize_appointment(appointment)}, status=status.HTTP_200_OK)


class AppointmentPrescriptionView(APIView):
    permission_classes = [IsAuthenticatedJWT]

    def get(self, request, appointment_id):
        prescription = Prescription.objects.filter(appointment_id=appointment_id).first()
        return Response({'success': True, 'data': serialize_prescription(prescription)}, status=status.HTTP_200_OK)

    def post(self, request, appointment_id):
        if request.user.role != 'Doctor':
            return Response(
                {'message': f'User role {request.user.role} is not authorized to access this route'},
                status=status.HTTP_403_FORBIDDEN,
            )

        appointment = Appointment.objects.filter(id=appointment_id).first()
        if not appointment:
            return Response({'message': 'Appointment not found'}, status=status.HTTP_404_NOT_FOUND)

        data = request.data or {}
        prescription = Prescription.objects.create(
            appointment=appointment,
            patient=appointment.patient,
            doctor=appointment.doctor,
            medications=data.get('medications') or [],
            instructions=data.get('instructions') or '',
        )
        log_audit(request, 'CREATE', 'Prescription')
        return Response({'success': True, 'data': serialize_prescription(prescription)}, status=status.HTTP_201_CREATED)


class AvailableSlotsView(APIView):
    permission_classes = [IsAuthenticatedJWT]

    def get(self, request):
        doctor_id = request.query_params.get('doctorId')
        date_raw = request.query_params.get('date')
        if not doctor_id or not date_raw:
            return Response({'message': 'Doctor ID and date required'}, status=status.HTTP_400_BAD_REQUEST)

        doctor = Doctor.objects.filter(id=doctor_id).first()
        if not doctor:
            return Response({'message': 'Doctor not found'}, status=status.HTTP_404_NOT_FOUND)

        selected_dt = parse_flexible_datetime(date_raw)
        if not selected_dt:
            return Response({'message': 'Invalid date'}, status=status.HTTP_400_BAD_REQUEST)

        booked_slots = set(
            Appointment.objects.filter(doctor_id=doctor_id, date__date=selected_dt.date())
            .exclude(status='Cancelled')
            .values_list('time_slot', flat=True)
        )

        all_slots = doctor.available_time_slots or DEFAULT_SLOTS
        available_slots = [s for s in all_slots if s not in booked_slots]

        now_local = datetime.datetime.now()
        if selected_dt.date() == now_local.date():
            filtered = []
            for slot in available_slots:
                m = re.match(r'^(\d+):(\d+)\s+(AM|PM)$', slot.strip(), re.IGNORECASE)
                if not m:
                    filtered.append(slot)
                    continue
                h = int(m.group(1))
                mins = int(m.group(2))
                period = m.group(3).upper()
                if period == 'PM' and h != 12:
                    h += 12
                if period == 'AM' and h == 12:
                    h = 0
                if h > now_local.hour or (h == now_local.hour and mins > now_local.minute):
                    filtered.append(slot)
            available_slots = filtered

        return Response({'success': True, 'data': available_slots}, status=status.HTTP_200_OK)
