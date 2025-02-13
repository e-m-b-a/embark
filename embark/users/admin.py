__copyright__ = 'Copyright 2022-2025 Siemens Energy AG'
__author__ = 'Benedikt Kuehne'
__license__ = 'MIT'

import pprint
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.sessions.models import Session

from users.models import User, Team


UserAdmin.list_display += ('timezone',)
UserAdmin.list_filter += ('timezone',)
UserAdmin.fieldsets += (("Custom", {"fields": ('timezone',)}),)


class SessionAdmin(admin.ModelAdmin):
    def _session_data(self, obj):
        return pprint.pformat(obj.get_decoded()).replace('\n', '<br>\n')
    _session_data.allow_tags = True
    list_display = ['session_key', '_session_data', 'expire_date']
    readonly_fields = ['_session_data']
    exclude = ['session_data']
    date_hierarchy = 'expire_date'


admin.site.register(User, UserAdmin)
admin.site.register(Team)
admin.site.register(Session, SessionAdmin)
