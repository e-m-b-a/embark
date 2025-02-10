__copyright__ = 'Copyright 2025 Siemens Energy AG'
__author__ = 'Benedikt Kuehne'
__license__ = 'MIT'

from django.core.management import BaseCommand
from django.contrib.auth.models import User, Group , Permission
import logging

GROUPS = {
    "Administration_Group": {
        # general permissions
        "log entry" : ["add","delete","change","view"],
        "group" : ["add","delete","change","view"],
        "permission" : ["add","delete","change","view"],
        "content type" : ["add","delete","change","view"],
        "session" : ["add","delete","change","view"],
        "django job" : ["add","delete","change","view"],
        "django job execution" : ["add","delete","change","view"],

        # model specific permissions
        "result" : ["add","delete","change","view"],
        "software bill of material" : ["add","delete","change","view"],
        "software info" : ["add","delete","change","view"],
        "vulnerability" : ["add","delete","change","view"],
        "log zip file" : ["add","delete","change","view"],
        "device" : ["add","delete","change","view"],
        "firmware analysis" : ["add","delete","change","view"],
        "firmware file" : ["add","delete","change","view"],
        "label" : ["add","delete","change","view"],
        "vendor" : ["add","delete","change","view"],

        # team permissions
        "team" : ["add","delete","change","view"],

        # user permissions
        "user" : ["add","delete","change","view",
                  "user_permission",
                  "tracker_permission",
                  "updater_permission",
                  "uploader_permission_minimal",
                  "uploader_permission_advanced",
                  "porter_permission",
                  "reporter_permission",
                  "dashboard_permission_minimal",
                  "dashboard_permission_advanced"
                  ]
    },

    "New_User" : {
        "content type" : ["view"],
        "session" : ["add","view"],
        "django job" : ["view"],
        "django job execution" : ["view"],

        "result" : ["add","delete","change","view"],
        "software bill of material" : ["add","delete","change","view"],
        "software info" : ["add","delete","change","view"],
        "vulnerability" : ["add","delete","change","view"],
        "log zip file" : ["add","delete","change","view"],
        "device" : ["add","delete","change","view"],
        "firmware analysis" : ["add","delete","change","view"],
        "firmware file" : ["add","delete","change","view"],
        "label" : ["add","delete","change","view"],
        "vendor" : ["add","delete","change","view"],

        # team permissions
        # "team" : ["view"],

        # user permissions
        "user" : ["user_permission",
                  "tracker_permission",
                  "updater_permission",
                  "uploader_permission_minimal",
                  "porter_permission",
                  "reporter_permission",
                  "dashboard_permission_minimal",
                  ]
    },

    "Group_Member": {
        "log entry" : ["view"],
        "group" : ["view"],
        "permission" : ["view"],
        "content type" : ["view"],
        "session" : ["add","view"],
        "django job" : ["add","change","view"],
        "django job execution" : ["add","change","view"],

        "result" : ["add","delete","change","view"],
        "software bill of material" : ["add","delete","change","view"],
        "software info" : ["add","delete","change","view"],
        "vulnerability" : ["add","delete","change","view"],
        "log zip file" : ["add","delete","change","view"],
        "device" : ["add","delete","change","view"],
        "firmware analysis" : ["add","delete","change","view"],
        "firmware file" : ["add","delete","change","view"],
        "label" : ["add","delete","change","view"],
        "vendor" : ["add","delete","change","view"],

        # team permissions
        "team" : ["view"],

        # user permissions
        "user" : ["view",
                  "user_permission",
                  "tracker_permission",
                  "updater_permission",
                  "uploader_permission_minimal",
                  "uploader_permission_advanced",
                  "porter_permission",
                  "reporter_permission",
                  "dashboard_permission_minimal",
                  "dashboard_permission_advanced"
                  ]
    },

    "Group_Manager": {
        "log entry" : ["view"],
        "group" : ["view"],
        "permission" : ["view"],
        "content type" : ["view"],
        "session" : ["add","view"],
        "django job" : ["add","change","view"],
        "django job execution" : ["add","change","view"],

        "result" : ["add","delete","change","view"],
        "software bill of material" : ["add","delete","change","view"],
        "software info" : ["add","delete","change","view"],
        "vulnerability" : ["add","delete","change","view"],
        "log zip file" : ["add","delete","change","view"],
        "device" : ["add","delete","change","view"],
        "firmware analysis" : ["add","delete","change","view"],
        "firmware file" : ["add","delete","change","view"],
        "label" : ["add","delete","change","view"],
        "vendor" : ["add","delete","change","view"],

        # team permissions
        "team" : ["add","change","view"],

        # user permissions
        "user" : ["view",
                  "user_permission",
                  "tracker_permission",
                  "updater_permission",
                  "uploader_permission_minimal",
                  "uploader_permission_advanced",
                  "porter_permission",
                  "reporter_permission",
                  "dashboard_permission_minimal",
                  "dashboard_permission_advanced"
                  ]
    }
}

class CreateDefaultGroups(BaseCommand):

    help = "Creates default permission groups for users"

    def handle(self, *args, **options):

        for group_name in GROUPS:

            new_group, created = Group.objects.get_or_create(name=group_name)

            # Loop models in group
            for app_model in GROUPS[group_name]:

                # Loop permissions in group/model
                for permission_name in GROUPS[group_name][app_model]:

                    # Generate permission name as Django would generate it
                    name = "Can {} {}".format(permission_name, app_model)
                    print("Creating {}".format(name))

                    try:
                        model_add_perm = Permission.objects.get(name=name)
                    except Permission.DoesNotExist:
                        logging.warning("Permission not found with name '{}'.".format(name))
                        continue

                    new_group.permissions.add(model_add_perm)
