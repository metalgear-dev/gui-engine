import json
from django.db.models.aggregates import Count
import jwt
from datetime import timedelta
import requests

from django.core.paginator import Paginator
from django.conf import settings
from django.db.models import Q, query
from django.http import Http404

from rest_framework import status
from rest_framework import generics
from rest_framework import mixins
from rest_framework.decorators import permission_classes, api_view
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated, BasePermission

from accounts.serializers.member import *
from accounts.serializers.auth import MemberSerializer, MediaImageSerializer, DetailSerializer, TransferInfoSerializer
from accounts.models import Member, Tweet, FavoriteTweet, Detail, TransferInfo, Friendship
from accounts.utils import get_edge_time, send_present, send_user
from chat.models import Room, Message
from calls.models import Invoice
from calls.axes import create_axes_payment
from basics.serializers import ChoiceSerializer
from chat.utils import send_room_to_users, send_message_to_user


class IsSuperuserPermission(BasePermission):
    message = "Only superuser is allowed"

    def has_permission(self, request, view):
        return request.user.is_superuser


class IsCastPermission(BasePermission):
    message = "Only Active Cast is allowed"

    def has_permission(self, request, view):
        return request.user.role == 0 and request.user.is_active


class IsGuestPermission(BasePermission):
    message = "Only Active Guest is allowed"

    def has_permission(self, request, view):
        return request.user.role == 1 and request.user.is_active


class IsAdminPermission(BasePermission):
    message = "Only Admin is allowed"

    def has_permission(self, request, view):
        return request.user.role < 0


