# Generated by Django 4.2.10 on 2024-05-18 14:13

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('base', '0005_room_price'),
    ]

    operations = [
        migrations.AddField(
            model_name='room',
            name='payees',
            field=models.ManyToManyField(related_name='paid_rooms', to=settings.AUTH_USER_MODEL),
        ),
    ]