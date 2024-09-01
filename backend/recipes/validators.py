from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator

characters_validator = RegexValidator(
    regex=r'^[-a-zA-Z0-9_]+$',
    message=('Разрешены только символы латинского алфавита, '
             'цифры и знак подчёркивания')
)


username_validator = RegexValidator(
    regex=r'^[\w.@+-]+\Z',
    message='Разрешены только буквы, цифры и символы @/./+/-/_.'
)


def validate_username(value):
    if value.lower() == 'me':
        raise ValidationError('Имя пользователя "me" недопустимо.')
    return value
