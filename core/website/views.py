from django.shortcuts import render
from django.views import generic

from shop.models import ProductModel

# Create your views here.


class IndexShowView(generic.ListView):
    template_name = "website/index.html"
    queryset =  ProductModel.objects.published()[:4] #type: ignore
    context_object_name = "products"


class ContactTemplateView(generic.TemplateView):
    template_name = "website/contact.html"


class AboutTemplateView(generic.TemplateView):
    template_name = "website/about.html"
