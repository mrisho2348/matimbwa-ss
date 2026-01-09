from django.urls import path
from . import views

urlpatterns = [
    path('', views.public_home, name='public_home'),
    path('about/', views.about_school, name='about_school'),
    path('programs/', views.academic_programs, name='academic_programs'),
    path('news/', views.news_and_updates, name='news_updates'),
    path('gallery/', views.gallery_and_events, name='gallery_events'),
    path('contact/', views.contact_school, name='public_contact'),
    path('login/', views.public_login, name='public_login'),
    path('logout/', views.public_logout, name='public_logout'),
    path('register/', views.public_register, name='public_register'),
    path('register/check/', views.public_register_check, name='public_register_check'),
    path('register/ajax/', views.public_register_ajax, name='public_register_ajax'),
]
