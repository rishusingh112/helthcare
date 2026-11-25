from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from core.models import Service
from core.authentication import IsAuthenticatedJWT, require_roles
from core.serializers import serialize_service


class ServiceListCreateView(APIView):
    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAuthenticatedJWT(), require_roles('Admin')()]
        return []

    def get(self, request):
        services = Service.objects.all().order_by('created_at')
        return Response({'success': True, 'data': [serialize_service(s) for s in services]})

    def post(self, request):
        data = request.data or {}
        title = (data.get('title') or '').strip()
        description = data.get('description') or ''
        if not title or not description:
            return Response(
                {'success': False, 'message': 'Failed to create service', 'error': 'Title and description required'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        svc = Service.objects.create(
            title=title,
            description=description,
            tags=data.get('tags') or [],
            image=data.get('image') or '',
            icon_name=data.get('iconName') or 'Stethoscope',
        )
        return Response({'success': True, 'data': serialize_service(svc)}, status=status.HTTP_201_CREATED)


class ServiceDetailView(APIView):
    permission_classes = [IsAuthenticatedJWT, require_roles('Admin')]

    def put(self, request, service_id):
        svc = Service.objects.filter(id=service_id).first()
        if not svc:
            return Response({'success': False, 'message': 'Service not found'}, status=status.HTTP_404_NOT_FOUND)

        data = request.data or {}
        if 'title' in data:
            svc.title = str(data['title']).strip()
        if 'description' in data:
            svc.description = data['description']
        if 'tags' in data:
            svc.tags = data['tags'] or []
        if 'image' in data:
            svc.image = data['image'] or ''
        if 'iconName' in data:
            svc.icon_name = data['iconName'] or 'Stethoscope'
        svc.save()
        return Response({'success': True, 'data': serialize_service(svc)})

    def delete(self, request, service_id):
        svc = Service.objects.filter(id=service_id).first()
        if not svc:
            return Response({'success': False, 'message': 'Service not found'}, status=status.HTTP_404_NOT_FOUND)
        svc.delete()
        return Response({'success': True, 'data': {}})
