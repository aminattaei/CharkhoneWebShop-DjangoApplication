from django.shortcuts import render
from django.views import generic

from shop.models import ProductModel,ProductStatusType

# Create your views here.


class IndexTemplateView(generic.TemplateView):
    template_name = "website/index.html"

    
    def get_context_data(self, **kwargs):
        context = super(IndexTemplateView, self).get_context_data(**kwargs)
        context['products'] = ProductModel.objects.filter(status =ProductStatusType.publish.value)[:10]
        return context
    

class ContactTemplateView(generic.TemplateView):
    template_name = "website/contact.html"


class AboutTemplateView(generic.TemplateView):
    template_name = "website/about.html"
