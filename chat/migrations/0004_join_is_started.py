# Generated by Django 3.1.3 on 2020-11-21 13:51

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('chat', '0003_auto_20201121_2136'),
    ]

    operations = [
        migrations.AddField(
            model_name='join',
            name='is_started',
            field=models.BooleanField(default=False, verbose_name='開始'),
        ),
    ]