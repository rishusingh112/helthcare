import os
import random
import time
from django.conf import settings
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework import status

from core.models import Message, Appointment, Doctor, Patient
from core.authentication import IsAuthenticatedJWT
from core.serializers import serialize_message


def _build_conversation_id(id1: str, id2: str) -> str:
    return '_'.join(sorted([str(id1), str(id2)]))


class ConversationsView(APIView):
    permission_classes = [IsAuthenticatedJWT]

    def get(self, request):
        role = request.user.role
        if role == 'Patient':
            patient = Patient.objects.filter(user=request.user).first()
            if not patient:
                return Response({'success': True, 'data': []})

            appointments = Appointment.objects.select_related('doctor').filter(
                patient=patient,
                status='Confirmed',
            )
            seen = set()
            conversations = []
            for appt in appointments:
                doc = appt.doctor
                if not doc or doc.id in seen:
                    continue
                seen.add(doc.id)
                conv_id = _build_conversation_id(patient.id, doc.id)
                last_msg = Message.objects.filter(conversation_id=conv_id).order_by('-created_at').first()
                unread = Message.objects.filter(
                    conversation_id=conv_id,
                    sender_role='Doctor',
                    read_at__isnull=True,
                ).count()
                conversations.append({
                    'conversationId': conv_id,
                    'participant': {
                        'id': doc.id,
                        'userId': doc.user_id,
                        'name': f'Dr. {doc.first_name} {doc.last_name}',
                        'specialization': doc.specialization,
                        'avatar': doc.avatar,
                        'role': 'Doctor',
                    },
                    'lastMessage': serialize_message(last_msg),
                    'unreadCount': unread,
                })
            return Response({'success': True, 'data': conversations})

        if role == 'Doctor':
            doctor = Doctor.objects.filter(user=request.user).first()
            if not doctor:
                return Response({'success': True, 'data': []})

            appointments = Appointment.objects.select_related('patient').filter(
                doctor=doctor,
                status='Confirmed',
            )
            seen = set()
            conversations = []
            for appt in appointments:
                pat = appt.patient
                if not pat or pat.id in seen:
                    continue
                seen.add(pat.id)
                conv_id = _build_conversation_id(pat.id, doctor.id)
                last_msg = Message.objects.filter(conversation_id=conv_id).order_by('-created_at').first()
                unread = Message.objects.filter(
                    conversation_id=conv_id,
                    sender_role='Patient',
                    read_at__isnull=True,
                ).count()
                conversations.append({
                    'conversationId': conv_id,
                    'participant': {
                        'id': pat.id,
                        'userId': pat.user_id,
                        'name': f'{pat.first_name} {pat.last_name}',
                        'avatar': pat.avatar,
                        'role': 'Patient',
                    },
                    'lastMessage': serialize_message(last_msg),
                    'unreadCount': unread,
                })
            return Response({'success': True, 'data': conversations})

        return Response({'success': True, 'data': []})


class MessagesView(APIView):
    permission_classes = [IsAuthenticatedJWT]

    def get(self, request, conversation_id):
        page = max(int(request.query_params.get('page') or 1), 1)
        limit = 50
        start = (page - 1) * limit
        msgs = list(
            Message.objects.filter(conversation_id=conversation_id)
            .order_by('-created_at')[start:start + limit]
        )
        msgs.reverse()
        return Response({'success': True, 'data': [serialize_message(m) for m in msgs]})


class SendMessageView(APIView):
    permission_classes = [IsAuthenticatedJWT]

    def post(self, request):
        data = request.data or {}
        conversation_id = data.get('conversationId')
        if not conversation_id:
            return Response(
                {'success': False, 'message': 'conversationId is required'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        text = data.get('text')
        clean_text = text.strip() if isinstance(text, str) and text.strip() else None
        attachment = data.get('attachment')
        clean_attachment = attachment if isinstance(attachment, dict) and attachment.get('url') else None

        if not clean_text and not clean_attachment:
            return Response(
                {'success': False, 'message': 'Message must have text or attachment'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        msg = Message.objects.create(
            conversation_id=conversation_id,
            sender=request.user,
            sender_role=request.user.role,
            text=clean_text,
            attachment=clean_attachment,
            is_call_log=bool(data.get('isCallLog', False)),
        )
        return Response({'success': True, 'data': serialize_message(msg)}, status=status.HTTP_201_CREATED)


class ChatUploadView(APIView):
    permission_classes = [IsAuthenticatedJWT]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        uploaded = request.FILES.get('file')
        if not uploaded:
            return Response({'success': False, 'message': 'No file uploaded'}, status=status.HTTP_400_BAD_REQUEST)

        ext = os.path.splitext(uploaded.name)[1].lower()
        allowed_exts = {'.jpeg', '.jpg', '.png', '.gif', '.webp', '.pdf', '.doc', '.docx', '.txt', '.xlsx', '.csv'}
        if ext not in allowed_exts:
            return Response({'success': False, 'message': 'File type not allowed'}, status=status.HTTP_400_BAD_REQUEST)

        upload_dir = os.path.join(settings.MEDIA_ROOT, 'chat')
        os.makedirs(upload_dir, exist_ok=True)
        filename = f'{int(time.time() * 1000)}-{random.randint(100000, 999999999)}{ext}'
        filepath = os.path.join(upload_dir, filename)
        with open(filepath, 'wb+') as dest:
            for chunk in uploaded.chunks():
                dest.write(chunk)

        is_image = (uploaded.content_type or '').startswith('image/')
        url = f'{settings.BASE_URL}/uploads/chat/{filename}'
        return Response(
            {
                'success': True,
                'data': {
                    'url': url,
                    'type': 'image' if is_image else 'file',
                    'name': uploaded.name,
                    'size': uploaded.size,
                },
            },
            status=status.HTTP_200_OK,
        )


class MarkReadView(APIView):
    permission_classes = [IsAuthenticatedJWT]

    def post(self, request, conversation_id):
        other_role = 'Doctor' if request.user.role == 'Patient' else 'Patient'
        Message.objects.filter(
            conversation_id=conversation_id,
            sender_role=other_role,
            read_at__isnull=True,
        ).update(read_at=timezone.now())
        return Response({'success': True}, status=status.HTTP_200_OK)


class IceServersView(APIView):
    permission_classes = [IsAuthenticatedJWT]

    def get(self, request):
        return Response(
            {
                'iceServers': [
                    {'urls': 'stun:stun.l.google.com:19302'},
                    {'urls': 'stun:stun1.l.google.com:19302'},
                ]
            },
            status=status.HTTP_200_OK,
        )
