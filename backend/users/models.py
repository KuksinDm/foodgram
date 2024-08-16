from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model

from api.constants import (MAX_EMAIL_LENGTH, MAX_USER_LENGTH)
# from api.validators import characters_validator, validate_username


class CustomUser(AbstractUser):
    email = models.EmailField(
        'Электронная почта',
        max_length=MAX_EMAIL_LENGTH,
        unique=True,
        help_text='Обязательное поле, не может быть пустым.'
    )
    username = models.CharField(
        'Имя пользователя',
        max_length=MAX_USER_LENGTH,
        unique=True,
        help_text='Обязательное поле, не может быть пустым.',
        # validators=[characters_validator, validate_username],
        error_messages={
            'unique': 'Пользователь с таким именем уже существует.',
        },
    )
    first_name = models.CharField(
        'Имя',
        max_length=MAX_USER_LENGTH,
        blank=True
    )
    last_name = models.CharField(
        'Фамилия',
        max_length=MAX_USER_LENGTH,
        blank=True
    )

    class Meta:

        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'

    def __str__(self):
        return self.username


User = get_user_model()


class Follow(models.Model):
    user = models.ForeignKey(
        User,
        verbose_name='Кто подписан',
        on_delete=models.CASCADE,
        related_name='follower'
    )
    following = models.ForeignKey(
        User,
        verbose_name='На кого подписан',
        on_delete=models.CASCADE,
        related_name='following'
    )

    class Meta:
        verbose_name = 'подписка'
        verbose_name_plural = 'Подписка'
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'following'],
                name='unique_follow')
        ]

    def clean(self):
        if self.user == self.following:
            raise ValidationError(
                "Пользователь не может подписаться сам на себя.")
        if Follow.objects.filter(
            user=self.user,
            following=self.following
        ).exists():
            raise ValidationError("Такая подписка уже существует.")

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.user} подписался на {self.following}'
