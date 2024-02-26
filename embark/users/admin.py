__copyright__ = 'Copyright 2022-2024, Siemens Energy AG'
__author__ = 'BenediktMKuehne'

from django.contrib import admin

from users.models import User, Team, TeamMember

admin.site.register(User)
admin.site.register(Team)
admin.site.register(TeamMember)
