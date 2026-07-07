from django.urls import path

from . import views

app_name = 'core'

urlpatterns = [
    path('', views.main_page, name='main'),
    path('login/', views.login_page, name='login'),
    path('signup/', views.signup_page, name='signup'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile_page, name='profile'),
    path('profile/edit/', views.edit_profile_page, name='edit_profile'),
    path('recommend/', views.recommend_crops_api, name='recommend'),
    path('theme/', views.set_theme, name='set_theme'),
    path('ask-ai/', views.ask_ai_api, name='ask_ai'),
]
