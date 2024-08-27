from django.contrib.auth import get_user_model
from rest_framework import serializers
from drf_extra_fields.fields import Base64ImageField

from recipes.models import (
    Ingredient,
    Recipe,
    RecipeIngredient,
    Tag
)
from recipes.constants import MIN_INGREDIENTS

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    avatar = serializers.ImageField(required=False, allow_null=True)
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
    """
    не знаю на сколько оправдано использование to_representation,
    или стоило просто сделать несколько разных Serializer'ов
    """
    def to_representation(self, instance):
        representation = super().to_representation(instance)
        request = self.context.get('request')
        view = self.context.get('view')

        if view and hasattr(view, 'basename') and view.basename == 'recipe':
            return representation

        if request and request.method == 'PUT':
            return {'avatar': representation.get('avatar')}

        if request and request.method == 'POST':
            representation.pop('avatar', None)
            representation.pop('is_subscribed', None)

        return representation

    def get_is_subscribed(self, obj):
        user = self.context.get('request').user
        if user.is_authenticated:
            return obj.following.filter(user=user).exists()
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


class RecipeSerializer(serializers.ModelSerializer):
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()
    image = Base64ImageField(required=False, allow_null=True)
    author = UserSerializer(read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    ingredients = serializers.ListField(write_only=True)

    class Meta:
        model = Recipe
        fields = (
            'id', 'tags', 'author', 'ingredients',
            'is_favorited', 'is_in_shopping_cart', 'name',
            'image', 'text', 'cooking_time'
        )

    def create(self, validated_data):
        tags = self.initial_data.get('tags')
        ingredients_data = validated_data.pop('ingredients')

        recipe = Recipe.objects.create(**validated_data)
        if tags:
            recipe.tags.set(tags)
        self._create_recipe_ingredients(recipe, ingredients_data)
        return recipe

    def update(self, instance, validated_data):
        tags = self.initial_data.get('tags')
        ingredients_data = validated_data.pop('ingredients', None)

        if tags is not None:
            instance.tags.set(tags)

        if ingredients_data is not None:
            instance.ingredients.clear()
            self._create_recipe_ingredients(instance, ingredients_data)

        return super().update(instance, validated_data)

    def _create_recipe_ingredients(self, recipe, ingredients_data):
        RecipeIngredient.objects.bulk_create([
            RecipeIngredient(
                recipe=recipe,
                ingredient=Ingredient.objects.get(id=ingredient['id']),
                amount=ingredient['amount']
            ) for ingredient in ingredients_data
        ])

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['ingredients'] = [
            {
                "id": ingredient.id,
                "name": ingredient.name,
                "measurement_unit": ingredient.measurement_unit,
                "amount": RecipeIngredient.objects.get(
                    recipe=instance, ingredient=ingredient).amount
            }
            for ingredient in instance.ingredients.all()
        ]
        return representation

    def get_is_favorited(self, obj):
        user = self.context.get('request').user
        if user.is_authenticated:
            return user.favorites.filter(recipe=obj).exists()
        return False

    def get_is_in_shopping_cart(self, obj):
        user = self.context.get('request').user
        if user.is_authenticated:
            return user.shopping_cart.filter(recipe=obj).exists()
        return False

    def get_short_link(self, obj):
        request = self.context.get('request')
        if request is not None:
            return request.build_absolute_uri(f'/api/recipes/{obj.short_id}/')
        return None

    def validate(self, attrs):
        tags = self.initial_data.get('tags')

        if tags is None:
            raise serializers.ValidationError(
                {'tags': 'Тэги обязательны.'})
        if not tags:
            raise serializers.ValidationError(
                {'tags': 'Тэги не могут быть пустыми.'})
        seen_tag_ids = set()
        for tag_id in tags:
            if tag_id in seen_tag_ids:
                raise serializers.ValidationError(
                    {'tags': 'Тэги не должны повторяться.'})
            seen_tag_ids.add(tag_id)
            if not Tag.objects.filter(id=tag_id).exists():
                raise serializers.ValidationError(
                    {'tags': f'Тэг с ID {tag_id} не существует.'})

        image = self.initial_data.get('image')
        if image is None or image.strip() == '':
            raise serializers.ValidationError(
                {'image': 'Изображение обязательно.'})

        ingredients = attrs.get('ingredients')

        if not ingredients:
            raise serializers.ValidationError(
                {'ingredients': 'Ингредиенты обязательны.'})
        seen_ingredient_ids = set()
        for ingredient in ingredients:
            ingredient_id = ingredient['id']
            if ingredient_id in seen_ingredient_ids:
                raise serializers.ValidationError(
                    {'ingredients': 'Ингредиенты не должны повторяться.'})
            seen_ingredient_ids.add(ingredient_id)
            if not Ingredient.objects.filter(id=ingredient_id).exists():
                raise serializers.ValidationError(
                    {'ingredients': f'Ингредиент с ID {ingredient_id}'
                      'не существует.'})
            if ingredient['amount'] < MIN_INGREDIENTS:
                raise serializers.ValidationError(
                    {'ingredients': 'Количество ингредиента '
                     'должно быть больше 0.'})

        return attrs


class ShortLinkRecipeSerializer(serializers.ModelSerializer):
    short_link = serializers.SerializerMethodField()

    class Meta:
        model = Recipe
        fields = ('short_link',)

    def get_short_link(self, obj):
        request = self.context.get('request')
        if request is not None:
            return request.build_absolute_uri(f'/api/recipes/{obj.short_id}/')
        return None

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['short-link'] = representation.pop('short_link')
        return representation


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
        request = self.context.get('request')
        recipes_limit = request.query_params.get('recipes_limit')
        recipes = obj.recipes.all()
        if recipes_limit:
            recipes = recipes[:int(recipes_limit)]
        return RecipeShortSerializer(recipes, many=True).data

    def get_is_subscribed(self, obj):
        user = self.context.get('request').user
        if user.is_authenticated:
            return user.follower.filter(following=obj).exists()
        return False


class ShoppingListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')

    def to_representation(self, instance):
        return {
            'id': instance.id,
            'name': instance.name,
            'image': instance.image.url if instance.image else None,
            'cooking_time': instance.cooking_time
        }


class ShoppingListDownloadSerializer(serializers.Serializer):
    content = serializers.CharField()

    def get_shopping_list_content(self, user):
        recipes = RecipeIngredient.objects.filter(
            recipe__in=user.shopping_cart.values_list('recipe', flat=True)
        )
        shopping_list = {}
        for item in recipes:
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
            f"{name} - {data['amount']} {data['measurement_unit']}"
            for name, data in shopping_list.items()
        ])

    def to_representation(self, instance):
        return {'content': instance}
