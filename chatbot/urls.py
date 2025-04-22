from django.urls import path
from . import views

app_name = 'chatbot'

urlpatterns = [
    path('api/chat/', views.chat_endpoint, name='chat_endpoint'),
]