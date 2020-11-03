# Generated by Django 3.1.3 on 2020-11-03 14:41

import django.contrib.auth.models
import django.contrib.auth.validators
import django.core.validators
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
import django_resized.forms


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
        ('basics', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Media',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('uri', django_resized.forms.ResizedImageField(blank=True, crop=['middle', 'center'], force_format='JPEG', keep_meta=True, null=True, quality=75, size=[400, 400], upload_to='static/images', verbose_name='URI')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='作成日時')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新日時')),
            ],
        ),
        migrations.CreateModel(
            name='Member',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('password', models.CharField(max_length=128, verbose_name='password')),
                ('last_login', models.DateTimeField(blank=True, null=True, verbose_name='last login')),
                ('is_superuser', models.BooleanField(default=False, help_text='Designates that this user has all permissions without explicitly assigning them.', verbose_name='superuser status')),
                ('username', models.CharField(error_messages={'unique': 'A user with that username already exists.'}, help_text='Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only.', max_length=150, unique=True, validators=[django.contrib.auth.validators.UnicodeUsernameValidator()], verbose_name='username')),
                ('first_name', models.CharField(blank=True, max_length=150, verbose_name='first name')),
                ('last_name', models.CharField(blank=True, max_length=150, verbose_name='last name')),
                ('is_staff', models.BooleanField(default=False, help_text='Designates whether the user can log into this admin site.', verbose_name='staff status')),
                ('is_active', models.BooleanField(default=True, help_text='Designates whether this user should be treated as active. Unselect this instead of deleting accounts.', verbose_name='active')),
                ('date_joined', models.DateTimeField(default=django.utils.timezone.now, verbose_name='date joined')),
                ('deleted_at', models.DateTimeField(blank=True, null=True)),
                ('email', models.EmailField(blank=True, max_length=100, null=True, unique=True, verbose_name='メールアドレス')),
                ('social_type', models.IntegerField(choices=[(0, 'email'), (1, 'line'), (2, 'phone')], default=0, verbose_name='ソーシャルタイプ')),
                ('social_id', models.CharField(blank=True, max_length=100, null=True, verbose_name='ソーシャルID')),
                ('phone_number', models.CharField(blank=True, max_length=20, null=True, unique=True, verbose_name='電話番号')),
                ('nickname', models.CharField(blank=True, max_length=190, null=True, unique=True, verbose_name='ニックネーム')),
                ('is_registered', models.BooleanField(default=False, verbose_name='初期登録')),
                ('is_verified', models.BooleanField(default=False, verbose_name='メール確認')),
                ('verify_code', models.CharField(blank=True, max_length=100, null=True, verbose_name='認証コード')),
                ('birthday', models.DateTimeField(blank=True, null=True, verbose_name='誕生日')),
                ('word', models.CharField(blank=True, max_length=190, null=True, verbose_name='今日のひとこと')),
                ('about', models.TextField(blank=True, null=True, verbose_name='自己紹介')),
                ('point', models.IntegerField(default=0, verbose_name='ポイント')),
                ('role', models.IntegerField(choices=[(0, 'email'), (1, 'line'), (2, 'phone')], default=1, verbose_name='ユーザーロール')),
                ('status', models.BooleanField(default=False, verbose_name='オンライン')),
                ('is_joining', models.BooleanField(default=False, verbose_name='合流中')),
                ('point_used', models.IntegerField(default=0, validators=[django.core.validators.MinValueValidator(0)], verbose_name='利用ポイント')),
                ('call_times', models.IntegerField(default=0, verbose_name='合流利用回数')),
                ('point_half', models.IntegerField(default=3000, validators=[django.core.validators.MaxValueValidator(100000), django.core.validators.MinValueValidator(1000)], verbose_name='30分あたりのポイント')),
                ('is_applied', models.BooleanField(default=False, verbose_name='キャスト応募')),
                ('is_present', models.BooleanField(default=False, verbose_name='出勤')),
                ('presented_at', models.DateTimeField(null=True, verbose_name='出勤日時')),
                ('axes_exist', models.BooleanField(default=False, verbose_name='クレカ登録')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='作成日時')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新日時')),
                ('avatars', models.ManyToManyField(related_name='avatar', to='accounts.Media', verbose_name='アバタ')),
                ('cast_class', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='basics.castclass')),
                ('groups', models.ManyToManyField(blank=True, help_text='The groups this user belongs to. A user will get all permissions granted to each of their groups.', related_name='user_set', related_query_name='user', to='auth.Group', verbose_name='groups')),
                ('guest_level', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='basics.guestlevel')),
                ('setting', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='basics.setting')),
                ('user_permissions', models.ManyToManyField(blank=True, help_text='Specific permissions for this user.', related_name='user_set', related_query_name='user', to='auth.Permission', verbose_name='user permissions')),
            ],
            options={
                'verbose_name': 'ユーザー',
                'verbose_name_plural': 'ユーザー',
                'unique_together': {('social_type', 'social_id')},
            },
            managers=[
                ('objects', django.contrib.auth.models.UserManager()),
            ],
        ),
    ]
