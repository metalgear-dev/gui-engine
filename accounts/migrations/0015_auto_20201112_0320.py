# Generated by Django 3.1.3 on 2020-11-11 19:20

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0014_auto_20201112_0241'),
    ]

    operations = [
        migrations.AlterField(
            model_name='member',
            name='word',
            field=models.CharField(default='', max_length=190, verbose_name='今日のひとこと'),
        ),
    ]
