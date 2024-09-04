from django.contrib.auth import get_user_model
from drf_extra_fields.fields import Base64ImageField
from rest_framework import serializers
from rest_framework.exceptions import NotFound, ValidationError

from recipes.constants import MAX_AMOUNT_COOK_TIME, MIN_AMOUNT_COOK_TIME
from recipes.models import Ingredient, Recipe, RecipeIngredient, Tag
from users.models import Follow

User = get_user_model()


class AvatarSerializer(serializers.ModelSerializer):
    avatar = Base64ImageField(required=False, allow_null=True)

    class Meta:
        model = User
        fields = ('avatar',)


class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    avatar = Base64ImageField(read_only=True)
    is_subscribed = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            'email',
            'id',
            'username',
            'first_name',
            'last_name',
            'password',
            'avatar',
            'is_subscribed'
        )

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        request = self.context.get('request')
        view = self.context.get('view')

        if view and hasattr(view, 'basename') and view.basename == 'recipe':
            return representation

        if request and request.method == 'POST':
            representation.pop('avatar', None)
            representation.pop('is_subscribed', None)

        return representation

    def get_is_subscribed(self, obj):
        request = self.context['request']

        if request.user.is_authenticated:
            return obj.following.filter(user=request.user).exists()
        return False

    def validate(self, attrs):
        if 'password' not in attrs:
            raise serializers.ValidationError(
                {'password': 'Пароль обязателен.'})
        if 'first_name' not in attrs:
            raise serializers.ValidationError(
                {'first_name': 'Имя обязательно.'})
        if 'last_name' not in attrs:
            raise serializers.ValidationError(
                {'last_name': 'Фамилия обязательна.'})
        return attrs

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = User.objects.create_user(**validated_data)
        user.set_password(password)
        user.save()
        return user


class SubscriptionSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()

    def validate_user_id(self, value):
        request = self.context.get('request')
        user = request.user

        if user.id == value:
            raise serializers.ValidationError('Нельзя подписаться на себя.')

        following = User.objects.filter(pk=value).first()

        if not following:
            raise NotFound('Пользователь не найден.')

        if Follow.objects.filter(user=user, following=following).exists():
            raise serializers.ValidationError(
                'Вы уже подписаны на этого пользователя.')

        return value

    def create(self, validated_data):
        user = self.context['request'].user
        following = User.objects.get(pk=validated_data['user_id'])
        Follow.objects.create(user=user, following=following)
        return following


class PasswordSerializer(serializers.Serializer):
    new_password = serializers.CharField()
    current_password = serializers.CharField()


class TagSerializer(serializers.ModelSerializer):

    class Meta:
        model = Tag
        fields = ('id', 'name', 'slug')


class IngredientSerializer(serializers.ModelSerializer):

    class Meta:
        model = Ingredient
        fields = ('id', 'name', 'measurement_unit')


class IngredientInRecipeSerializer(serializers.ModelSerializer):
    id = serializers.PrimaryKeyRelatedField(
        queryset=Ingredient.objects.all(),
        source='ingredient.id'
    )
    name = serializers.ReadOnlyField(source='ingredient.name')
    measurement_unit = serializers.ReadOnlyField(
        source='ingredient.measurement_unit'
    )

    class Meta:
        model = RecipeIngredient
        fields = ('id', 'name', 'measurement_unit', 'amount')


