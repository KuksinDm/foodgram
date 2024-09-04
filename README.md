# Проект YaMDb

## Описание
Проект Foodgram — это онлайн-сервис, где пользователи могут делиться рецептами различных блюд, загружать их с фотографиями, а также просматривать рецепты других пользователей. На платформе можно подписываться на любимых авторов, добавлять понравившиеся рецепты в избранное и использовать удобную функцию для добавления ингредиентов в корзину. Кроме того, пользователи могут скачать список покупок с точным количеством ингредиентов, необходимым для приготовления выбранных блюд.

Создавать ингредиенты и тэги, используемые в рецептах, может только администратор. 
Все действия, связанные с публикацией рецептов и взаимодействием с ними, доступны только аутентифицированным пользователям.

### Cписок используемых технологий:
<div align="center">
	<img width="50" src="https://user-images.githubusercontent.com/25181517/183423507-c056a6f9-1ba8-4312-a350-19bcbc5a8697.png" alt="Python" title="Python"/>
	<img width="50" src="https://github.com/marwin1991/profile-technology-icons/assets/62091613/9bf5650b-e534-4eae-8a26-8379d076f3b4" alt="Django" title="Django"/>
  <img width="50" src="https://s3.amazonaws.com/media-p.slid.es/uploads/708405/images/4005243/django_rest_500x500.png" alt="DjangoRestFramework" title="DjangoRestFramework"/>
	<img width="50" src="https://user-images.githubusercontent.com/25181517/192109061-e138ca71-337c-4019-8d42-4792fdaa7128.png" alt="Postman" title="Postman"/>
  <img width="50" src="https://www.postgresql.org/media/img/about/press/elephant.png" alt="PostgreSQL" title="PostgreSQL"/>
</div>

## Установка

### Клонировать репозиторий и перейти в него в командной строке:

```
git clone https://github.com/KuksinDm/foodgram.git

cd foodgram
```

### Cоздать и активировать виртуальное окружение:

```
# Command for Windows:
python -m venv venv
source venv/Scripts/activate

# Command for Linux:
python3 -m venv venv
source venv/bin/activate
```

### Обновить пакетный менеджер pip:
```
python -m pip install --upgrade pip
```

### Установить зависимости из файла requirements.txt:

```
pip install -r requirements.txt
```

### Выполнить миграции:

```
python manage.py makemigrations

python manage.py migrate
```

## Примеры

Запросы доступные без токена:

GET http://127.0.0.1:8000/api/recipes/{id}/

Вернется рецепт
```json
{
  "id": "integer",
  "tags": [
    {
      "id": "integer",
      "name": "string",
      "slug": "string"
    }
  ],
  "author": {
    "email": "string",
    "id": "integer",
    "username": "string",
    "first_name": "string",
    "last_name": "string",
    "is_subscribed": "boolean",
    "avatar": "string <uri>"
  },
  "ingredients": [
    {
      "id": "integer",
      "name": "string",
      "measurement_unit": "string",
      "amount": "integer"
    }
  ],
  "is_favorited": "boolean",
  "is_in_shopping_cart": "boolean",
  "name": "string",
  "image": "string <uri>",
  "text": "string",
  "cooking_time": "integer"
}
```

## Автор:
• [Дмитрий](https://github.com/KuksinDm) - Написал весь бэекэнд
