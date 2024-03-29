"""
APIs for Chat
"""
import json
from django.core.paginator import Paginator, EmptyPage
from django.db.models import Q, Count, F

# from django.shortcuts import render
from rest_framework import generics, mixins, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.serializers import Serializer
from rest_framework.views import APIView

from .models import Notice, Room, Message, AdminNotice
from calls.models import Invoice
from basics.models import Gift
from .serializers import AdminMessageSerializer, NoticeSerializer, RoomSerializer, AdminNoticeSerializer, MessageSerializer, FileListSerializer

from accounts.models import Member
from accounts.serializers.member import UserSerializer
from accounts.views.member import IsAdminPermission, IsSuperuserPermission

from .utils import send_super_message, send_super_room, send_message_to_user, send_room_to_users, send_notice_to_room

# def index(request):
#     return render(request, 'chat/index.html', {})


# def room(request, room_name):
#     return render(request, 'chat/room.html', {
#         'room_name': room_name
#     })


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def notices_list(request):
    """
    List all notices by user, or create a new notice.
    """

    if request.method == 'GET':
        notices = Notice.objects.filter(
            user=request.user,
            notice_type=request.GET.get('notice_type', 'foot')
        )
        paginator = Paginator(notices.order_by('-created_at'), 10)
        try:
            paginated_notices = paginator.page(request.GET.get('page', 1))
            return Response(
                data=NoticeSerializer(paginated_notices, many=True).data,
                status=status.HTTP_200_OK
            )
        except EmptyPage:
            return Response(
                data=[],
                status=status.HTTP_200_OK
            )

    elif request.method == 'POST':
        serializer = NoticeSerializer(data=request.data)
        if serializer.is_valid():
            new_notice = serializer.save()
            return Response(
                data=NoticeSerializer(new_notice).data,
                status=status.HTTP_201_CREATED
            )
        else:
            return Response(
                data=serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def room_list(request):
    """
    List all rooms by user.
    """

    if request.method == 'GET':
        mode = request.GET.get('mode', 'all')
        keyword = request.GET.get('keyword', '')
        page = int(request.GET.get('page', '1'))
        offset = int(request.GET.get('offset', '0'))
        page_size = 10
        start_index = offset + (page - 1) * page_size

        # initial queryset
        query_set = request.user.rooms

        # mode is group or all
        if mode == "group":
            query_set = query_set.filter(is_group=True)

        # get rooms
        rooms = Room.objects.filter(id__in=list(
            query_set.values_list('id', flat=True)))

        # nickname search
        if keyword != "":
            rooms = rooms.filter(users__nickname__icontains=keyword)

        # order by created at and pagination
        rooms = rooms.order_by(
            '-updated_at').all()[start_index:start_index + page_size]
        rooms = rooms.annotate(unread=Count('messages', filter=Q(
            messages__receiver=request.user) & Q(messages__is_read=False)))
        return Response(
            data=RoomSerializer(rooms, many=True).data,
            status=status.HTTP_200_OK
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def room_detail(request, room_id):
    """
    Retrieve a room.
    """

    try:
        room = Room.objects.get(pk=room_id)
        if request.user.role >= 0 and room.users.filter(
                id=request.user.id).count() == 0:
            return Response(status=status.HTTP_400_BAD_REQUEST)
    except Room.DoesNotExist:
        return Response(
            status=status.HTTP_404_NOT_FOUND
        )

    if request.method == 'GET':
        serializer = RoomSerializer(room)
        return Response(
            data=serializer.data,
            status=status.HTTP_200_OK
        )


@api_view(['GET', 'POST', 'PUT'])
@permission_classes([IsAuthenticated])
def message_list(request, room_id):
    """
    List all messages, or create messages by room and user.
    """

    try:
        room = Room.objects.get(pk=room_id, users__id=request.user.id)
    except Room.DoesNotExist:
        return Response(
            status=status.HTTP_404_NOT_FOUND
        )

    if request.method == 'GET':
        page = int(request.GET.get('page', '1'))
        offset = int(request.GET.get('offset', '0'))
        page_size = 10
        start_index = offset + (page - 1) * page_size
        messages = room.messages.filter(receiver=request.user).order_by(
            '-created_at').all()[start_index:start_index + page_size]
        return Response(
            data=MessageSerializer(messages, many=True).data,
            status=status.HTTP_200_OK
        )

    if request.method == 'POST':
        serializer = MessageSerializer(data=request.data)

        if serializer.is_valid():
            input_data = serializer.validated_data
            media_ids = input_data.get('media_ids', [])
            gift_id = input_data.get('gift_id', 0)

            # create self message
            self_message = Message.objects.create(
                content=input_data.get('content'),
                sender=request.user,
                receiver=request.user,
                room=room,
                is_read=True
            )
            self_message.medias.set(media_ids)
            if not room.is_group and room.room_type == "private":
                if gift_id > 0:
                    try:
                        gift = Gift.objects.get(pk=gift_id)

                        self_message.gift_id = gift_id
                        self_message.save()

                        # give and take gift point
                        Invoice.objects.create(
                            invoice_type="GIFT",
                            give_amount=gift.point,
                            giver=request.user,
                            gift=gift,
                            room=room)
                        request.user.point -= gift.point
                        request.user.point_used += gift.point
                        request.user.save()

                        for user in room.users.all():
                            if user.id != request.user.id:
                                Invoice.objects.create(
                                    invoice_type="GIFT", take_amount=gift.back, taker=user, gift=gift, room=room)
                                user.point += gift.back
                                user.save()
                    except BaseException:
                        pass

            # create others message
            for user in room.users.all():
                if user.id != request.user.id:
                    message = Message.objects.create(
                        content=input_data.get('content'),
                        sender=request.user,
                        receiver=user,
                        room=room,
                        is_read=False,
                        follower=self_message
                    )
                    message.medias.set(media_ids)
                    if gift_id > 0:
                        message.gift_id = gift_id
                        message.save()

                    send_message_to_user(message, user.id)

            room.last_sender = request.user
            if len(media_ids) > 0:
                room.last_message = "『画像』"
            elif gift_id > 0:
                room.last_message = "『ステッカー』"
            else:
                room.last_message = input_data.get('content')
            room.save()

            return Response(
                status=status.HTTP_200_OK
            )
        else:
            return Response(
                status=status.HTTP_400_BAD_REQUEST
            )

    if request.method == 'PUT':
        room.messages.filter(
            receiver=request.user).update(is_read=True)
        return Response(
            status=status.HTTP_200_OK
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def unread_count(request):
    """
    Get the number of unread messages for the user.
    """

    if request.method == 'GET':
        return Response(
            data=Message.objects.filter(
                receiver=request.user, is_read=False).count(),
            status=status.HTTP_200_OK
        )


class ChatroomView(mixins.ListModelMixin, generics.GenericAPIView):
    permission_classes = [IsAdminPermission]
    serializer_class = RoomSerializer
    queryset = Room.objects.all()

    def get_queryset(self):
        user_id = int(self.request.GET.get("user_id", "0"))
        if user_id > 0:
            return Member.objects.get(pk=user_id).rooms.order_by('-updated_at')
        else:
            return Room.objects.all().order_by('-updated_at')

    def get(self, request, *args, **kwargs):
        total = self.get_queryset().count()
        paginator = Paginator(self.get_queryset().order_by('-updated_at'), 10)
        page = int(request.GET.get("page", "1"))
        reviews = paginator.page(page)

        return Response({"total": total, "results": RoomSerializer(
            reviews, many=True).data}, status=status.HTTP_200_OK)


class AdminNoticeView(
        mixins.UpdateModelMixin,
        mixins.DestroyModelMixin,
        mixins.CreateModelMixin,
        mixins.ListModelMixin,
        generics.GenericAPIView):
    permission_classes = [IsAdminPermission]
    serializer_class = AdminNoticeSerializer
    queryset = AdminNotice.objects.all()

    def get(self, request, *args, **kwargs):
        page = int(request.GET.get('page', "1"))
        cur_request = request.query_params.get("query", "")

        # user type
        query_set = AdminNotice.objects

        # query
        if cur_request != "":
            try:
                query_obj = json.loads(cur_request)
            except BaseException:
                return Response({"total": 0, "results": []},
                                status=status.HTTP_200_OK)

            # location
            location_val = query_obj.get("location_id", 0)
            if location_val > 0:
                query_set = query_set.filter(location_id=location_val)

            # title
            title = query_obj.get("title", "")
            if title != "":
                query_set = query_set.filter(title__icontains=title)

        total = query_set.count()
        paginator = Paginator(query_set.order_by('-updated_at'), 10)
        notices = paginator.page(page)

        return Response({"total": total, "results": AdminNoticeSerializer(
            notices, many=True).data}, status=status.HTTP_200_OK)

    def post(self, request, *args, **kwargs):
        return self.create(request, *args, **kwargs)

    def put(self, request, *args, **kwargs):
        return self.update(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        return self.destroy(request, *args, **kwargs)


@api_view(['GET'])
@permission_classes([IsAdminPermission])
def get_user_count(request):
    cur_request = request.query_params.get("query", "")
    query_set = Member.objects.filter(
        is_active=True).filter(Q(role=0) | Q(role=1))

    if cur_request != "":
        try:
            query_obj = json.loads(cur_request)
        except BaseException:
            return Response([], status=status.HTTP_200_OK)

        if query_obj.get('location_id', 0) > 0:
            query_set = query_set.filter(
                location_id=query_obj.get('location_id', 0))

        user_type = query_obj.get('user_type', 0)
        if user_type == 1:
            query_set = query_set.filter(role=0)
        elif user_type == 2:
            query_set = query_set.filter(role=1)
        elif user_type == 3:
            query_set = query_set.filter(is_introducer=True)

        if len(query_obj.get('cast_class', [])) > 0:
            query_set = query_set.filter(
                cast_class_id__in=query_obj.get('cast_class', []))

    return Response(
        list(
            query_set.values_list(
                'id',
                flat=True)),
        status=status.HTTP_200_OK)


class MessageUserView(generics.GenericAPIView):
    permission_classes = [IsAdminPermission]
    serializer_class = UserSerializer

    def get(self, request):
        import json

        page = int(request.GET.get('page', "1"))
        size = int(request.GET.get('size', "10"))

        cur_request = request.query_params.get("query", "")
        query_set = Member.objects.filter(
            is_active=True).filter(Q(role=0) | Q(role=1))

        if cur_request != "":
            try:
                query_obj = json.loads(cur_request)
            except BaseException:
                return Response({"total": 0, "results": []},
                                status=status.HTTP_200_OK)

            if query_obj.get('location_id', 0) > 0:
                query_set = query_set.filter(
                    location_id=query_obj.get('location_id', 0))

            user_type = query_obj.get('user_type', 0)
            if user_type == 1:
                query_set = query_set.filter(role=0)
            elif user_type == 2:
                query_set = query_set.filter(role=1)
            elif user_type == 3:
                query_set = query_set.filter(is_introducer=True)

            if len(query_obj.get('cast_class', [])) > 0:
                query_set = query_set.filter(
                    cast_class_id__in=query_obj.get('cast_class', []))

        # sort order
        sort_field = request.GET.get("sortField", "")
        sort_order = request.GET.get("sortOrder", "")
        if sort_field != "null" and sort_field != "":
            if sort_field == "usertype":
                if sort_order == "ascend":
                    query_set = query_set.order_by("-is_introducer", "-role")
                else:
                    query_set = query_set.order_by("role", "is_introducer")
            else:
                if sort_order == "ascend":
                    query_set = query_set.order_by(sort_field)
                else:
                    query_set = query_set.order_by("-{}".format(sort_field))

        total = query_set.count()
        paginator = Paginator(query_set, size)
        users = paginator.page(page)

        return Response({"total": total, "results": UserSerializer(
            users, many=True).data}, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def upload_images(request):
    serializer = FileListSerializer(data=request.data)
    if serializer.is_valid():
        return_array = serializer.save()
        return Response(return_array, status=status.HTTP_200_OK)
    else:
        print(serializer.errors)
        return Response(status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsSuperuserPermission])
def send_bulk_messages(request):
    message_serializer = AdminMessageSerializer(data=request.data)
    if message_serializer.is_valid():
        input_data = message_serializer.validated_data
        receiver_ids = input_data.pop('receiver_ids')
        content = input_data.pop('content')
        media_ids = input_data.pop('media_ids')

        if len(receiver_ids) == 0:
            return Response(status=status.HTTP_406_NOT_ACCEPTABLE)

        sender = request.user

        for user_id in receiver_ids:
            send_super_message(sender.username, user_id, content, media_ids)

        return Response({"success": True}, status=status.HTTP_200_OK)
    else:
        return Response(status=status.HTTP_400_BAD_REQUEST)


class MessageView(generics.GenericAPIView):
    permission_classes = [IsAdminPermission]
    serializer_class = MessageSerializer

    def get(self, request):
        import json

        page = int(request.GET.get('page', "1"))
        size = int(request.GET.get('size', "10"))

        cur_request = request.query_params.get("query", "")
        query_set = Message.objects.filter(receiver_id=F('sender_id'))

        if cur_request != "":
            try:
                query_obj = json.loads(cur_request)
            except BaseException:
                return Response({"total": 0, "results": []},
                                status=status.HTTP_200_OK)

            content = query_obj.get('content', "")
            nickname = query_obj.get('nickname', "")

            if content != "":
                query_set = query_set.filter(content__icontains=content)

            if nickname != "":
                query_set = query_set.filter(
                    sender__nickname__icontains=nickname)

        # sort order
        sort_field = request.GET.get("sortField", "")
        sort_order = request.GET.get("sortOrder", "")
        if sort_field != "null" and sort_field != "":
            if sort_order == "ascend":
                query_set = query_set.order_by(sort_field)
            else:
                query_set = query_set.order_by("-{}".format(sort_field))
        else:
            query_set = query_set.order_by("-created_at")

        total = query_set.count()
        paginator = Paginator(query_set, size)
        messages = paginator.page(page)

        return Response({"total": total, "results": MessageSerializer(
            messages, many=True).data}, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = MessageSerializer(data=request.data)
        if serializer.is_valid():
            input_data = serializer.validated_data
            room_id = input_data.get('room_id', 0)
            sender_id = input_data.get('sender_id', 0)
            content = input_data.get('content', "")
            media_ids = []
            if 'media_ids' in input_data:
                media_ids = input_data.get("media_ids")

            is_read = input_data.get("is_read", False)
            if room_id > 0 and sender_id > 0:
                try:
                    Room.objects.get(pk=room_id)
                    self_message = send_super_room(
                        room_id, sender_id, content, media_ids, is_read)
                    return Response(
                        MessageSerializer(self_message).data,
                        status=status.HTTP_200_OK)
                except Room.DoesNotExist:
                    return Response(status=status.HTTP_406_NOT_ACCEPTABLE)

        return Response(status=status.HTTP_400_BAD_REQUEST)


@api_view(['DELETE'])
@permission_classes([IsSuperuserPermission])
def delete_message(request, id):
    try:
        message = Message.objects.get(pk=id)
        message.delete()
        return Response(status=status.HTTP_200_OK)
    except Message.DoesNotExist:
        return Response(status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsSuperuserPermission])
def get_unread_admin_messages(request):
    page = int(request.GET.get('page', "1"))
    size = int(request.GET.get('size', "10"))

    query_set = Message.objects
    superuser_ids = list(
        Member.objects.filter(
            is_superuser=True).values_list(
            'id',
            flat=True))
    query_set = query_set.filter(
        receiver_id__in=superuser_ids, is_read=False
    ).order_by('-created_at')

    total = query_set.count()
    paginator = Paginator(query_set, size)
    messages = paginator.page(page)

    return Response({"total": total, "results": MessageSerializer(
        messages, many=True).data}, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsSuperuserPermission])
def get_unread_admin_messages_count(request):
    query_set = Message.objects
    superuser_ids = list(
        Member.objects.filter(
            is_superuser=True).values_list(
            'id',
            flat=True))
    query_set = query_set.filter(
        receiver_id__in=superuser_ids, is_read=False
    ).order_by('-created_at')

    total = query_set.count()

    return Response({"total": total}, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsSuperuserPermission])
def get_all_rooms(request):
    rooms = Room.objects.filter(room_type="admin")
    return Response(
        RoomSerializer(
            rooms,
            many=True).data,
        status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsSuperuserPermission])
def change_message_state(request, id):
    Message.objects.filter(pk=id).update(is_read=True)
    return Response({"success": True}, status=status.HTTP_200_OK)


class RoomView(mixins.CreateModelMixin, generics.GenericAPIView):
    permission_classes = [IsAdminPermission]
    serializer_class = RoomSerializer

    def get(self, request):
        import json

        page = int(request.GET.get('page', "1"))
        size = int(request.GET.get('size', "10"))

        cur_request = request.query_params.get("query", "")
        query_set = Room.objects

        if cur_request != "":
            try:
                query_obj = json.loads(cur_request)
            except BaseException:
                return Response({"total": 0, "results": []},
                                status=status.HTTP_200_OK)

            roomname = query_obj.get('roomname', "")
            nickname = query_obj.get('nickname', "")
            roomtype = query_obj.get('roomtype', "")

            if roomname != "":
                query_set = query_set.filter(title__icontains=roomname)

            if nickname != "":
                query_set = query_set.filter(
                    users__nickname__icontains=nickname)

            if roomtype != "":
                query_set = query_set.filter(room_type=roomtype)

        # sort order
        sort_field = request.GET.get("sortField", "")
        sort_order = request.GET.get("sortOrder", "")
        if sort_field != "null" and sort_field != "":
            if sort_order == "ascend":
                query_set = query_set.order_by(sort_field)
            else:
                query_set = query_set.order_by("-{}".format(sort_field))
        else:
            query_set = query_set.order_by("-created_at")

        total = query_set.count()
        paginator = Paginator(query_set, size)
        rooms = paginator.page(page)

        return Response({"total": total, "results": RoomSerializer(
            rooms, many=True).data}, status=status.HTTP_200_OK)

    def post(self, request, *args, **kwargs):
        room_serializer = self.get_serializer(data=request.data)
        if room_serializer.is_valid():

            new_room = room_serializer.save()
            not_admin_users = list(
                new_room.users.filter(
                    role__gte=0).values_list(
                    "id",
                    flat=True))

            send_room_to_users(new_room, not_admin_users, "create")
            send_notice_to_room(new_room, new_room.last_message, False)
            return Response(RoomSerializer(new_room).data)
        else:
            print("room not valid")
            return Response(status=status.HTTP_400_BAD_REQUEST)


class RoomDetailView(mixins.RetrieveModelMixin, generics.GenericAPIView):
    permission_classes = [IsSuperuserPermission]
    serializer_class = RoomSerializer
    queryset = Room.objects.all()

    def get(self, request, *args, **kwargs):
        return self.retrieve(request, *args, **kwargs)

    def put(self, request, *args, **kwargs):
        old_room = self.get_object()
        old_user_ids = list(old_room.users.values_list('id', flat=True))

        serializer = self.get_serializer(old_room, data=request.data)
        if serializer.is_valid():
            new_room = serializer.save()
            new_user_ids = list(new_room.users.values_list('id', flat=True))

            # kicked out users
            kicked_user_ids = [
                x for x in old_user_ids if x not in new_user_ids]
            remaining_user_ids = [x for x in old_user_ids if x in new_user_ids]

            # send room update to users
            send_room_to_users(new_room, remaining_user_ids, "create")

            # send room delete
            send_room_to_users(old_room, kicked_user_ids, "delete")

            message = "残念ですが管理画面より{0}から却下されました。"
            real_message = ""

            if old_room.room_type != "private":
                real_message = message.format(
                    "チャットルーム「{0}」").format(old_room.title)

            for user_id in kicked_user_ids:
                no_errors = True
                if old_room.room_type == "private":
                    try:
                        roommate_ids = [
                            x for x in old_user_ids if x != user_id]
                        if len(roommate_ids) > 0:
                            partner = Member.objects.get(pk=roommate_ids[0])
                            real_message = message.format(
                                "{0}とのチャットルーム").format(partner.nickname)
                    except BaseException:
                        no_errors = False
                if no_errors:
                    send_super_message("system", user_id, real_message)

                cur_user = Member.objects.get(pk=user_id)
                cur_user.joins.filter(
                    order__room__id=new_room.id,
                    is_ended=False).update(
                    is_ended=True)

            # newly added users
            added_user_ids = [x for x in new_user_ids if x not in old_user_ids]
            send_room_to_users(new_room, added_user_ids, "create")

            return Response(RoomSerializer(new_room).data)
        else:
            return Response(status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsSuperuserPermission])
