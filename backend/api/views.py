from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from django.db.models import Prefetch
from django.http import HttpResponse

from rest_framework import filters, permissions, status, viewsets
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.decorators import action
from rest_framework.response import Response

from .serializers import (
    FollowSerializer,
    RecipeSerializer,
    RecipeShortSerializer,
    IngredientSerializer,
    PasswordSerializer,
    ShoppingListSerializer,
    ShoppingListDownloadSerializer,
    ShortLinkRecipeSerializer,
    TagSerializer,
    UserSerializer
)
from recipes.filters import IngredientFilter, RecipeFilter
from recipes.models import Favorite, Recipe, Tag, Ingredient, ShoppingList
from users.models import Follow
from recipes.pagination import PageLimitPaginator


User = get_user_model()


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    pagination_class = PageLimitPaginator
    permission_classes = (permissions.IsAuthenticated,)

    def get_permissions(self):
        if self.action in ['retrieve', 'list', 'create']:
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]

    @action(
        detail=False,
        methods=['GET'],
        permission_classes=(permissions.IsAuthenticated,)
    )
    def me(self, request):
        serializer = UserSerializer(request.user, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(
        detail=False,
        methods=['PUT', 'DELETE'],
        permission_classes=(permissions.IsAuthenticated,),
        url_path='me/avatar'
    )
    def update_avatar(self, request):
        user = request.user
        avatar = request.data.get('avatar')

        if request.method == 'PUT':
            if avatar:
                user.avatar = avatar
                user.save()
                serializer = UserSerializer(user, context={'request': request})
                return Response(serializer.data, status=status.HTTP_200_OK)
            return Response(
                {'detail': 'Аватар не предоставлен.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if request.method == 'DELETE':
            user.avatar = None
            user.save()
            return Response(
                {'detail': 'Аватар успешно удален.'},
                status=status.HTTP_204_NO_CONTENT
            )

    @action(
        detail=False,
        methods=['POST'],
        permission_classes=(permissions.IsAuthenticated,)
    )
    def set_password(self, request):
        serializer = PasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        password = serializer.validated_data['current_password']
        new_password = serializer.validated_data['new_password']

        if request.user.check_password(password):
            request.user.set_password(new_password)
            request.user.save()
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response(
            {'detail': 'Неверный пароль.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    @action(
        detail=False,
        methods=['GET'],
        permission_classes=(permissions.IsAuthenticated,),
    )
    def subscriptions(self, request):
        queryset = User.objects.filter(
            following__user=request.user
        ).prefetch_related(
            Prefetch('recipes', queryset=Recipe.objects.all())
        ).order_by('pk')

        recipes_limit = request.query_params.get('recipes_limit')
        page = self.paginate_queryset(queryset)
        users = page if page else queryset
        serializer = FollowSerializer(
            users, many=True, context={'request': request}
        )

        data = serializer.data
        if recipes_limit is not None:
            recipes_limit = int(recipes_limit)
            for user_data in data:
                user_data['recipes'] = user_data['recipes'][:recipes_limit]

        return self.get_paginated_response(data) if page else Response(
            data,
            status=status.HTTP_200_OK
        )

    @action(
        detail=True,
        methods=['POST', 'DELETE'],
        permission_classes=(permissions.IsAuthenticated,),
        url_path='subscribe'
    )
    def manage_subscription(self, request, pk=None):
        user = request.user
        following = get_object_or_404(User, pk=pk)

        if request.method == 'POST':
            if user == following:
                return Response(
                    {'detail': 'Нельзя подписаться на себя.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            if Follow.objects.filter(user=user, following=following).exists():
                return Response(
                    {'detail': 'Вы уже подписаны на этого пользователя.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            Follow.objects.create(user=user, following=following)
            serializer = FollowSerializer(
                following,
                context={'request': request}
            )
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        if request.method == 'DELETE':
            subscription = Follow.objects.filter(
                user=user,
                following=following
            )
            if subscription.exists():
                subscription.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
            return Response(
                {'detail': 'Вы не подписаны на этого пользователя.'},
                status=status.HTTP_400_BAD_REQUEST
            )


class TagViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = (permissions.IsAuthenticatedOrReadOnly,)
    pagination_class = None


class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    permission_classes = (permissions.AllowAny,)
    filter_backends = (DjangoFilterBackend, filters.SearchFilter)
    filterset_class = IngredientFilter
    search_fields = ('name',)
    pagination_class = None


class RecipeViewSet(viewsets.ModelViewSet):
    queryset = Recipe.objects.all()
    serializer_class = RecipeSerializer
    permission_classes = (permissions.IsAuthenticatedOrReadOnly,)
    pagination_class = PageLimitPaginator
    filter_backends = (DjangoFilterBackend,)
    filterset_class = RecipeFilter

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context.update({'view': self})
        return context

    def update(self, request, *args, **kwargs):
        self.object = self.get_object()
        if request.user != self.object.author:
            return Response(
                {'detail': 'У вас нет прав редактировать этот рецепт.'},
                status=status.HTTP_403_FORBIDDEN
            )
        serializer = self.get_serializer(
            self.object, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)

    def destroy(self, request, *args, **kwargs):
        self.object = self.get_object()
        if request.user != self.object.author:
            return Response(
                {'detail': 'У вас нет прав удалять этот рецепт.'},
                status=status.HTTP_403_FORBIDDEN
            )
        self.object.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=True,
        methods=['GET'],
        permission_classes=(permissions.IsAuthenticatedOrReadOnly,),
        url_path='get-link'
    )
    def get_link(self, request, pk=None):
        recipe = self.get_object()
        serializer = ShortLinkRecipeSerializer(
            recipe, context={'request': request})
        return Response(serializer.data)

    @action(
        detail=True,
        methods=['post'],
        permission_classes=(permissions.IsAuthenticated,)
    )
    def shopping_cart(self, request, pk=None):
        user = request.user
        recipe = get_object_or_404(Recipe, pk=pk)

        if ShoppingList.objects.filter(user=user, recipe=recipe).exists():
            return Response(
                {'detail': 'Рецепт уже добавлен в корзину покупок.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        ShoppingList.objects.create(user=user, recipe=recipe)
        serializer = ShoppingListSerializer(recipe)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @shopping_cart.mapping.delete
    def remove_from_shopping_cart(self, request, pk=None):
        user = request.user
        recipe = get_object_or_404(Recipe, pk=pk)
        shopping_item = ShoppingList.objects.filter(user=user, recipe=recipe)
        if shopping_item.exists():
            shopping_item.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response(
            {'detail': 'Рецепт не найден в списке покупок.'},
            status=status.HTTP_400_BAD_REQUEST)

    @action(
        detail=False,
        methods=['get'],
        permission_classes=(permissions.IsAuthenticated,)
    )
    def download_shopping_cart(self, request):
        user = request.user
        content = ShoppingListDownloadSerializer(
        ).get_shopping_list_content(user)
        response = HttpResponse(content, content_type='text/plain')
        response['Content-Disposition'] = (
            'attachment; filename="shopping_list.txt"'
        )
        return response

    @action(
        detail=True,
        methods=['POST', 'DELETE'],
        permission_classes=(permissions.IsAuthenticated,),
        url_path='favorite'
    )
    def manage_favorites(self, request, pk=None):
        user = request.user
        recipe = get_object_or_404(Recipe, pk=pk)

        if request.method == 'POST':
            if Favorite.objects.filter(user=user, recipe=recipe).exists():
                return Response(
                    {'detail': 'Рецепт уже в избранном.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            Favorite.objects.create(user=user, recipe=recipe)
            serializer = RecipeShortSerializer(
                recipe,
                context={'request': request}
            )
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        if request.method == 'DELETE':
            favorite = Favorite.objects.filter(user=user, recipe=recipe)
            if favorite.exists():
                favorite.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
            return Response(
                {'detail': 'Рецепт не найден в избранном.'},
                status=status.HTTP_400_BAD_REQUEST
            )
