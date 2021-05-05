import sys
from django.template.loader import get_template
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.core.files.storage import FileSystemStorage



# TODO: Add required headers like type of requests allowed later.


# home page test view TODO: change name accordingly
def home(request):
    html_body = get_template('uploader/home.html')
    return HttpResponse(html_body.render())


# additional page test view TODO: change name accordingly
def about(request):
    html_body = get_template('uploader/about.html')
    return HttpResponse(html_body.render())

# Function which renders the uploader html
@csrf_exempt
def upload_file(request):

    html_body = get_template('uploader/fileUpload.html')
    return HttpResponse(html_body.render())

#Function which saves the file .
#request - Post request
@csrf_exempt
@require_http_methods(["POST"])
def save_file(request):
    try:
        fs = FileSystemStorage()
        for file in request.FILES.getlist('file'):
            fs.save(file.name,file)
        return HttpResponse("Firmwares has been successfully saved")
    except Exception  as error:
        return HttpResponse("Firware Couldn't be uploaded")


