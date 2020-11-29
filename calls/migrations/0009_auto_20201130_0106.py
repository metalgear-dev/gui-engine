# Generated by Django 3.1.3 on 2020-11-29 17:06

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('calls', '0008_auto_20201130_0050'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='collect_ended_at',
            field=models.DateTimeField(blank=True, null=True, verbose_name='キャスト募集修了時刻'),
        ),
        migrations.AddField(
            model_name='order',
            name='collect_started_at',
            field=models.DateTimeField(blank=True, null=True, verbose_name='キャスト募集開始時刻'),
        ),
        migrations.AddField(
            model_name='order',
            name='cost_extended',
            field=models.IntegerField(default=0, verbose_name='延長料金'),
        ),
        migrations.AddField(
            model_name='order',
            name='cost_value',
            field=models.IntegerField(default=0, verbose_name='料金'),
        ),
        migrations.AddField(
            model_name='order',
            name='ended_at',
            field=models.DateTimeField(null=True, verbose_name='修了時刻'),
        ),
        migrations.AddField(
            model_name='order',
            name='ended_predict',
            field=models.DateTimeField(null=True, verbose_name='修了予定時刻'),
        ),
        migrations.AddField(
            model_name='order',
            name='remark',
            field=models.TextField(null=True, verbose_name='備考'),
        ),
    ]