class RecipeSerializer(serializers.ModelSerializer):
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()
    image = Base64ImageField(required=False, allow_null=False)
    author = serializers.ReadOnlyField(source='author.username')
    tags = TagSerializer(many=True, read_only=True)
    ingredients = IngredientInRecipeSerializer(
        many=True,
        source='recipeingredient_set')
    cooking_time = serializers.IntegerField(
        min_value=MIN_AMOUNT_COOK_TIME,
        max_value=MAX_AMOUNT_COOK_TIME
    )

    class Meta:
        model = Recipe
        fields = (
            'id', 'tags', 'author', 'ingredients',
            'is_favorited', 'is_in_shopping_cart', 'name',
            'image', 'text', 'cooking_time'
        )

    def validate_ingredients(self, value):
        if not value:
            raise ValidationError(
                'Необходимо добавить хотя бы один ингредиент.')
        unique_ingredients = set()
        for item in value:
            if item['ingredient']['id'] in unique_ingredients:
                raise ValidationError('Ингредиенты должны быть уникальными.')
            unique_ingredients.add(item['ingredient']['id'])
        return value

    def validate_tags(self, value):
        if not value:
            raise ValidationError('Необходимо указать хотя бы один тег.')
        if not isinstance(value, list):
            raise ValidationError('Теги должны быть переданы в виде списка.')
        if not all(isinstance(tag_id, int) for tag_id in value):
            raise ValidationError('Каждый тег должен быть целым числом.')

        existing_tags = Tag.objects.in_bulk(value)
        if len(existing_tags) != len(value):
            non_existing_tags = set(value) - set(existing_tags.keys())
            raise ValidationError(
                'Указан несуществующий тег: '
                f'{", ".join(map(str, non_existing_tags))}'
            )
        if len(value) != len(set(value)):
            raise ValidationError('Теги должны быть уникальными.')
        return value

    def validate_image(self, value):
        if not value:
            raise ValidationError('Изображение является обязательным.')
        return value

    def create(self, validated_data):
        tags_data = self.initial_data.get('tags', None)
        if not tags_data:
            raise ValidationError({'tags': 'Это поле обязательно.'})

        ingredients_data = validated_data.pop('recipeingredient_set', None)
        if not ingredients_data:
            raise ValidationError({'ingredients': 'Это поле обязательно.'})
        image = validated_data.get('image', None)
        if not image:
            raise ValidationError({'image': 'Это поле обязательно.'})

        self.validate_tags(tags_data)

        recipe = Recipe.objects.create(**validated_data)

        for ingredient in ingredients_data:
            RecipeIngredient.objects.create(
                recipe=recipe,
                ingredient=ingredient['ingredient']['id'],
                amount=ingredient['amount']
            )
        recipe.tags.set(tags_data)
        return recipe

    def update(self, instance, validated_data):

        tags_data = self.initial_data.get('tags', [])
        ingredients_data = validated_data.pop('recipeingredient_set', [])
        image = validated_data.pop('image', None)
        if not ingredients_data:
            raise ValidationError({'ingredients': 'Это поле обязательно.'})

        self.validate_tags(tags_data)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        if image is not None:
            instance.image = image

        instance.save()

        instance.tags.set(tags_data)

        instance.recipeingredient_set.all().delete()

        for ingredient in ingredients_data:
            RecipeIngredient.objects.create(
                recipe=instance,
                ingredient=ingredient['ingredient']['id'],
                amount=ingredient['amount']
            )

        return instance

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        request = self.context['request']
        user = request.user
        representation['author'] = {
            'email': instance.author.email,
            'id': instance.author.id,
            'username': instance.author.username,
            'first_name': instance.author.first_name,
            'last_name': instance.author.last_name,
            'avatar': (instance.author.avatar.url
                       if instance.author.avatar else None),
            'is_subscribed': (user.is_authenticated
                              and instance.author.following.filter
                              (user=user).exists())
        }
        return representation

    def get_is_favorited(self, obj):
        request = self.context['request']
        return request.user.is_authenticated and request.user.favorites.filter(
            recipe=obj).exists()

    def get_is_in_shopping_cart(self, obj):
        request = self.context['request']
        return (request.user.is_authenticated
                and request.user.shopping_cart.filter(recipe=obj).exists())


class RecipeShortSerializer(serializers.ModelSerializer):
    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')


class FollowSerializer(serializers.ModelSerializer):
    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.IntegerField(
        source='recipes.count',
        read_only=True
    )
    is_subscribed = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            'email', 'id', 'username', 'first_name', 'last_name',
            'is_subscribed', 'recipes', 'recipes_count', 'avatar'
        )

    def get_recipes(self, obj):
        request = self.context['request']
        recipes_limit = request.query_params.get('recipes_limit')
        recipes = obj.recipes.all().prefetch_related('author')
        if recipes_limit:
            recipes = recipes[:int(recipes_limit)]
        return RecipeShortSerializer(recipes, many=True).data

    def get_is_subscribed(self, obj):
        request = self.context['request']

        if request.user.is_authenticated:
            return request.user.follower.filter(following=obj).exists()

        return False


class ShoppingListDownloadSerializer(serializers.Serializer):
    content = serializers.CharField()

    def get_shopping_list_content(self, user):
        shopping_list = {}
        for item in RecipeIngredient.objects.filter(
                recipe__in=user.shopping_cart.values_list(
                    'recipe', flat=True)):
            name = item.ingredient.name
            measurement_unit = item.ingredient.measurement_unit
            amount = item.amount

            if name in shopping_list:
                shopping_list[name]['amount'] += amount
            else:
                shopping_list[name] = {
                    'measurement_unit': measurement_unit,
                    'amount': amount
                }

        return '\n'.join([
            f'{name} - {data["amount"]} {data["measurement_unit"]}'
            for name, data in shopping_list.items()
        ])

    def to_representation(self, instance):
        return {'content': instance}


class ShortLinkSerializer(serializers.Serializer):
    short_link = serializers.SerializerMethodField()

    def get_short_link(self, obj):
        request = self.context['request']
        short_id = obj.short_id
        if short_id:
            return request.build_absolute_uri(f'/s/{short_id}/')
        return None

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['short-link'] = representation.pop('short_link')
        return representation
