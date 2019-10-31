from django.conf.urls import include, url

from .views import RedirectView, ReturnView

event_patterns = [
    url(r'^modirum/', include([
        url(r'^redirect/(?P<order>[^/]+)/(?P<hash>[^/]+)/(?P<payment>[^/]+)/$', RedirectView.as_view(),
            name='redirect'),
        url(r'^return/(?P<order>[^/]+)/(?P<hash>[^/]+)/(?P<payment>[^/]+)/$', ReturnView.as_view(), name='return'),
    ])),
]
