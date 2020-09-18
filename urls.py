from .views import ArkServer, arkAcknowledgement, ArkDetail
from django.urls import include, path, re_path


urlpatterns = [
    path('', ArkServer.as_view(), name='ark-list'),
    path('<naan>/', arkAcknowledgement.as_view(), name='ark-statement'),
    path('<naan>/<ark>', ArkServer.as_view(), name='ark-detail'),
    path('<naan>/<ark>/detail', ArkDetail.as_view(), name='ark-details'),
]
