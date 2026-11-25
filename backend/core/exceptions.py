from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is not None:
        detail = response.data
        if isinstance(detail, dict):
            msg = detail.get('detail') or detail.get('message') or str(detail)
        elif isinstance(detail, list) and detail:
            msg = str(detail[0])
        else:
            msg = str(detail)

        # DRF returns 403 for NotAuthenticated when authenticate() returns None and permission fails;
        # match Express auth middleware which returns 401 when no token is provided.
        status_code = response.status_code
        if status_code == 403 and 'no token' in str(msg).lower():
            status_code = 401
        elif status_code == 403 and not getattr(context.get('request'), 'user', None):
            status_code = 401
            msg = 'Not authorized, no token'

        return Response({'success': False, 'message': str(msg)}, status=status_code)

    return Response(
        {'success': False, 'message': str(exc) or 'Internal server error'},
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )
