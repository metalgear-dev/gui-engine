# Generated by Django 3.1.3 on 2020-11-06 05:25

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('basics', '0005_choice_receiptsetting'),
        ('accounts', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='member',
            name='location',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='basics.location', verbose_name='地域'),
        ),
        migrations.AlterField(
            model_name='member',
            name='role',
            field=models.IntegerField(choices=[(-1, 'admin'), (0, 'cast'), (1, 'guest'), (10, 'applier')], default=1, verbose_name='ユーザーロール'),
        ),
    ]