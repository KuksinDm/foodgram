from django import forms
from django.forms import BaseInlineFormSet, inlineformset_factory

from .models import Recipe, RecipeIngredient


class RecipeForm(forms.ModelForm):
    class Meta:
        model = Recipe
        fields = '__all__'

    def clean(self):
        cleaned_data = super().clean()
        return cleaned_data


class RecipeIngredientInlineFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()
        if any(self.errors):
            return

        has_ingredients = False

        for form in self.forms:
            if form.cleaned_data and not form.cleaned_data.get(
                'DELETE', False
            ):
                has_ingredients = True
                amount = form.cleaned_data.get('amount')
                if amount is None or amount <= 0:
                    raise forms.ValidationError(
                        'Количество для каждого '
                        'ингредиента должно быть больше нуля.'
                    )

        if not has_ingredients:
            raise forms.ValidationError(
                'Рецепт должен содержать хотя бы один ингредиент.')


RecipeIngredientFormSet = inlineformset_factory(
    Recipe,
    RecipeIngredient,
    formset=RecipeIngredientInlineFormSet,
    fields=('ingredient', 'amount'),
    extra=1
)
