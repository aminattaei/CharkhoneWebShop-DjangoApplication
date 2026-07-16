from django.shortcuts import render
from django.views import generic

# Create your views here.


class IndexTemplateView(generic.TemplateView):
    template_name = "website/index.html"