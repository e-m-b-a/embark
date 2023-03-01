# pylint: disable=E1101
import logging
from django import forms

from uploader import models

logger = logging.getLogger(__name__)


class VendorForm(forms.ModelForm):

    class Meta:
        model = models.Vendor

        fields = ['vendor_name']


class LabelForm(forms.ModelForm):

    class Meta:
        model = models.Label

        fields = ['label_name']


class DeviceForm(forms.ModelForm):

    class Meta:
        model = models.Device

        fields = ['device_name', 'device_label', 'device_vendor']


class FirmwareAnalysisForm(forms.ModelForm):
    MODULE_CHOICES = [
        ('s02', 'S02_UEFI_FwHunt'),
        ('s03', 'S03_firmware_bin_base_analyzer'),
        ('s05', 'S05_firmware_details'),
        ('s06', 'S06_distribution_identification'),
        ('s08', 'S08_package_mgmt_extractor'),
        ('s09', 'S09_firmware_base_version_check'),
        ('s10', 'S10_binaries_basic_check'),
        ('s12', 'S12_binary_protection'),
        ('s13', 'S13_weak_func_check'),
        ('s14', 'S14_weak_func_radare_check'),
        ('s15', 'S15_bootloader_check'),
        ('s20', 'S20_shell_check'),
        ('s21', 'S21_python_check'),
        ('s22', 'S22_php_check'),
        ('s24', 'S24_kernel_bin_identifier'),
        ('s25', 'S25_kernel_check'),
        ('s35', 'S35_http_file_check'),
        ('s40', 'S40_weak_perm_check'),
        ('s45', 'S45_pass_file_check'),
        ('s50', 'S50_authentication_check'),
        ('s55', 'S55_history_file_check'),
        ('s60', 'S60_cert_file_check'),
        ('s65', 'S65_config_file_check'),
        ('s70', 'S70_hidden_file_check'),
        ('s75', 'S75_network_check'),
        ('s80', 'S80_cronjob_check'),
        ('s85', 'S85_ssh_check'),
        ('s90', 'S90_mail_check'),
        ('s95', 'S95_interesting_binaries_check'),
        ('s99', 'S99_grepit'),
        ('s100', 'S100_command_inj_check'),
        ('s106', 'S106_deep_key_search'),
        ('s107', 'S107_deep_password_search'),
        ('s108', 'S108_stacs_password_search'),
        ('s109', 'S109_jtr_local_pw_cracking'),
        ('s110', 'S110_yara_check'),
        ('s115', 'S115_usermode_emulator'),
        ('s116', 'S116_qemu_version_detection'),
        ('s120', 'S120_cwe_checker')
    ]
    scan_modules = forms.MultipleChoiceField(choices=MODULE_CHOICES, help_text='Enable/disable specific scan-modules for your analysis', widget=forms.CheckboxSelectMultiple, required=False)

    class Meta:
        model = models.FirmwareAnalysis

        fields = ['firmware', 'version', 'device', 'notes', 'firmware_Architecture', 'user_emulation_test', 'system_emulation_test', 'scan_modules']
        widgets = {
            "device": forms.CheckboxSelectMultiple,
        }

    def clean_scan_modules(self):
        logger.debug("starting the cleaning")
        _scan_modules = self.cleaned_data.get('scan_modules') or None
        logger.debug("got modules : %s", _scan_modules)
        return _scan_modules


class DeleteFirmwareForm(forms.Form):
    firmware = forms.ModelChoiceField(queryset=models.FirmwareFile.objects, empty_label='Select firmware-file to delete')
