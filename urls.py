# LibcalTokenView, SierraSearchView
from .views import ArkServer, arkAcknowledgement, ArkServerDetail
from django.urls import include, path, re_path
_author__ = 'mstacy'


urlpatterns = [
    path('', ArkServer.as_view(), name='ark-list'),
    path('<naan>/', arkAcknowledgement.as_view(), name='ark-statement'),
    path('<naan>/<ark>', ArkServer.as_view(), name='ark-detail'),
    path('<naan>/<ark>/detail', ArkServerDetail.as_view(), name='ark-details'),
]

# re_path('/(?P<database>[^/]+)/(?P<collection>[^/]+)/(?P<id>[^/]+)/$', CatalogDataDetail.as_view(),
#              name='catalog-detail-id'),

# urlpatterns = [
#     path('mintArk', LibcalTokenView.as_view(), name='libcal-token'),
#     path('ark', SierraSearchView.as_view(), name='sierra-search')
# ]
