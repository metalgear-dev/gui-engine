"""
Serializers for Member
"""

from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from rest_framework import serializers
from rest_framework_jwt.settings import api_settings

from rest_framework.pagination import PageNumberPagination
from drf_extra_fields.fields import Base64ImageField
from accounts.models import Media, Tweet
from datetime import datetime
from rest_framework.response import Response


def file_validator(file):
    max_file_size = 1024 * 1024 * 1  # 1MB

    if file.size > max_file_size:
        raise serializers.ValidationError(_('Max file size is {} and your file size is {}'.
                                            format(max_file_size, file.size)))


class InitialInfoRegisterSerializer(serializers.Serializer):
    media = serializers.FileField(max_length=1000000, allow_empty_file=False, use_url=False,
                                  validators=[file_validator], write_only=True)
    nickname = serializers.CharField()
    birthday = serializers.CharField()

    def update(self, instance, validated_data):
        # save media
        image = validated_data.pop('media')
        media_image = Media.objects.create(uri=image)

        # save user
        instance.nickname = validated_data['nickname']
        instance.birthday = validated_data['birthday']
        instance.avatars.add(media_image)
        instance.is_registered = True
        instance.save()

        return instance

class TweetSerializer(serializers.ModelSerializer):
    hearts = serializers.SerializerMethodField()
    class Meta:
        fields = ("id", "content", "image", "user", "hearts", "updated_at")

    def get_hearts(self, obj):
        return obj.tweet_likers.count()

class TweetPagination(PageNumberPagination):
    page_size = 10

    def get_paginated_response(self, data):        
        return Response({
            'results': data
        })