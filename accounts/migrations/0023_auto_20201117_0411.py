# Generated by Django 3.1.3 on 2020-11-16 20:11

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0022_delete_channel'),
    ]

    operations = [
        migrations.RenameField(
            model_name='transferinfo',
            old_name='rank_name',
            new_name='bank_name',
        ),
        migrations.RenameField(
            model_name='transferinfo',
            old_name='rank_no',
            new_name='bank_no',
        ),
    ]
