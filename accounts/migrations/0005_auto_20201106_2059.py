# Generated by Django 3.1.3 on 2020-11-06 12:59

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0004_auto_20201106_1716'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='tweet',
            name='image',
        ),
        migrations.AddField(
            model_name='tweet',
            name='images',
            field=models.ManyToManyField(blank=True, null=True, to='accounts.Media', verbose_name='画像'),
        ),
    ]