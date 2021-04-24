from django.template.loader import get_template
from django.http import HttpResponse

# TODO: Add required headers like type of requests allowed later.


# home page test view TODO: change name accordingly
def home(request):
    html_body = get_template('uploader/home.html')
    return HttpResponse(html_body.render())


# additional page test view TODO: change name accordingly
def about(request):
    html_body = get_template('uploader/about.html')
    return HttpResponse(html_body.render())
