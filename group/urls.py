"""
URLconf of the homepage
"""


from django.urls import path

from . import views


urlpatterns = [
    path('', views.home, name='home'),
    path('<str:group_id>', views.sheet, name='group-sheet')
]
