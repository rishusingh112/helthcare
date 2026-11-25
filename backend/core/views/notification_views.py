from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from core.models import Notification
from core.authentication import IsAuthenticatedJWT
from core.serializers import serialize_notification


class NotificationsListView(APIView):
    permission_classes = [IsAuthenticatedJWT]

    def get(self, request):
        notifs = Notification.objects.filter(user=request.user).order_by('-created_at')[:50]
        return Response({'success': True, 'data': [serialize_notification(n) for n in notifs]})


class NotificationMarkReadView(APIView):
    permission_classes = [IsAuthenticatedJWT]

    def put(self, request, notif_id):
        notif = Notification.objects.filter(id=notif_id, user=request.user).first()
        if not notif:
            return Response({'message': 'Notification not found'}, status=status.HTTP_404_NOT_FOUND)
        notif.is_read = True
        notif.save(update_fields=['is_read', 'updated_at'])
        return Response({'success': True, 'data': serialize_notification(notif)})


class NotificationMarkAllReadView(APIView):
    permission_classes = [IsAuthenticatedJWT]

    def put(self, request):
        Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
        return Response({'success': True, 'message': 'All notifications marked as read'})
