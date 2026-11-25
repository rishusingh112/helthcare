from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from core.models import Review, Appointment, Doctor, Patient
from core.authentication import IsAuthenticatedJWT, require_roles
from core.serializers import serialize_review


class ReviewCreateView(APIView):
    permission_classes = [IsAuthenticatedJWT, require_roles('Patient')]

    def post(self, request):
        data = request.data or {}
        doctor_id = data.get('doctorId')
        appointment_id = data.get('appointmentId')
        rating = data.get('rating')
        comment = (data.get('comment') or '').strip()

        patient = Patient.objects.filter(user=request.user).first()
        if not patient:
            return Response({'message': 'Patient profile not found'}, status=status.HTTP_404_NOT_FOUND)

        appointment = Appointment.objects.filter(id=appointment_id).first()
        if not appointment:
            return Response({'message': 'Appointment not found'}, status=status.HTTP_404_NOT_FOUND)

        if appointment.patient_id != patient.id:
            return Response({'message': 'Not authorized to review this appointment'}, status=status.HTTP_403_FORBIDDEN)

        if appointment.status != 'Completed':
            return Response({'message': 'Can only review completed appointments'}, status=status.HTTP_400_BAD_REQUEST)

        if Review.objects.filter(appointment_id=appointment_id).exists():
            return Response({'message': 'You have already reviewed this appointment'}, status=status.HTTP_400_BAD_REQUEST)

        doctor = Doctor.objects.filter(id=doctor_id).first()
        if not doctor:
            return Response({'message': 'Doctor not found'}, status=status.HTTP_404_NOT_FOUND)

        review = Review.objects.create(
            patient=patient,
            doctor=doctor,
            appointment=appointment,
            rating=int(rating),
            comment=comment,
        )

        approved = list(Review.objects.filter(doctor=doctor, status='approved'))
        total_reviews = len(approved)
        avg = round(sum(r.rating for r in approved) / total_reviews, 1) if total_reviews > 0 else 0
        doctor.average_rating = avg
        doctor.total_reviews = total_reviews
        doctor.save(update_fields=['average_rating', 'total_reviews', 'updated_at'])

        return Response({'success': True, 'data': serialize_review(review)}, status=status.HTTP_201_CREATED)


class DoctorReviewsView(APIView):
    def get(self, request, doctor_id):
        reviews = (
            Review.objects.select_related('patient')
            .filter(doctor_id=doctor_id, status='approved')
            .order_by('-created_at')
        )
        return Response(
            {
                'success': True,
                'count': len(reviews),
                'data': [serialize_review(r, populate_patient=True) for r in reviews],
            }
        )


class PublicReviewsView(APIView):
    def get(self, request):
        reviews = (
            Review.objects.select_related('patient', 'doctor')
            .filter(status='approved', rating=5)
            .order_by('-created_at')[:6]
        )
        return Response(
            {
                'success': True,
                'count': len(reviews),
                'data': [serialize_review(r, populate_patient=True, populate_doctor=True) for r in reviews],
            }
        )
