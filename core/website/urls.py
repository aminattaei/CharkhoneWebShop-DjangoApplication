from django.urls import path

from . import views


app_name="website"

urlpatterns = [
    path('',views.IndexTemplateView.as_view(),name="home_page")
]
