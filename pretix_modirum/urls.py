from django.urls import include, path

from .views import RedirectView, ReturnView

event_patterns = [
    path('modirum/', include([
        path('redirect/<str:order>/<str:hash>/<str:payment>/', RedirectView.as_view(),
            name='redirect'),
        path('return/<str:order>/<str:hash>/<str:payment>/', ReturnView.as_view(), name='return'),
    ])),
]
