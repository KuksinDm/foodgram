from django.contrib import admin
from django.contrib.auth import get_user_model
from django.db.models import Count
from recipes.forms import RecipeForm, RecipeIngredientFormSet
from recipes.models import Favorite, Ingredient, Recipe, RecipeIngredient, Tag

User = get_user_model()


class RecipeIngredientInline(admin.TabularInline):
    model = RecipeIngredient
    formset = RecipeIngredientFormSet
    extra = 1


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    form = RecipeForm
    list_display = ('name', 'author', 'total_favorites')
    search_fields = ('name', 'author__username', 'author__email')
    list_filter = ('tags',)
    inlines = [RecipeIngredientInline]

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        queryset = queryset.annotate(total_favorites=Count('favorited_by'))
        return queryset

    def total_favorites(self, obj):
        return obj.total_favorites
    total_favorites.short_description = 'Total Favorites'


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = ('name', 'measurement_unit')
    search_fields = ('name',)


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff')
    search_fields = ('email', 'username')
    list_filter = ('is_staff', 'is_superuser', 'is_active')


admin.site.register(Tag)
admin.site.register(Favorite)
