# Generated by Django 3.1.3 on 2020-11-06 09:16

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0003_favoritetweet_tweet'),
    ]

    operations = [
        migrations.RenameField(
            model_name='favoritetweet',
            old_name='favorite',
            new_name='tweet',
        ),
    ]