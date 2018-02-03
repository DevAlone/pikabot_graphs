import json
import logging
import traceback

import time

from bot.users_module import UsersModule
from pikabot_graphs import settings
from core.models import User, UserRatingEntry, UserCommentsCountEntry, PikabuUser, UserPostsCountEntry
from core.models import UserHotPostsCountEntry, UserPlusesCountEntry, UserMinusesCountEntry, UserSubscribersCountEntry

from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse, HttpResponseForbidden, JsonResponse
from django.views.decorators.csrf import csrf_exempt
# from django.db.models import Q

from rest_framework import generics, viewsets
from rest_framework.response import Response
from rest_framework.decorators import api_view
from core.serializers import UserSerializer, PikabuUserSerializer
from rest_framework.filters import OrderingFilter, SearchFilter
from django_filters.rest_framework import DjangoFilterBackend, FilterSet

import os

logger = logging.getLogger('pikabot_graphs/{}'.format('push_users_info'))
logger.setLevel(logging.INFO)

error_file_handler = logging.FileHandler('logs/{}.error.log'.format('push_users_info'))
error_file_handler.setLevel(logging.ERROR)

info_file_handler = logging.FileHandler('logs/{}.info.log'.format('push_users_info'))
info_file_handler.setLevel(logging.INFO)

logger.addHandler(info_file_handler)


def angular_debug_url(request):
    # DON'T USE IN PRODUCTION!!!

    allowed_routes = {
        '/',
        '/inline.bundle.js',
        '/polyfills.bundle.js',
        '/styles.bundle.js',
        '/vendor.bundle.js',
        '/main.bundle.js'
    }
    routes = {
        '/': '/index.html'
    }

    if request.path not in allowed_routes:
        request.path = '/'

    route = routes[request.path] if request.path in routes else request.path
    route = route[1:]

    file_path = os.path.join(settings.ANGULAR_ROOT, route)
    try:
        with open(file_path, 'r') as file:
            return HttpResponse(file.read())
    except FileNotFoundError:
        pass

    request.path = '/'
    return angular_debug_url(request)


def secret_page_for_l4rever(request):
    users = User.objects.all().order_by('-subscribers_count')
    return render(request, 'core/secret_page_for_l4rever.html', {
        'users': users,
    })


def ok(_):
    return HttpResponse("OK")


# API


# class UserFilter(FilterSet):
#     class Meta:
#         model = User
#         fields = {
#             'pikabu_id': ('exact', 'lte', 'gte'),
#             'username': ('exact', 'contains', 'icontains'),
#             'is_processed': ('exact', )
#         }


class UserViewSet(viewsets.ReadOnlyModelViewSet):
    model = User
    queryset = User.objects.all()
    serializer_class = UserSerializer
    filter_backends = (DjangoFilterBackend, OrderingFilter, SearchFilter)
    ordering_fields = (
        'rating',
        'username',
        'subscribers_count',
        'comments_count',
        'posts_count',
        'hot_posts_count',
        'pluses_count',
        'minuses_count',
        'last_update_timestamp',
        'updating_period',
        'pikabu_id',
        'approved',
        'signup_timestamp',
        'pk',
    )
    ordering = ('pk',)
    search_fields = ('username', 'info', 'approved', )
    # filter_class = UserFilter


@api_view(['GET'])
def get_user_graph(_, username, graph_name):

    user = get_object_or_404(User, username=username)
    graph_name = graph_name.lower()

    classes = {
        'rating': UserRatingEntry,
        'comments': UserCommentsCountEntry,
        'posts': UserPostsCountEntry,
        'hot_posts': UserHotPostsCountEntry,
        'pluses': UserPlusesCountEntry,
        'minuses': UserMinusesCountEntry,
        'subscribers': UserSubscribersCountEntry,
    }

    if graph_name not in classes:
        return HttpResponse(status=404)

    data = classes[graph_name].objects.filter(user=user).order_by('timestamp').all()

    data = [
        {
            'timestamp': item.timestamp,
            'value': item.value,
            # 'user_id',
        } for item in data
    ]

    return Response({
        'results': data
    })


class UserView(generics.RetrieveAPIView):
    lookup_field = 'username'
    queryset = User.objects.all()
    serializer_class = UserSerializer


class PikabuUserFilter(FilterSet):
    class Meta:
        model = PikabuUser
        fields = {
            'pikabu_id': ('exact', 'lte', 'gte'),
            'username': ('exact', 'contains', 'icontains'),
            'is_processed': ('exact', )
        }


class PikabuUserViewSet(viewsets.ReadOnlyModelViewSet):
    model = PikabuUser
    queryset = PikabuUser.objects.all()
    serializer_class = PikabuUserSerializer
    filter_backends = (DjangoFilterBackend, OrderingFilter)
    ordering_fields = ('pikabu_id', 'username')
    ordering = ('pikabu_id',)
    filter_class = PikabuUserFilter




@csrf_exempt
def push_users_info(request, session):
    global logger
    logger.info('{}: request started'.format(time.time()))

    if request.method == 'POST' and session in settings.ALLOWED_PUSH_USERS_SESSIONS:
        try:
            json_body = json.loads(request.body.decode())

            for json_user in json_body['data']:
                json_user = json_user['user']

                username = json_user['user_name'].strip().lower()

                logger.info('{}: getting or creating user'.format(time.time()))
                try:
                    user = User.objects.get(username=username)
                except User.DoesNotExist:
                    user = User()
                    user.username = username

                logger.info('{}: processing user'.format(time.time()))
                if json_user['avatar']:
                    user.avatar_url = json_user['avatar']
                else:
                    user.avatar_url = ""

                user.rating = int(float(json_user['rating']))
                user.comments_count = int(json_user['comments_count'])
                user.posts_count = int(json_user['stories_count'])
                user.hot_posts_count = int(json_user['stories_hot_count'])
                user.pluses_count = int(json_user['pluses_count'])
                user.minuses_count = int(json_user['minuses_count'])

                user.gender = str(json_user['gender'])
                user.approved = json_user['approved']
                user.awards = json_user['awards']
                user.communities = json_user['communities']
                user.signup_timestamp = int(json_user['signup_date'])
                user.pikabu_id = int(json_user['user_id'])

                try:
                    user.subscribers_count = int(json_user['subscribers_count'])
                except KeyError:
                    logger.warning("subscribers_count disappeared")
                try:
                    if type(json_user['is_rating_ban']) is bool:
                        user.is_rating_ban = json_user['is_rating_ban']
                    else:
                        user.is_rating_ban = json_user['is_rating_ban'].lower().strip() == 'true'
                except KeyError:
                    logger.warning("is_rating_ban disappeared")

                user.last_update_timestamp = int(time.time())

                logger.info('{}: saving user'.format(time.time()))
                user.save()

                logger.info('{}: getting pikabu user'.format(time.time()))
                pikabu_user = PikabuUser.objects.get(username=json_user['user_name'])
                pikabu_user.is_processed = True
                logger.info('{}: saving pikabu user'.format(time.time()))
                pikabu_user.save()

            return JsonResponse({
                'status': 'ok'
            })
        except BaseException as ex:
            logger.exception(ex)

            return JsonResponse({
                'status': 'error'
            })

    return HttpResponseForbidden("""
    <style>
    img { 
        width: 100%;
    }
    </style>
    <img src="http://karaul.ru/uploads/posts/2016-05/1462950596_ob005.jpg">
""")
