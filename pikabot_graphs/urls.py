import core.views
import communities_app.views

from django.conf.urls import url, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    url(r'^secret_page_for_lactarius/$', communities_app.views.secret_page_for_lactarius,
        name='secret_page_for_lactarius'),
]


if settings.DEBUG:
    urlpatterns += [
        *static(settings.ANGULAR_STATIC_URL,
                document_root=settings.ANGULAR_STATIC_ROOT),
        url(r'^', core.views.angular_debug_url),
    ]
