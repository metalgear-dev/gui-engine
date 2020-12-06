# Generated by Django 3.1.3 on 2020-12-05 14:27

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('calls', '0015_auto_20201205_0436'),
    ]

    operations = [
        migrations.AddField(
            model_name='join',
            name='dropped',
            field=models.BooleanField(default=False, verbose_name='却下'),
        ),
        migrations.AlterField(
            model_name='join',
            name='status',
            field=models.IntegerField(choices=[(0, 'ドラフト'), (1, '確定')], default=0, verbose_name='状態'),
        ),
    ]
