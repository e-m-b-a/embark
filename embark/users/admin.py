__copyright__ = 'Copyright 2022-2024 Siemens Energy AG'
__author__ = 'Benedikt Kuehne'
__license__ = 'MIT'

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from users.models import User, Team, TeamMember

admin.site.register(User, UserAdmin)
admin.site.register(Team, UserAdmin)
admin.site.register(TeamMember, UserAdmin)
