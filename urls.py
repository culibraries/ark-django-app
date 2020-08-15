# LibcalTokenView, SierraSearchView
from .views import ArkServer, arkAcknowledgement
from django.urls import include, path, re_path
_author__ = 'mstacy'


urlpatterns = [
    path('', ArkServer.as_view(), name='ark-list'),
    re_path('(?P<naan>[^/])/$',
            arkAcknowledgement.as_view(), name='ark-statement'),
    re_path('(?P<naan>[^/]+)/(?P<ark>[^/]+)/$',
            ArkServer.as_view(), name='ark-detail'),

]

# re_path('/(?P<database>[^/]+)/(?P<collection>[^/]+)/(?P<id>[^/]+)/$', CatalogDataDetail.as_view(),
#              name='catalog-detail-id'),

# urlpatterns = [
#     path('mintArk', LibcalTokenView.as_view(), name='libcal-token'),
#     path('ark', SierraSearchView.as_view(), name='sierra-search')
# ]
