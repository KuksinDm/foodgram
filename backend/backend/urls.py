from api.views import ShortLinkViewSet
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('api.urls', namespace='api')),
    path('s/<str:short_id>/', ShortLinkViewSet.as_view(
        {'get': 'redirect_short_link'}), name='short-link-redirect'),
]
