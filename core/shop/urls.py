"""
URL configuration for shop project.
"""

from django.urls import path, re_path
from . import views

app_name = "shop"

urlpatterns = [
    path("", views.ProductListView.as_view(), name="product_list"),
    # path("<int:pk>/", views.ProductDetailView.as_view(), name="product_detail"),
    path('product/<str:slug>/', views.ProductDetailView.as_view(), name='product_detail'),
    
]
