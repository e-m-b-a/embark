# pylint: disable=E1101
__copyright__ = 'Copyright 2021-2025 Siemens Energy AG, Copyright 2021 The AMOS Projects'
__author__ = 'Benedikt Kuehne, Maximilian Wagner, m-1-k-3, VAISHNAVI UMESH, diegiesskanne'
__license__ = 'MIT'

import logging

from django.conf import settings
from django import forms
from rest_framework import serializers

from uploader import models

logger = logging.getLogger(__name__)


class FirmwareAnalysisSerializer(serializers.ModelSerializer):
    MODULE_CHOICES = settings.EMBA_MODULE_DICT['F_Modules'] + settings.EMBA_MODULE_DICT['L_Modules'] + settings.EMBA_MODULE_DICT['P_Modules'] + settings.EMBA_MODULE_DICT['S_Modules'] + settings.EMBA_MODULE_DICT['Q_Modules']
    scan_modules = forms.MultipleChoiceField(choices=MODULE_CHOICES, help_text='Enable/disable specific scan-modules for your analysis', widget=forms.CheckboxSelectMultiple, required=False)

    class Meta:
        model = models.FirmwareAnalysis
        fields = ['firmware', 'version', 'device', 'notes', 'firmware_Architecture', 'user_emulation_test', 'system_emulation_test', 'sbom_only_test', 'scan_modules']

    def validate_scan_modules(self, value):
        logger.debug("starting the cleaning")
        _scan_modules = value or None
        logger.debug("got modules : %s", _scan_modules)
        return _scan_modules
