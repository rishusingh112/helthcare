from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from core.models import FAQ
from core.authentication import IsAuthenticatedJWT, require_roles
from core.serializers import serialize_faq


class FAQListCreateView(APIView):
    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAuthenticatedJWT(), require_roles('Admin')()]
        return []

    def get(self, request):
        faqs = FAQ.objects.filter(is_active=True).order_by('order', 'created_at')
        return Response({'success': True, 'data': [serialize_faq(f) for f in faqs]})

    def post(self, request):
        data = request.data or {}
        question = (data.get('question') or '').strip()
        answer = (data.get('answer') or '').strip()
        if not question or not answer:
            return Response({'success': False, 'message': 'Question and answer are required'}, status=status.HTTP_400_BAD_REQUEST)

        faq = FAQ.objects.create(
            question=question,
            answer=answer,
            order=int(data.get('order') or 0),
            is_active=data.get('isActive', True) is not False,
        )
        return Response({'success': True, 'data': serialize_faq(faq)}, status=status.HTTP_201_CREATED)


class FAQAllView(APIView):
    permission_classes = [IsAuthenticatedJWT, require_roles('Admin')]

    def get(self, request):
        faqs = FAQ.objects.all().order_by('order', 'created_at')
        return Response({'success': True, 'data': [serialize_faq(f) for f in faqs]})


class FAQDetailView(APIView):
    permission_classes = [IsAuthenticatedJWT, require_roles('Admin')]

    def put(self, request, faq_id):
        faq = FAQ.objects.filter(id=faq_id).first()
        if not faq:
            return Response({'success': False, 'message': 'FAQ not found'}, status=status.HTTP_404_NOT_FOUND)

        data = request.data or {}
        if 'question' in data:
            faq.question = str(data['question']).strip()
        if 'answer' in data:
            faq.answer = str(data['answer']).strip()
        if 'order' in data and data['order'] is not None:
            faq.order = int(data['order'])
        if 'isActive' in data:
            faq.is_active = bool(data['isActive'])
        faq.save()
        return Response({'success': True, 'data': serialize_faq(faq)})

    def delete(self, request, faq_id):
        faq = FAQ.objects.filter(id=faq_id).first()
        if not faq:
            return Response({'success': False, 'message': 'FAQ not found'}, status=status.HTTP_404_NOT_FOUND)
        faq.delete()
        return Response({'success': True, 'message': 'FAQ deleted'})
