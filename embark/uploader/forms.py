# pylint: disable=E1101
__copyright__ = 'Copyright 2021-2025 Siemens Energy AG, Copyright 2021 The AMOS Projects'
__author__ = 'Benedikt Kuehne, Maximilian Wagner, m-1-k-3, VAISHNAVI UMESH, diegiesskanne'
__license__ = 'MIT'

import logging

from django.conf import settings
from django import forms

from embark.helper import get_emba_modules
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

    def clean(self):
        cleaned_data = super().clean()
        name = cleaned_data.get('device_name')
        vendor = cleaned_data.get('device_vendor')
        if name and vendor:
            if models.Device.objects.filter(device_name=name, device_vendor=vendor).exists():
                self.add_error('device_name', 'device already created')
        return cleaned_data


class FirmwareAnalysisForm(forms.ModelForm):
    try:
        emba_module_dict = get_emba_modules(settings.EMBA_ROOT)
    except FileNotFoundError as file_error:
        emba_module_dict = {
            'D_Modules': [
                ('d10', 'D10_firmware_diffing'),
                ('d02', 'D02_firmware_diffing_bin_details'),
                ('d05', 'D05_firmware_diffing_extractor')
            ],
            'F_Modules': [
                ('f02', 'F02_toolchain'),
                ('f50', 'F50_base_aggregator'),
                ('f15', 'F15_cyclonedx_sbom'),
                ('f05', 'F05_qs_resolver'),
                ('f10', 'F10_license_summary'),
                ('f20', 'F20_vul_aggregator')
            ],
            'L_Modules': [
                ('l99', 'L99_cleanup'),
                ('l35', 'L35_metasploit_check'),
                ('l10', 'L10_system_emulation'),
                ('l23', 'L23_vnc_checks'),
                ('l25', 'L25_web_checks'),
                ('l20', 'L20_snmp_checks'),
                ('l22', 'L22_upnp_hnap_checks'),
                ('l15', 'L15_emulated_checks_nmap')
            ],
            'P_Modules': [
                ('p15', 'P15_ubi_extractor'),
                ('p60', 'P60_deep_extractor'),
                ('p02', 'P02_firmware_bin_file_check'),
                ('p35', 'P35_UEFI_extractor'),
                ('p14', 'P14_ext_mounter'),
                ('p07', 'P07_windows_exe_extract'),
                ('p25', 'P25_android_ota'),
                ('p18', 'P18_BMC_decryptor'),
                ('p99', 'P99_prepare_analyzer'),
                ('p50', 'P50_binwalk_extractor'),
                ('p20', 'P20_foscam_decryptor'),
                ('p40', 'P40_DJI_extractor'),
                ('p22', 'P22_Zyxel_zip_decrypt'),
                ('p17', 'P17_gpg_decompress'),
                ('p65', 'P65_package_extractor'),
                ('p21', 'P21_buffalo_decryptor'),
                ('p19', 'P19_bsd_ufs_mounter'),
                ('p23', 'P23_qemu_qcow_mounter'),
                ('p55', 'P55_unblob_extractor'),
                ('p10', 'P10_vmdk_extractor')
            ],
            'Q_Modules': [('q02', 'Q02_openai_question')],
            'S_Modules': [
                ('s100', 'S100_command_inj_check'),
                ('s99', 'S99_grepit'),
                ('s90', 'S90_mail_check'),
                ('s03', 'S03_firmware_bin_base_analyzer'),
                ('s20', 'S20_shell_check'),
                ('s02', 'S02_UEFI_FwHunt'),
                ('s45', 'S45_pass_file_check'),
                ('s12', 'S12_binary_protection'),
                ('s23', 'S23_lua_check'),
                ('s110', 'S110_yara_check'),
                ('s60', 'S60_cert_file_check'),
                ('s35', 'S35_http_file_check'),
                ('s24', 'S24_kernel_bin_identifier'),
                ('s16', 'S16_ghidra_decompile_checks'),
                ('s50', 'S50_authentication_check'),
                ('s108', 'S108_stacs_password_search'),
                ('s21', 'S21_python_check'),
                ('s109', 'S109_jtr_local_pw_cracking'),
                ('s17', 'S17_cwe_checker'),
                ('s25', 'S25_kernel_check'),
                ('s09', 'S09_firmware_base_version_check'),
                ('s65', 'S65_config_file_check'),
                ('s18', 'S18_capa_checker'),
                ('s36', 'S36_lighttpd'),
                ('s05', 'S05_firmware_details'),
                ('s115', 'S115_usermode_emulator'),
                ('s55', 'S55_history_file_check'),
                ('s27', 'S27_perl_check'),
                ('s80', 'S80_cronjob_check'),
                ('s19', 'S19_apk_check'),
                ('s95', 'S95_interesting_files_check'),
                ('s75', 'S75_network_check'),
                ('s106', 'S106_deep_key_search'),
                ('s107', 'S107_deep_password_search'),
                ('s15', 'S15_radare_decompile_checks'),
                ('s07', 'S07_bootloader_check'),
                ('s22', 'S22_php_check'),
                ('s26', 'S26_kernel_vuln_verifier'),
                ('s85', 'S85_ssh_check'),
                ('s10', 'S10_binaries_basic_check'),
                ('s13', 'S13_weak_func_check'),
                ('s08', 'S08_main_package_sbom'),
                ('s40', 'S40_weak_perm_check'),
                ('s118', 'S118_busybox_verifier'),
                ('s14', 'S14_weak_func_radare_check'),
                ('s116', 'S116_qemu_version_detection'),
                ('s04', 'S04_windows_basic_analysis'),
                ('s06', 'S06_distribution_identification')
            ]
        }
    MODULE_CHOICES = emba_module_dict['F_Modules'] + emba_module_dict['L_Modules'] + emba_module_dict['P_Modules'] + emba_module_dict['S_Modules'] + emba_module_dict['Q_Modules']
    scan_modules = forms.MultipleChoiceField(choices=MODULE_CHOICES, help_text='Enable/disable specific scan-modules for your analysis', widget=forms.CheckboxSelectMultiple, required=False)

    class Meta:
        model = models.FirmwareAnalysis

        fields = ['firmware', 'version', 'device', 'notes', 'firmware_Architecture', 'user_emulation_test', 'system_emulation_test', 'sbom_only_test', 'web_report', 'scan_modules']
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


class DownloadFirmwareForm(forms.Form):
    firmware = forms.ModelChoiceField(queryset=models.FirmwareFile.objects, empty_label='Select firmware-file to download')
