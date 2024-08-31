# Generated by Django 3.2.3 on 2024-08-31 10:50

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('recipes', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='recipe',
            name='short_id',
            field=models.CharField(blank=True, editable=False, max_length=11, unique=True),
        ),
        migrations.DeleteModel(
            name='ShortLink',
        ),
    ]
