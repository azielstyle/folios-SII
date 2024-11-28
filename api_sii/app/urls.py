from django.urls import re_path
from .views import GenerateCaf
from .views_old import PedirFolios,AnularFolios,ConsultarFolio,ViewLog


urlpatterns = [
    re_path(r'^solicitarFolios/´$',PedirFolios.as_view(),name='api_getFolios'),
    re_path(r'^anularFolios/$',AnularFolios.as_view(), name='api_deleteFolios' ),
    re_path(r'^consultarFolios/$',ConsultarFolio.as_view(),name='api_consultaFolios'),
    re_path(r'^logs/$', ViewLog.as_view(),name='logs'),
    re_path(r'caf/generate_caf/$', GenerateCaf.as_view(),name='request_caf')

]