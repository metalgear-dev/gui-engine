# Generated by Django 3.1.3 on 2020-11-21 20:25

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0028_auto_20201121_0418'),
    ]

    operations = [
        migrations.AddField(
            model_name='member',
            name='group_times',
            field=models.IntegerField(default=0, verbose_name='グループ回数'),
        ),
        migrations.AddField(
            model_name='member',
            name='private_times',
            field=models.IntegerField(default=0, verbose_name='プライベート回数'),
        ),
    ]
