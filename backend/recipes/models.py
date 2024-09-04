import shortuuid
from django.contrib.auth import get_user_model
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from .constants import (
    MAX_AMOUNT_COOK_TIME,
    MAX_ID_LENGTH,
    MAX_INGREDIENT_LENGTH,
    MAX_LENGTH,
    MAX_MEASUREMENT_LENGTH,
    MAX_URL_LENGTH,
    MIN_AMOUNT_COOK_TIME,
    TAG_LENGTH,
)
from .validators import characters_validator

User = get_user_model()


class Tag(models.Model):
    name = models.CharField(
        max_length=TAG_LENGTH,
        unique=True,
        verbose_name='Название',
    )
    slug = models.SlugField(
        max_length=TAG_LENGTH,
        unique=True,
        verbose_name='Слаг',
        validators=[characters_validator]
    )

    class Meta:
        verbose_name = 'Тег'
        verbose_name_plural = 'Теги'
        ordering = ['name']

    def __str__(self):
        return self.name


class Ingredient(models.Model):
    name = models.CharField(
        max_length=MAX_INGREDIENT_LENGTH,
        verbose_name='Название ингридиента',
    )
    measurement_unit = models.CharField(
        max_length=MAX_MEASUREMENT_LENGTH,
        verbose_name='Единица измерения',
    )

    class Meta:
        verbose_name = 'Ингредиент'
        verbose_name_plural = 'Ингредиенты'
        ordering = ['name']

    def __str__(self):
        return self.name


class Recipe(models.Model):
    author = models.ForeignKey(
        User,
        verbose_name='Автор рецепта',
        on_delete=models.CASCADE,
        related_name='recipes',
    )
    name = models.CharField(
        max_length=MAX_LENGTH,
        unique=True,
        verbose_name='Название рецепта',
    )
    image = models.ImageField(
        upload_to='recipes/images/',
        null=True,
        default=None,
        verbose_name='Изображение рецепта'
    )
    text = models.TextField(
        verbose_name='Текст рецепта',
    )
    ingredients = models.ManyToManyField(
        Ingredient,
        through='RecipeIngredient',
        related_name='recipes',
        verbose_name='Ингредиенты рецепта'
    )
    tags = models.ManyToManyField(
        Tag,
        related_name='recipes',
        verbose_name='Тэги рецепта'
    )
    cooking_time = models.PositiveSmallIntegerField(
        verbose_name='Время приготовления рецепта',
        validators=[
            MinValueValidator(
                MIN_AMOUNT_COOK_TIME,
                'Минимальное время приготовления: '
                f'{MIN_AMOUNT_COOK_TIME} минута'
            ),
            MaxValueValidator(
                MAX_AMOUNT_COOK_TIME,
                'Максимальное время приготовления: '
                f'{MAX_AMOUNT_COOK_TIME} минут'
            )
        ]
    )
    pub_date = models.DateTimeField(
        verbose_name='Дата публикации',
        auto_now_add=True
    )
    short_id = models.CharField(
        max_length=MAX_ID_LENGTH,
        unique=True,
        blank=True,
        editable=False,
        verbose_name='Короткий идентификатор'
    )

    class Meta:
        verbose_name = 'Рецепт'
        verbose_name_plural = 'Рецепты'
        ordering = ['-pub_date']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.short_id:
            self.short_id = shortuuid.ShortUUID().random(length=MAX_URL_LENGTH)
        super().save(*args, **kwargs)


class RecipeIngredient(models.Model):
    recipe = models.ForeignKey(
        Recipe,
        verbose_name='Рецепт',
        on_delete=models.CASCADE
    )
    ingredient = models.ForeignKey(
        Ingredient,
        on_delete=models.CASCADE,
        verbose_name='Ингредиент',
    )
    amount = models.PositiveSmallIntegerField(
        verbose_name='Количество',
        validators=[
            MinValueValidator(
                MIN_AMOUNT_COOK_TIME,
                f'Минимальное количество ингредиента: {MIN_AMOUNT_COOK_TIME}'
            ),
            MaxValueValidator(
                MAX_AMOUNT_COOK_TIME,
                f'Максимальное количество ингредиента: {MAX_AMOUNT_COOK_TIME}'
            )
        ]
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['recipe', 'ingredient'],
                name='unique_recipe_ingredient'
            )
        ]
        verbose_name = 'Ингредиент в рецепте'
        verbose_name_plural = 'Ингредиенты в рецептах'
        ordering = ['recipe', 'ingredient']

    def __str__(self):
        return (
            f'{self.ingredient.name} - {self.amount} '
            f'{self.ingredient.measurement_unit} для '
            f'{self.recipe.name}'
        )


class Favorite(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='favorites',
        verbose_name='Автор'
    )
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name='favorited_by',
        verbose_name='Избранный рецепт'
    )

    class Meta:
        verbose_name = 'Избранный рецепт'
        verbose_name_plural = 'Избранные рецепты'
        ordering = ['user']

    def __str__(self):
        return self.user.username


class ShoppingList(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='shopping_cart',
        verbose_name='Покупатель'
    )
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name='in_shopping_carts',
        verbose_name='Рецепт для покупки'
    )

    class Meta:
        verbose_name = 'Список покупок'
        verbose_name_plural = 'Список покупок'
        ordering = ['user']

    def __str__(self):
        return self.user.username
