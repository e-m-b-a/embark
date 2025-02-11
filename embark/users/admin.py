__copyright__ = 'Copyright 2022-2024 Siemens Energy AG'
__author__ = 'Benedikt Kuehne'
__license__ = 'MIT'

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from users.models import User, Team

UserAdmin.list_display += ('timezone',)
UserAdmin.list_filter += ('timezone',)
UserAdmin.fieldsets += (("Custom", {"fields": ('timezone',)}),)

admin.site.register(User, UserAdmin)
admin.site.register(Team)
