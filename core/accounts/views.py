from django.shortcuts import render
from django.contrib.auth import views as auth_views

from .forms import AuthenticationForm

# Create your views here.


class LoginView(auth_views.LoginView):
    """
    Display the login form and handle the login action.
    """
    form_class = AuthenticationForm
    template_name = "accounts/login.html"
    redirect_authenticated_user = True 