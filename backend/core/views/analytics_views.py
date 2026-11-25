import datetime
from django.db.models import Count
from django.db.models.functions import TruncDate
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from core.models import User, Patient, Doctor, Appointment
from core.authentication import IsAuthenticatedJWT, require_roles


class AnalyticsView(APIView):
    permission_classes = [IsAuthenticatedJWT, require_roles('Admin')]

    def get(self, request):
        total_patients = Patient.objects.count()
        total_doctors = Doctor.objects.count()
        total_appointments = Appointment.objects.count()
        active_users = User.objects.filter(status='Active').count()

        status_rows = (
            Appointment.objects.values('status')
            .annotate(count=Count('id'))
            .order_by('status')
        )
        appointments_by_status = [
            {'_id': row['status'], 'count': row['count']} for row in status_rows
        ]

        seven_days_ago = timezone.now() - datetime.timedelta(days=7)
        trend_rows = (
            Appointment.objects.filter(created_at__gte=seven_days_ago)
            .annotate(day=TruncDate('created_at'))
            .values('day')
            .annotate(count=Count('id'))
            .order_by('day')
        )
        appointments_trend = [
            {'_id': row['day'].strftime('%Y-%m-%d'), 'count': row['count']}
            for row in trend_rows
            if row['day'] is not None
        ]

        data = {
            'totalPatients': total_patients,
            'totalDoctors': total_doctors,
            'totalAppointments': total_appointments,
            'activeUsers': active_users,
            'appointmentsByStatus': appointments_by_status,
            'appointmentsTrend': appointments_trend,
        }
        return Response({'success': True, 'data': data, 'source': 'db'}, status=status.HTTP_200_OK)
