# Generated by Django 3.1.3 on 2020-11-12 08:33

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0018_member_cast_status'),
    ]

    operations = [
        migrations.DeleteModel(
            name='CastStatus',
        ),
    ]
