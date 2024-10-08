from django.contrib.auth import get_user_model
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from .serializers import (
    AvatarSerializer,
    FollowSerializer,
    IngredientSerializer,
    PasswordSerializer,
    RecipeSerializer,
    RecipeShortSerializer,
    ShoppingListDownloadSerializer,
    ShortLinkSerializer,
    SubscriptionSerializer,
    TagSerializer,
    UserSerializer,
)
from recipes.filters import IngredientFilter, RecipeFilter, UserFilter
from recipes.models import Favorite, Ingredient, Recipe, ShoppingList, Tag
from recipes.pagination import PageLimitPaginator
from recipes.permissions import IsAuthorOrReadOnly
from users.models import Follow

User = get_user_model()


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    pagination_class = PageLimitPaginator
    permission_classes = (permissions.IsAuthenticated,)
    filter_backends = (DjangoFilterBackend, filters.OrderingFilter)
    filterset_class = UserFilter
    ordering_fields = '__all__'
    ordering = ['username']

    def get_permissions(self):
        return (
            [permissions.AllowAny()]
            if self.action in ['retrieve', 'list', 'create']
            else [permissions.IsAuthenticated()]
        )

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
        if request.method == 'PUT':
            avatar = request.data.get('avatar')
            if not avatar:
                raise ValidationError({'detail': 'Поле `avatar` обязательно.'})

            serializer = AvatarSerializer(
                request.user,
                data=request.data,
                context={'request': request}
            )
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(
                serializer.data,
                status=status.HTTP_200_OK
            )

        if request.method == 'DELETE':
            request.user.avatar = None
            request.user.save()
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
            following__user=request.user).prefetch_related(
                'recipes').order_by('pk')

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = FollowSerializer(
                page,
                many=True,
                context={'request': request}
            )
            return self.get_paginated_response(serializer.data)

        serializer = FollowSerializer(
            queryset,
            many=True,
            context={'request': request}
        )
        return Response(serializer.data, status=status.HTTP_200_OK)

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
            serializer = SubscriptionSerializer(
                data={'user_id': pk},
                context={'request': request}
            )
            serializer.is_valid(raise_exception=True)

            follow, created = Follow.objects.get_or_create(
                user=user,
                following=following
            )
            if not created:
                return Response(
                    {'detail': 'Вы уже подписаны на этого пользователя.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            return Response(FollowSerializer(
                following,
                context={'request': request}).data,
                status=status.HTTP_201_CREATED
            )

        if request.method == 'DELETE':
            subscription = user.follower.filter(following=following)
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
    permission_classes = (
        permissions.IsAuthenticatedOrReadOnly,
        IsAuthorOrReadOnly
    )
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
        serializer = self.get_serializer(
            self.object, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)

    def destroy(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.object.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    def _manage_item(
            self,
            request,
            pk,
            model,
            error_message_exists,
            error_message_not_found
    ):
        user = request.user
        recipe = get_object_or_404(Recipe, pk=pk)

        if request.method == 'POST':
            if model.objects.filter(user=user, recipe=recipe).exists():
                return Response(
                    {'detail': error_message_exists},
                    status=status.HTTP_400_BAD_REQUEST
                )
            model.objects.create(user=user, recipe=recipe)
            serializer = RecipeShortSerializer(
                recipe,
                context={'request': request}
            )
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        if request.method == 'DELETE':
            deleted, _ = model.objects.filter(
                user=user, recipe=recipe).delete()
            if not deleted:
                return Response(
                    {'detail': error_message_not_found},
                    status=status.HTTP_400_BAD_REQUEST
                )
            return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=True,
        methods=['GET'],
        url_path='get-link'
    )
    def get_link(self, request, pk=None):
        recipe = get_object_or_404(Recipe, pk=pk)
        serializer = ShortLinkSerializer(recipe, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(
        detail=True,
        methods=['POST', 'DELETE'],
        permission_classes=(permissions.IsAuthenticated,),
        url_path='shopping_cart'
    )
    def manage_shopping_cart(self, request, pk=None):
        return self._manage_item(
            request,
            pk,
            model=ShoppingList,
            error_message_exists='Рецепт уже добавлен в корзину покупок.',
            error_message_not_found='Рецепт не найден в списке покупок.'
        )

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
        return self._manage_item(
            request,
            pk,
            model=Favorite,
            error_message_exists='Рецепт уже в избранном.',
            error_message_not_found='Рецепт не найден в избранном.'
        )


class ShortLinkViewSet(viewsets.ViewSet):
    permission_classes = (permissions.IsAuthenticatedOrReadOnly,)

    def redirect_short_link(self, request, short_id=None):
        recipe = get_object_or_404(Recipe, short_id=short_id)
        recipe_detail_url = f'/recipes/{recipe.id}/'
        return redirect(recipe_detail_url)
