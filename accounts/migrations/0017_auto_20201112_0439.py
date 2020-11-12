# Generated by Django 3.1.3 on 2020-11-11 20:39

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('basics', '0013_auto_20201108_1601'),
        ('accounts', '0016_member_cast_status'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='member',
            name='cast_status',
        ),
        migrations.CreateModel(
            name='CastStatus',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('cast', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='choices', to=settings.AUTH_USER_MODEL, verbose_name='キャスト')),
                ('choice', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='casts', to='basics.choice', verbose_name='チョイス')),
            ],
        ),
    ]