def add_member(request, pk):
    user_id = int(request.data.get('user_id', '0'))
    if pk > 0 and user_id > 0:
        room = Room.objects.get(pk=pk)
        room.users.add(Member.objects.get(pk=user_id))
        return Response(RoomSerializer(room).data, status=status.HTTP_200_OK)
    else:
        return Response(status=status.HTTP_400_BAD_REQUEST)


class RoomMessageView(APIView):
    permission_classes = [IsSuperuserPermission]

    def get(self, request, pk):
        room = Room.objects.get(pk=pk)

        page = int(request.GET.get('page', "1"))
        size = int(request.GET.get('size', "10"))

        query_set = room.messages.filter(
            receiver_id=F('sender_id')).order_by('-created_at')
        total = query_set.count()
        paginator = Paginator(query_set, size)
        messages = paginator.page(page)

        return Response({"total": total, "results": MessageSerializer(
            messages, many=True).data}, status=status.HTTP_200_OK)


@api_view(['DELETE'])
@permission_classes([IsSuperuserPermission])
def delete_member(request, pk, id):
    # print(pk, id)
    try:
        room = Room.objects.get(pk=pk)
        deleted_user = Member.objects.get(pk=id)
        room.users.remove(deleted_user)

        # send room delete
        send_room_to_users(room, [deleted_user.id], "delete")

        message = "残念ですが管理画面よりチャットルーム「{0}」から却下されました。\
                是非またオーダーにエントリー頂けますようお願いいたします!".format(room.title)
        send_super_message("system", deleted_user.id, message)

        # order setting
        order = room.orders.first()
        if order is not None:
            order.joins.filter(user=deleted_user).delete()
            order.person = order.person - 1
            order.save()
    except Exception as e:
        print(e)
        return Response(status=status.HTTP_400_BAD_REQUEST)

    return Response(status=status.HTTP_200_OK)