class InitialRegister(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        cur_user = request.user
        if cur_user.role != 0:
            return Response(status=status.HTTP_400_BAD_REQUEST)

        serializer = InitialInfoRegisterSerializer(cur_user, request.data)
        if not cur_user.is_registered and serializer.is_valid():
            # if Member.objects.exclude(id=cur_user.id).filter(nickname=request.data['nickname']).count() > 0:
            #     return Response(status=status.HTTP_409_CONFLICT)
            updated_user = serializer.save()
            return Response(
                MemberSerializer(updated_user).data,
                status.HTTP_200_OK)
        else:
            return Response(status=status.HTTP_400_BAD_REQUEST)


class TweetView(
        mixins.DestroyModelMixin,
        mixins.CreateModelMixin,
        mixins.ListModelMixin,
        mixins.UpdateModelMixin,
        generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = TweetSerializer
    pagination_class = TweetPagination

    def get_queryset(self):
        tweet_type = self.request.GET.get('tweet_type', "")
        tweet_queryset = Tweet.objects.annotate(heart=Count('tweet_likers'))

        if self.request.user.role == 1:
            return tweet_queryset.filter(category=0)
        else:
            if tweet_type == "cast":
                return tweet_queryset.filter(user__role=0)
            else:
                return tweet_queryset

    def get(self, request, *args, **kwargs):
        query_set = self.get_queryset()

        # sort order
        sort_field = request.GET.get("sortField", "")
        sort_order = request.GET.get("sortOrder", "")
        page = int(request.GET.get('page', "1"))
        size = int(request.GET.get('size', "10"))
        # print(sort_field, sort_order)
        if sort_field != "null" and sort_field != "":
            if sort_order == "ascend":
                query_set = query_set.order_by(sort_field)
            else:
                query_set = query_set.order_by("-{}".format(sort_field))
        else:
            query_set = query_set.order_by("-created_at")

        total = query_set.count()
        paginator = Paginator(query_set, size)
        tweets = paginator.page(page)

        return Response({"total": total, "results": TweetSerializer(
            tweets, many=True).data}, status=status.HTTP_200_OK)

    def post(self, request, *args, **kwargs):
        return self.create(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        return self.destroy(request, *args, **kwargs)

    def put(self, request, *args, **kwargs):
        return self.update(request, *args, **kwargs)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def toggle_tweet(request):
    cur_user = request.user
    try:
        target_id = request.data['id']
        cur_tweet = Tweet.objects.get(pk=target_id)
        if FavoriteTweet.objects.filter(
                liker=cur_user,
                tweet=cur_tweet).count() > 0:
            FavoriteTweet.objects.filter(
                liker=cur_user, tweet=cur_tweet).delete()
        else:
            FavoriteTweet.objects.create(liker=cur_user, tweet=cur_tweet)
        likers_id = cur_tweet.tweet_likers.all().order_by(
            '-created_at').values_list('liker')
        like_users = MainInfoSerializer(Member.objects.filter(
            id__in=likers_id, is_registered=True), many=True)
        return Response(like_users.data)
    except Exception as e:
        return Response(status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAdminPermission])
def count_tweet(request):
    return Response(Tweet.objects.count(), status=status.HTTP_200_OK)


class AvatarView(mixins.UpdateModelMixin, generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = AvatarSerializer

    def post(self, request, *args, **kwargs):
        avatar_serializer = self.get_serializer(data=request.data)
        if avatar_serializer.is_valid():
            new_avatar = avatar_serializer.save()
            user = request.user
            user.avatars.add(new_avatar)
            return Response(
                MediaImageSerializer(
                    user.avatars,
                    many=True).data,
                status=status.HTTP_200_OK)
        else:
            return Response(status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, pk, *args, **kwargs):
        avatar_serializer = self.get_serializer(
            instance=Media.objects.get(pk=pk), data=request.data)
        if avatar_serializer.is_valid():
            new_avatar = avatar_serializer.save()
            user = request.user
            return Response(
                MediaImageSerializer(
                    user.avatars,
                    many=True).data,
                status=status.HTTP_200_OK)
        else:
            return Response(status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk, *args, **kwargs):
        user = request.user
        user.avatars.remove(Media.objects.get(pk=pk))
        Media.objects.get(pk=pk).delete()
        return Response(
            MediaImageSerializer(
                user.avatars,
                many=True).data,
            status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def change_avatar_order(request):
    serializer = AvatarChangerSerializer(data=request.data)
    if serializer.is_valid():
        uris_data = serializer.validated_data
        cur_user = request.user
        cur_user.avatars.clear()
        for uri_item in uris_data['uris']:
            media_obj = Media.objects.create(uri=uri_item)
            cur_user.avatars.add(media_obj)
        return Response(
            MediaImageSerializer(
                cur_user.avatars,
                many=True).data,
            status=status.HTTP_200_OK)
    else:
        return Response(status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def change_line(request):
    if 'code' in request.data.keys():
        line_code = request.data.get('code')

        url = "https://api.line.me/oauth2/v2.1/token"

        payload = 'grant_type=authorization_code' + \
            '&code=' + line_code + \
            '&redirect_uri=' + settings.CLIENT_URL + '/main/mypage/help/signin-method' + \
            '&client_id=' + settings.LINE_CLIENT_ID + \
            '&client_secret=' + settings.LINE_CLIENT_SECRET

        headers = {
            'Content-Type': 'application/x-www-form-urlencoded'
        }

        response = requests.request(
            "POST", url, headers=headers, data=payload)

        id_token = json.loads(
            response.text.encode('utf8')).get('id_token', '')

        try:
            decoded_payload = jwt.decode(id_token, None, None)
            line_id = decoded_payload['sub']

            cur_user = request.user

            if Member.objects.exclude(
                    pk=cur_user.id).filter(
                    social_id=line_id).count() > 0:
                return Response(status=status.HTTP_400_BAD_REQUEST)
            else:
                cur_user.social_id = line_id
                cur_user.save()
                return Response(status=status.HTTP_200_OK)

        except jwt.exceptions.InvalidSignatureError:
            return Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    else:
        return Response(status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def change_password(request):
    serializer = PasswordChange(data=request.data)
    if serializer.is_valid():
        input_data = serializer.validated_data
        old_pwd = input_data.get('old', "")
        new_pwd = input_data.get('new', "")
        confirm_pwd = input_data.get('confirm', "")
        user = request.user
        if old_pwd != "" or new_pwd != confirm_pwd:
            if not user.check_password(old_pwd):
                return Response(status=status.HTTP_400_BAD_REQUEST)
        user.set_password(new_pwd)
        user.save()
        return Response(status=status.HTTP_200_OK)
    else:
        return Response(status=status.HTTP_400_BAD_REQUEST)


class DetailView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = DetailSerializer(data=request.data, partial=True)
        if serializer.is_valid():
            detail_obj = serializer.save()
            user = request.user
            user.detail = detail_obj
            user.save()
            return Response(
                DetailSerializer(detail_obj).data,
                status.HTTP_200_OK)
        else:
            return Response(status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, pk):
        detail_obj = Detail.objects.get(pk=pk)
        serializer = DetailSerializer(
            detail_obj, data=request.data, partial=True)
        if serializer.is_valid():
            # print(serializer.validated_data)
            detail_obj = serializer.save()
            if Member.objects.filter(detail_id=detail_obj.id).count() > 0:
                user = Member.objects.filter(detail_id=detail_obj.id).first()
                send_user(user)
            # user = request.user
            # user.detail = detail_obj
            # user.save()
            return Response(
                DetailSerializer(detail_obj).data,
                status.HTTP_200_OK)
        else:
            return Response(status=status.HTTP_400_BAD_REQUEST)


class ProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ProfileSerializer(
            request.user, data=request.data, partial=True)
        user = request.user
        if serializer.is_valid():
            new_nickname = request.data.get('nickname', "")
            # if Member.objects.exclude(id=user.id).filter(nickname=new_nickname).count() > 0:
            #     return Response(status=status.HTTP_409_CONFLICT)
            updated_user = serializer.save()
            return Response(
                MemberSerializer(updated_user).data,
                status=status.HTTP_200_OK)
        else:
            print(serializer.errors)
            return Response(status=status.HTTP_400_BAD_REQUEST)


class AdminView(
        mixins.DestroyModelMixin,
        mixins.ListModelMixin,
        mixins.CreateModelMixin,
        mixins.UpdateModelMixin,
        generics.GenericAPIView):
    permission_classes = [IsSuperuserPermission]
    serializer_class = AdminSerializer
    pagination_class = AdminPagination

    def get_queryset(self):
        return Member.objects.filter(role__lt=0, is_superuser=False)

    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        return self.create(request, *args, **kwargs)

    def put(self, request, *args, **kwargs):
        return self.update(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        user = self.get_object()
        user.username = "user_{}".format(user.id)
        user.save()
        return self.destroy(request, *args, **kwargs)


class MemberView(APIView):
    permission_classes = [IsAdminPermission]

    def get(self, request):
        is_all = int(request.GET.get("is_all", "0"))
        is_cast = int(request.GET.get("is_cast", "0"))
        is_admin = int(request.GET.get("is_admin", "0"))
        is_super = int(request.GET.get("is_super", "0"))
        is_guest = int(request.GET.get("is_guest", "0"))

        if is_all > 0:
            members = Member.objects.filter(
                Q(is_registered=True, is_active=True, role__gte=0) | Q(role__lt=0))
        elif is_super > 0:
            members = Member.objects.filter(is_superuser=True)
        elif is_admin > 0:
            members = Member.objects.filter(role__lt=0)
        elif is_cast > 0:
            members = Member.objects.filter(is_registered=True, role=0)
        elif is_guest > 0:
            members = Member.objects.filter(role=1, is_active=True)
        else:
            members = Member.objects.filter(
                role__gte=0, is_registered=True, is_active=True)
        return Response(MemberSerializer(members, many=True).data)


class CastView(APIView):
    permission_classes = [IsAdminPermission]

    def get(self, request):
        page = int(request.GET.get('page', "1"))
        size = int(request.GET.get('size', "10"))
        is_present = int(request.GET.get("is_present", "0"))

        if is_present > 0:
            query_set = Member.objects.filter(
                is_registered=True, role=0, is_present=True)
        else:
            query_set = Member.objects.filter(is_registered=True, role=0)

        total = query_set.count()
        paginator = Paginator(query_set.order_by('id'), size)
        members = paginator.page(page)

        return Response({"total": total, "results": MemberSerializer(
            members, many=True).data}, status=status.HTTP_200_OK)


class UserView(
        mixins.ListModelMixin,
        mixins.CreateModelMixin,
        generics.GenericAPIView):
    permission_classes = [IsAdminPermission]
    serializer_class = UserSerializer
    queryset = Member.objects.all()

    def get(self, request, *args, **kwargs):
        page = int(request.GET.get('page', "1"))
        cur_request = request.query_params.get("query", "")
        user_type = request.GET.get('user_type', 'guest')
        is_introducer = request.GET.get('is_introducer', 'false')

        # user type
        if user_type == 'guest':
            if is_introducer == 'true':
                query_set = Member.objects.filter(is_introducer=True)
            else:
                query_set = Member.objects.filter(role=1)
        elif user_type == 'cast':
            query_set = Member.objects.filter(Q(role=0) | Q(role=10))
        else:
            query_set = Member.objects

        # query
        if cur_request != "":
            try:
                query_obj = json.loads(cur_request)
            except BaseException:
                return Response({"total": 0, "results": []},
                                status=status.HTTP_200_OK)

            if user_type == "cast":
                # ids array
                ids_array = query_obj.get('ids_array', [])

                if len(ids_array) > 0:
                    query_set = query_set.filter(id__in=ids_array)

                # location
                location_val = query_obj.get("location", 0)
                if location_val > 0:
                    query_set = query_set.filter(location_id=location_val)

                # cast level
                cast_class = query_obj.get("cast_class", 0)
                if cast_class > 0:
                    query_set = query_set.filter(cast_class_id=cast_class)

                # phone_number
                phone_number = query_obj.get("phone_number", "")
                if phone_number != "":
                    query_set = query_set.filter(
                        phone_number__icontains=phone_number)

                # is_applied
                is_applied = query_obj.get("is_applied", -1)
                if is_applied > -1:
                    if is_applied == 0:
                        query_set = query_set.filter(role=0)
                    else:
                        query_set = query_set.filter(role=10, is_applied=True)

                # register status
                reg_status = query_obj.get("reg_status", -1)
                if reg_status > -1:
                    if reg_status == 0:
                        query_set = query_set.filter(is_registered=False)
                    else:
                        query_set = query_set.filter(is_registered=True)

            if user_type == "guest":

                # guest level
                guest_level = query_obj.get("guest_level", 0)
                if guest_level > 0:
                    query_set = query_set.filter(guest_level_id=guest_level)

                # card register status
                card_register_status = query_obj.get("card_register", -1)
                if card_register_status == 1:
                    query_set = query_set.filter(axes_exist=True)
                if card_register_status == 0:
                    query_set = query_set.filter(axes_exist=False)

            # user_id
            user_id = query_obj.get("user_id", 0)
            if user_id and user_id > 0:
                query_set = query_set.filter(pk=user_id)

            # nickname
            nickname = query_obj.get("nickname", "")
            if nickname != "":
                query_set = query_set.filter(nickname__icontains=nickname)

            # username
            username = query_obj.get("username", "")
            query_set = query_set.filter(username__icontains=username)

            # introducer id
            introducer_id = query_obj.get("introducer_id", 0)
            if introducer_id and introducer_id > 0:
                query_set = query_set.filter(introducer_id=introducer_id)

        total = query_set.count()

        # sort order
        sort_field = request.GET.get("sortField", "")
        sort_order = request.GET.get("sortOrder", "")
        print(sort_field, sort_order)
        if sort_field != "null" and sort_field != "":
            if sort_order == "ascend":
                query_set = query_set.order_by(sort_field)
            else:
                query_set = query_set.order_by("-{}".format(sort_field))
        else:
            query_set = query_set.order_by("-created_at")

        paginator = Paginator(query_set, 10)
        members = paginator.page(page)

        return Response({"total": total, "results": UserSerializer(
            members, many=True).data}, status=status.HTTP_200_OK)

    def post(self, request, *args, **kwargs):
        return self.create(request, *args, **kwargs)


class UserDetailView(
        mixins.RetrieveModelMixin,
        mixins.DestroyModelMixin,
        mixins.UpdateModelMixin,
        generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = UserSerializer
    queryset = Member.objects.all()

    def get(self, request, *args, **kwargs):
        return self.retrieve(request, *args, **kwargs)

    def put(self, request, *args, **kwargs):
        instance = self.get_object()
        user_serializer = self.get_serializer(instance, data=request.data)
        if user_serializer.is_valid():
            new_user = user_serializer.save()
            send_user(new_user)
            return Response(UserSerializer(new_user).data)
        else:
            return Response(status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, *args, **kwargs):
        user = self.get_object()
        user.username = "user_{}".format(user.id)
        user.save()
        return self.destroy(request, *args, **kwargs)


class MemberDetailView(APIView):
    def get_object(self, pk):
        try:
            return Member.objects.get(pk=pk)
        except Member.DoesNotExist:
            raise Http404

    def get(self, request, pk):
        member = self.get_object(pk)
        serializer = MemberSerializer(member)
        return Response(serializer.data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_fresh_casts(request):
    from dateutil.relativedelta import relativedelta
    from datetime import datetime, timedelta

    today = timezone.now()
    three_months_ago = today - timedelta(days=90)

    casts = Member.objects.filter(
        role=0,
        started_at__gt=three_months_ago,
        is_active=True)
    return Response(
        GeneralInfoSerializer(
            casts,
            many=True).data,
        status=status.HTTP_200_OK)


@api_view(["GET"])
@permission_classes([IsGuestPermission])
def get_present_casts(request):
    casts = Member.objects.filter(role=0, is_present=True, is_active=True)
    return Response(
        GeneralInfoSerializer(
            casts,
            many=True).data,
        status=status.HTTP_200_OK)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def search_casts(request):
    serializer = CastFilterSerializer(data=request.GET, partial=True)
    if serializer.is_valid():
        input_data = serializer.validated_data
        queryset = Member.objects.filter(
            role=0, is_active=True, is_registered=True)
        page = input_data.get('page', 1)
        size = 10

        # location = input_data.get('location', 0)
        # if location > 0:
        #     queryset = queryset.filter()

        cast_class = input_data.get('cast_class', 0)
        if cast_class > 0:
            queryset = queryset.filter(cast_class__id=cast_class)

        nickname = input_data.get('nickname', "")
        if nickname != "":
            queryset = queryset.filter(nickname__icontains=nickname)

        # is new
        is_new = input_data.get('is_new', False)
        if is_new:
            today = timezone.now()
            three_months_ago = today - timedelta(days=90)
            queryset = queryset.filter(started_at__gt=three_months_ago)

        # point min and max
        point_min = input_data.get('point_min', 0)
        queryset = queryset.filter(point_half__gte=point_min)

        point_max = input_data.get('point_max', 30000)
        queryset = queryset.filter(point_half__lte=point_max)

        # choices
        choices = input_data.get('choices', [])
        for choice_item in choices:
            queryset = queryset.filter(cast_status__id=choice_item)

        start_index = (page - 1) * size

        return Response(
            GeneralInfoSerializer(
                queryset.order_by("-started_at")
                .all()[(start_index):(start_index + size)],
                many=True
            ).data,
            status=status.HTTP_200_OK)
    else:
        return Response(status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def search_guests(request):
    serializer = GuestFilterSerializer(data=request.GET, partial=True)
    if serializer.is_valid():
        input_data = serializer.validated_data
        queryset = Member.objects.filter(
            role=1, is_active=True, is_registered=True)
        page = input_data.get('page', 1)
        size = 10
        start_index = (page - 1) * size

        # age min and max
        year_now = timezone.now().year
        age_min = input_data.get('age_min', 20)
        age_max = input_data.get('age_max', 50)
        year_min = year_now - age_max
        year_max = year_now - age_min + 1

        from_date = datetime(year_min, 1, 1, 0, 0, 0)
        to_date = datetime(year_max, 1, 1, 0, 0, 0)
        queryset = queryset.filter(
            birthday__gte=from_date, birthday__lt=to_date)

        # nickname
        nickname = input_data.get('nickname', "")
        if nickname != "":
            queryset = queryset.filter(nickname__icontains=nickname)

        # salary
        salary = input_data.get('salary', 0)
        if salary > 0:
            queryset = queryset.filter(detail__annual=salary)

        # favorite
        favorite = input_data.get('favorite', "")
        if favorite != "":
            queryset = queryset.filter(favorite__icontains=favorite)

        return Response(
            GeneralInfoSerializer(
                queryset.order_by("-started_at")
                .all()[(start_index):(start_index + size)],
                many=True
            ).data,
            status=status.HTTP_200_OK)
    else:
        return Response(status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def edit_choice(request):
    choice_serializer = ChoiceIdSerializer(data=request.data)
    if choice_serializer.is_valid():
        user = request.user
        choice_data = choice_serializer.validated_data
        user.cast_status.clear()
        user.cast_status.set(choice_data.get('choice'))
        user.save()
        return Response(
            ChoiceSerializer(
                user.cast_status,
                many=True).data,
            status=status.HTTP_200_OK)
    else:
        return Response(status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET"])
@permission_classes([IsCastPermission])
def apply_transfer(request):
    import math
    cur_user = request.user
    amount = request.user.point - 440 - math.ceil(request.user.point / 50)
    if amount < 0:
        return Response(status=status.HTTP_400_BAD_REQUEST)
    else:
        TransferApplication.objects.create(
            location=cur_user.location,
            user=cur_user,
            amount=amount,
            point=request.user.point,
            apply_type=1,
            currency_type='jpy'
        )
        return Response(status=status.HTTP_200_OK)


class TransferView(generics.GenericAPIView):
    permission_classes = [IsSuperuserPermission]
    serializer_class = TransferSerializer

    def get(self, request):
        import json
        from dateutil.parser import parse

        page = int(request.GET.get('page', "1"))
        cur_request = request.query_params.get("query", "")
        query_set = TransferApplication.objects

        if cur_request != "":
            try:
                query_obj = json.loads(cur_request)
            except BaseException:
                return Response({"total": 0, "results": []},
                                status=status.HTTP_200_OK)

            # status
            status_val = query_obj.get("status", -1)
            if status_val > -1:
                query_set = query_set.filter(status=status_val)

            # user category
            user_cat = query_obj.get("user_cat", -1)
            if user_cat > -1:
                if user_cat == 1:
                    query_set = query_set.filter(
                        user__introducer__isnull=False)
                else:
                    query_set = query_set.filter(user__introducer__isnull=True)

            # location
            location_id = query_obj.get("location", 0)
            if location_id > 0:
                query_set = query_set.filter(location_id=location_id)

            # nickname
            nickname = query_obj.get("nickname", "")
            if nickname != "":
                query_set = query_set.filter(
                    user__nickname__icontains=nickname)

            # transfer category
            transfer_cat = query_obj.get("transfer_cat", -1)
            if transfer_cat > -1:
                query_set = query_set.filter(apply_type=transfer_cat)

            # transfer from
            date_from = query_obj.get("from", "")
            if date_from != "":
                query_set = query_set.filter(
                    created_at__gte=get_edge_time(date_from, "from"))

            # transfer to
            date_to = query_obj.get("to", "")
            if date_to != "":
                query_set = query_set.filter(
                    created_at__lt=get_edge_time(date_to, "to"))

        total = query_set.count()

        # sort order
        sort_field = request.GET.get("sortField", "")
        sort_order = request.GET.get("sortOrder", "")
        print(sort_field, sort_order)
        if sort_field != "null" and sort_field != "":
            if sort_order == "ascend":
                query_set = query_set.order_by(sort_field)
            else:
                query_set = query_set.order_by("-{}".format(sort_field))
        else:
            query_set = query_set.order_by("-created_at")

        paginator = Paginator(query_set, 10)
        transfers = paginator.page(page)

        return Response({"total": total, "results": TransferSerializer(
            transfers, many=True).data}, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsSuperuserPermission])
def count_transfer(request):
    status_array = []

    # present casts
    query_set = TransferApplication.objects.filter(status=0)
    orders_count = query_set.count()
    ids_array = list(query_set.values_list('id', flat=True).distinct())

    status_array.append({
        "title": "Transfer not processed",
        "count": orders_count,
        "ids_array": ids_array,
        "value": 0
    })

    # present casts
    query_set = TransferApplication.objects.filter(apply_type=1)
    orders_count = query_set.count()
    ids_array = list(query_set.values_list('id', flat=True).distinct())

    status_array.append({
        "title": "Immediate transfer application",
        "count": orders_count,
        "ids_array": ids_array,
        "value": 0
    })

    return Response(status_array)


class TransferInfoView(
        mixins.UpdateModelMixin,
        mixins.CreateModelMixin,
        generics.GenericAPIView):
    permission_classes = (IsCastPermission | IsSuperuserPermission, )
    serializer_class = TransferInfoSerializer
    queryset = TransferInfo.objects.all()

    def post(self, request, *args, **kwargs):
        return self.create(request, *args, **kwargs)

    def put(self, request, *args, **kwargs):
        return self.update(request, *args, **kwargs)


@api_view(["GET"])
@permission_classes([IsSuperuserPermission])
def proceed_transfer(request, id):
    cur_transfer = TransferApplication.objects.get(pk=id)
    cur_transfer.status = 1
    cur_transfer.save()

    # cast point update
    # print(cur_transfer.user.point)
    cur_transfer.user.point = cur_transfer.user.point - cur_transfer.point
    # print(cur_transfer.user.point)
    cur_transfer.user.save()
    send_user(cur_transfer.user)

    return Response({"success": True}, status=status.HTTP_200_OK)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def like_person(request, id):
    cur_user = request.user
    target_user = Member.objects.get(pk=id)
    if Friendship.objects.filter(
            follower=cur_user,
            favorite=target_user).count() == 0:
        Friendship.objects.create(follower=cur_user, favorite=target_user)

    # search room first
    old_room_exist = Room.objects.filter(
        room_type="private").filter(
        users__id=cur_user.id).filter(
            users__id=target_user.id).count()

    if old_room_exist == 0:

        # create room
        new_room = Room.objects.create(
            last_message="♥ いいね", room_type="private")
        new_room.users.set([cur_user.id, target_user.id])

        # send room
        send_room_to_users(new_room, [target_user.id, cur_user.id], "create")

        # send message
        cur_message = Message.objects.create(
            room=new_room,
            sender=cur_user,
            receiver=cur_user,
            is_like=True,
            is_read=True)
        send_message_to_user(cur_message, cur_user.id)

        target_message = Message.objects.create(
            room=new_room,
            sender=cur_user,
            receiver=target_user,
            is_like=True,
            is_read=False,
            follower=cur_message)
        send_message_to_user(target_message, target_user.id)
    else:
        new_room = Room.objects.filter(
            room_type="private").filter(
            users__id=cur_user.id).filter(
            users__id=target_user.id).get()

    return Response(new_room.id, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsSuperuserPermission])
def remove_thumbnail(request):
    user_id = request.GET.get("user_id", 0)
    thumbnail_id = request.GET.get("thumbnail_id", 0)
    if user_id == 0 or thumbnail_id == 0:
        return Response(status=status.HTTP_400_BAD_REQUEST)
    else:
        cur_user = Member.objects.get(pk=user_id)
        cur_user.avatars.remove(Media.objects.get(pk=thumbnail_id))
        Media.objects.get(pk=thumbnail_id).delete()
        return Response({"success": True}, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsSuperuserPermission])
def add_thumbnails(request):
    serializer = MediaListSerializer(data=request.data)
    if serializer.is_valid():
        return_array = serializer.save()
        return Response(MediaImageSerializer(return_array, many=True).data)
    else:
        return Response(status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsSuperuserPermission])
def set_choices(request):
    choice_serializer = ChoiceIdSerializer(data=request.data)
    if choice_serializer.is_valid():
        input_data = choice_serializer.validated_data
        user_id = input_data.get("user_id", 0)
        if user_id > 0:
            user = Member.objects.get(pk=user_id)
            user.cast_status.clear()
            user.cast_status.set(input_data.get('choice'))
            user.save()
            return Response(
                ChoiceSerializer(
                    user.cast_status,
                    many=True).data,
                status=status.HTTP_200_OK)
    return Response(status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAdminPermission])
def toggle_active(request, id):
    cur_user = Member.objects.get(pk=id)
    cur_user.is_active = not cur_user.is_active
    cur_user.save()
    return Response(status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAdminPermission])
def to_cast(request, id):
    cur_user = Member.objects.get(pk=id)
    cur_user.role = 0
    cur_user.save()
    return Response(status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAdminPermission])
def get_user_statistics(request):
    status_array = []
    status_title = [
        'Present Casts', 'Interview Request',
        'Temperary Registered Cast'
    ]

    # present casts
    query_set = Member.objects.filter(is_present=True)
    orders_count = query_set.count()
    ids_array = list(query_set.values_list('id', flat=True).distinct())

    status_array.append({
        "title": "Present Casts",
        "count": orders_count,
        "ids_array": ids_array,
        "value": 0
    })

    # interview request
    query_set = Member.objects.filter(is_applied=True, role=10)
    orders_count = query_set.count()
    ids_array = list(query_set.values_list('id', flat=True).distinct())

    status_array.append({
        "title": "Interview Request",
        "count": orders_count,
        "ids_array": ids_array,
        "value": 0
    })

    # interview request
    query_set = Member.objects.filter(is_registered=False, role=0)
    orders_count = query_set.count()
    ids_array = list(query_set.values_list('id', flat=True).distinct())

    status_array.append({
        "title": "Temperary Registered Cast",
        "count": orders_count,
        "ids_array": ids_array,
        "value": 0
    })

    return Response(status_array)


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def member_apply(request, member_id):
    """
    Apply to cast.
    """

    if member_id != request.user.id:
        return Response(
            status=status.HTTP_403_FORBIDDEN
        )

    try:
        member = Member.objects.get(pk=member_id)
    except Member.DoesNotExist:
        return Response(
            status=status.HTTP_404_NOT_FOUND
        )

    if request.method == 'PUT':
        member.is_applied = True
        member.save()
        return Response(
            status=status.HTTP_200_OK
        )


@api_view(['GET'])
@permission_classes([IsCastPermission])
def toggle_present(request):
    cur_user = request.user
    cur_user.is_present = not cur_user.is_present
    if cur_user.is_present:
        cur_user.presented_at = timezone.now() + timedelta(days=1)
    else:
        cur_user.presented_at = None
    cur_user.save()

    # notify to guests
    guest_ids = list(
        Member.objects.filter(
            role=1,
            is_active=True).values_list(
            'id',
            flat=True))
    if cur_user.is_present:
        send_present(cur_user, "add", guest_ids)
    else:
        send_present(cur_user, "remove", guest_ids)

    return Response(MemberSerializer(cur_user).data)


@api_view(['POST'])
@permission_classes([IsGuestPermission])
def buy_point(request):
    point = int(request.data.get('points', "0"))
    user = request.user
    if point > 0:

        # create axes payment
        if not create_axes_payment(request.user, point):
            return Response(status=status.HTTP_406_NOT_ACCEPTABLE)
        else:
            user.point += point
            user.save()

            # create invoice
            Invoice.objects.create(
                taker=request.user,
                take_amount=point,
                invoice_type="BUY")

            return Response(MemberSerializer(user).data)
    else:
        return Response(status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsGuestPermission])
def export_pdf(request):
    from .pdf.export import export_pdf

    pdf_info = request.GET.get("info")
    query_obj = json.loads(pdf_info)
    # print(query_obj)

    seed = query_obj.get("seed", "")
    date = query_obj.get("date", "")
    name_array = query_obj.get("names", [])
    number = query_obj.get("number", 1)
    no = query_obj.get("no", 100)

    try:
        point = Invoice.objects.get(pk=no).take_amount
    except Invoice.DoesNotExist:
        return Response(status=status.HTTP_400_BAD_REQUEST)

    filename = export_pdf(
        seed,
        date,
        name_array,
        number,
        no,
        point,
        request.user.id)

    return Response(filename)


@api_view(['GET'])
@permission_classes([IsAdminPermission])
def update_admin_profile(request):
    nickname = request.GET.get('nickname', '')
    password = request.GET.get('password', '')
    old_password = request.GET.get('old_password', '')
    username = request.GET.get('username', '')
    point = int(request.GET.get('point', 0))
    admin = request.user

    if old_password == "":
        return Response(status=status.HTTP_406_NOT_ACCEPTABLE)
    else:
        if not admin.check_password(old_password):
            return Response(status=status.HTTP_406_NOT_ACCEPTABLE)

    if password != "":
        admin.set_password(password)

    if nickname.strip() != "" and username.strip() != "" and point >= 0:
        new_nickname = nickname.strip()
        new_username = username.strip()

        if Member.all_objects.exclude(
                id=admin.id).filter(
                username=new_username).count() > 0:
            return Response(status=status.HTTP_409_CONFLICT)

        admin.nickname = new_nickname
        admin.username = new_username
        admin.point = point
        admin.save()
        return Response(
            MemberSerializer(admin).data,
            status=status.HTTP_200_OK)
    else:
        return Response(status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsSuperuserPermission])
def check_user_exist(request):
    user_id = int(request.query_params.get('id'))
    user_email = request.query_params.get('email')

    if Member.objects.exclude(id=user_id).filter(email=user_email).count() > 0:
        return Response({"success": False, "deleted": False})
    else:
        if Member.all_objects.exclude(
                id=user_id).filter(
                email=user_email).count() > 0:
            return Response({"success": False, "deleted": False})

    return Response({"success": True})
