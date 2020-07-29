"""
Alliance URLconf
"""

from django.urls import path

from . import views

urlpatterns = [
    path('', views.home, name='alliance-home'),
    path('<int:ally_id>/', views.sheet, name='alliance-sheet'),
]
