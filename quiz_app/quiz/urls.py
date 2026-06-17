from django.urls import path
from . import views
urlpatterns = [

    path('', views.home, name='QuizHome'),
    path('score/', views.score, name='score'),
    path('leaderboard/', views.leaderboard, name='leaderboard'),
    path('login/', views.loginl, name="bruuuuuuh"),
    path('logout/', views.logoutl, name="bruuuuuuhsdfgsdfgsdfsdfgsdfg"),
    path('archive/', views.archive_cats, name="bruuuusdffgjkjgfvbnjuuh"),
    path('about/', views.about, name="bruuuusdffgjkjgfvbnjuuh"),
    path('archive/<str:event>/', views.archive_cats_events, name="bruuuusdffgjkjgfvbnjuuh"),
    path('archive/<str:event>/<str:title>/', views.archive_cats_events_title, name="bruuuusdffgjkjgfvbnjuuh"),
    path('flashcard/categories/', views.cats, name="bruhh"),
    path('flashcard/categories/questions/Random', views.randomCat, name="imaginesmhhh"),
    path('flashcard/categories/<str:maincat>', views.subcats, name="imaginesmh"),
    path('flashcard/categories/questions/<str:cat>', views.categories, name="bruh"),
    path('mcq/categories/', views.cats, name="bruhh"),
    path('mcq/categories/questions/Random', views.randomCat, name="imaginesmhhh"),
    path('mcq/categories/<str:maincat>', views.subcats, name="imaginesmh"),
    path('mcq/categories/questions/<str:cat>', views.mcqcategories, name="bruh"),
    path('written/categories/', views.cats, name="bruhh"),
    path('written/categories/questions/Random', views.mcqrandomCat, name="imaginesmhhh"),
    path('written/categories/<str:maincat>', views.subcats, name="imaginesmh"),
    path('written/categories/questions/<str:cat>', views.writtencategories, name="bruh"),
    path('written/categories/questions/<str:cat>/<str:number>', views.writtencategoriesstuff, name="bruh"),
    path('connect/categories/', views.cats, name="bruhh"),
    path('connect/categories/questions/Random', views.mcqrandomCat, name="imaginesmhhh"),
    path('connect/categories/<str:maincat>', views.subcats, name="imaginesmh"),
    path('connect/categories/questions/<str:cat>', views.connectcategories, name="bruh"),
    path('connect/categories/questions/<str:cat>/<str:number>', views.connectcategoriesstuff, name="brudfghdfghdfghdfghdfghdfghdfghdfghh"),
    path('audiovisual/categories/',views.cats,name="brahfhasdfhisdhf"),
    path('audiovisual/categories/questions/Random', views.randomCat, name="imaginesmasdaddghdgfhdgfhdfghfhhh"),
    path('audiovisual/categories/<str:maincat>', views.subcats, name="imagihdfghdfghdfghdgfhdfghnesmh"),
    path('audiovisual/categories/questions/<str:cat>', views.audiovisualcategories, name="bruh"),
    path('audiovisual/categories/questions/<str:cat>/<str:number>', views.audiovisualcategoriesstuff, name="brasdfasdfasdfasdfuh"),





]
