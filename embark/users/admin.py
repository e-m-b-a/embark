__copyright__ = 'Copyright 2022-2024 Siemens Energy AG'
__author__ = 'Benedikt Kuehne'
__license__ = 'MIT'

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin, GroupAdmin

from users.models import User, Team

UserAdmin.list_display += ('timezone', 'team_role',)
UserAdmin.list_filter += ('timezone', 'team_role',)
UserAdmin.fieldsets += ('timezone', 'team_role',)

admin.site.register(User, UserAdmin)
admin.site.register(Team, GroupAdmin)
