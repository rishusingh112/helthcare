from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from core.models import Doctor, Subscriber


class PublicDoctorsView(APIView):
    def get(self, request):
        doctors = (
            Doctor.objects.select_related('user')
            .filter(is_available=True, user__status='Active')
            .order_by('-created_at')[:50]
        )
        data = [
            {
                '_id': d.id,
                'firstName': d.first_name,
                'lastName': d.last_name,
                'specialization': d.specialization,
                'department': d.department,
                'bio': d.bio,
                'avatar': d.avatar or '',
                'experienceYears': d.experience_years,
                'consultationFee': d.consultation_fee,
                'qualifications': d.qualifications or [],
                'availableDays': d.available_days or [],
                'availableTimeSlots': d.available_time_slots or [],
                'isAvailable': d.is_available,
                'averageRating': d.average_rating or 0,
                'totalReviews': d.total_reviews or 0,
            }
            for d in doctors
        ]
        return Response({'success': True, 'count': len(data), 'data': data}, status=status.HTTP_200_OK)


class SubscribeNewsletterView(APIView):
    def post(self, request):
        email = str((request.data or {}).get('email') or '').lower().strip()
        if not email:
            return Response({'success': False, 'message': 'Email is required'}, status=status.HTTP_400_BAD_REQUEST)

        if Subscriber.objects.filter(email=email).exists():
            return Response(
                {'success': False, 'message': 'You are already subscribed!'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        Subscriber.objects.create(email=email)
        return Response(
            {'success': True, 'message': 'Successfully subscribed to the newsletter!'},
            status=status.HTTP_201_CREATED,
        )
