from django.urls import include, path
from rest_framework import routers

from .views import (
    IngredientViewSet,
    RecipeViewSet,
    ShortLinkViewSet,
    TagViewSet,
    UserViewSet)

app_name = 'api'

router_api = routers.DefaultRouter()

router_api.register('users', UserViewSet, basename='users')
router_api.register(r'tags', TagViewSet, basename='tags')
router_api.register('ingredients', IngredientViewSet)
router_api.register(r'recipes', RecipeViewSet)

urlpatterns = [
    path('auth/', include('djoser.urls')),
    path('auth/', include('djoser.urls.authtoken')),
    path('s/<str:short_id>/', ShortLinkViewSet.as_view(
        {'get': 'redirect_short_link'}), name='short-link-redirect'),
    path('', include(router_api.urls)),
]
