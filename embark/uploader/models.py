from django.db import models
from mongoengine import Document


class Firmware(Document):
    title = StringField(required=True, max_length=200)
    posted = DateTimeField(default=datetime.datetime.utcnow)
    url = StringField(required=True)
    version = StringField(required=True, max_length=200)
    vendor = StringField(required=True, max_length=200)
    device = StringField(required=True, max_length=200)
    notes = StringField(required=True, max_length=200)
    firmware_Architecture = StringField(required=True, max_length=100)
    cwe_checker = BooleanField(required=True, default=False)
    docker_container = BooleanField(required=True, default=False)
    log_path = BooleanField(required=True, default=False)
    grep_able_log = BooleanField(required=True, default=False)
    relative_paths = BooleanField(required=True, default=False)
    ANSI_color = BooleanField(required=True, default=False)
    web_reporter = BooleanField(required=True, default=False)
    



# Create your models here.
