from django.conf import settings
from django.contrib import admin
from django.http import HttpResponse
from django.urls import include, path, re_path
from django.views.static import serve


def root_health(_request):
    return HttpResponse('Healthcare Workflow System API is running...', content_type='text/plain')


urlpatterns = [
    path('', root_health),
    path('admin/', admin.site.urls),
    path('api/', include('core.urls')),
    re_path(r'^uploads/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
]
