import os
import random
import time
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework import status

from core.authentication import IsAuthenticatedJWT


class UploadAvatarView(APIView):
    permission_classes = [IsAuthenticatedJWT]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        uploaded = request.FILES.get('avatar') or request.FILES.get('file')
        if not uploaded:
            return Response({'success': False, 'message': 'No image file uploaded'}, status=status.HTTP_400_BAD_REQUEST)

        ctype = (uploaded.content_type or '').lower()
        ext = os.path.splitext(uploaded.name)[1].lower()
        if not (ctype.startswith('image/') or ext in {'.jpg', '.jpeg', '.png', '.gif', '.webp'}):
            return Response(
                {'success': False, 'message': 'Only image files (JPEG, PNG, GIF, WebP) are allowed'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        upload_dir = os.path.join(settings.MEDIA_ROOT, 'avatars')
        os.makedirs(upload_dir, exist_ok=True)
        filename = f'{int(time.time() * 1000)}-{random.randint(100000, 999999999)}{ext or ".jpg"}'
        filepath = os.path.join(upload_dir, filename)
        with open(filepath, 'wb+') as dest:
            for chunk in uploaded.chunks():
                dest.write(chunk)

        return Response({'success': True, 'url': f'/uploads/avatars/{filename}'}, status=status.HTTP_200_OK)


class UploadDocumentView(APIView):
    # Note: Login.jsx uses /upload/document during public doctor registration before login,
    # while /uploads/document is authenticated. Allowing AllowAny or authenticated works for both!
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        uploaded = request.FILES.get('file') or request.FILES.get('document')
        if not uploaded:
            return Response({'success': False, 'message': 'No PDF file uploaded'}, status=status.HTTP_400_BAD_REQUEST)

        ctype = (uploaded.content_type or '').lower()
        ext = os.path.splitext(uploaded.name)[1].lower()
        if ctype != 'application/pdf' and ext != '.pdf':
            return Response({'success': False, 'message': 'Only PDF files are allowed'}, status=status.HTTP_400_BAD_REQUEST)

        upload_dir = os.path.join(settings.MEDIA_ROOT, 'documents')
        os.makedirs(upload_dir, exist_ok=True)
        filename = f'{int(time.time() * 1000)}-{random.randint(100000, 999999999)}{ext or ".pdf"}'
        filepath = os.path.join(upload_dir, filename)
        with open(filepath, 'wb+') as dest:
            for chunk in uploaded.chunks():
                dest.write(chunk)

        return Response({'success': True, 'url': f'/uploads/documents/{filename}'}, status=status.HTTP_200_OK)
