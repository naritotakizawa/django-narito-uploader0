from django.urls import path
from . import views

app_name = 'nuploader0'

urlpatterns = [
    path('', views.PathTop.as_view(), name='path'),
    path('zip/<int:pk>/', views.download_zip, name='zip'),
    # /index.html のようなURLを許可するため、末尾にスラッシュをつけない
    path('<path:request_path>', views.Path.as_view(), name='path')
]
