from django.shortcuts import render
from django.template.loader import get_template
from django.template.response import TemplateResponse
from django.http import HttpResponse


# home page view
def home(request):
    # response = TemplateResponse(request, 'home.html', {})
    html_body = get_template('uploader/home.html')
    return HttpResponse(html_body.render())


# additional page view TODO: change name accordingly
def about(request):
    html_body = get_template('uploader/about.html')
    return HttpResponse(html_body.render())
