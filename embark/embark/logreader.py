# pylint: disable=W0602
# ignores no-assignment error since there is one!
__copyright__ = 'Copyright 2021-2025 Siemens Energy AG, Copyright 2021 The AMOS Projects'
__author__ = 'Benedikt Kuehne, m-1-k-3, diegiesskanne, Maximilian Wagner, Garima Chauhan, Ashutosh Singh'
__license__ = 'MIT'

import builtins
import difflib
import pathlib
import re
import time
import logging
from embark.helper import count_emba_modules, get_emba_modules
import rx
import rx.operators as ops

from inotify_simple import INotify, flags
from asgiref.sync import async_to_sync

from channels.layers import get_channel_layer
from django.conf import settings
from django.utils import timezone

from uploader.models import FirmwareAnalysis


logger = logging.getLogger(__name__)

EMBA_PHASE_CNT = 4  # P, S, L, F modules
# EMBA states
EMBA_P_PHASE = 0
EMBA_S_PHASE = 1
EMBA_L_PHASE = 2
EMBA_F_PHASE = 3


class LogReader:
    def __init__(self, firmware_id):

        # global module count and status_msg directory
        self.module_cnt = 0
        self.firmware_id = firmware_id
        self.firmware_id_str = str(self.firmware_id)
        try:
            self.analysis = FirmwareAnalysis.objects.get(id=self.firmware_id)
        except FirmwareAnalysis.DoesNotExist:
            logger.error("No Analysis wit this id (%s)", self.firmware_id_str)

        # set variables for channels communication
        self.user = self.analysis.user
        self.room_group_name = f"services_{self.user}"
        self.channel_layer = get_channel_layer()

        # variables for cleanup
        self.finish = False
        # self.wd = None

        # status update dict (appended to db)
        self.status_msg = {
            "percentage": 0,
            "module": "",
            "phase": "",
        }

        # start processing
        time.sleep(10)   # embas dep-check takes some time
        if self.analysis:
            self.read_loop()
        else:
            self.cleanup()

    def save_status(self):
        logger.debug("Appending status with message: %s", self.status_msg)
        # append message to the json-field structure of the analysis
        self.analysis.status["percentage"] = self.status_msg["percentage"]
        self.analysis.status["last_update"] = str(timezone.now())
        # append modules and phase list
        if self.status_msg["module"] != self.analysis.status["last_module"]:
            self.analysis.status["last_module"] = self.status_msg["module"]
            self.analysis.status["module_list"].append(self.status_msg["module"])
        if self.status_msg["phase"] != self.analysis.status["last_phase"]:
            self.analysis.status["last_phase"] = self.status_msg["phase"]
            self.analysis.status["phase_list"].append(self.status_msg["phase"])
        if self.status_msg["percentage"] == 100:
            self.analysis.status["finished"] = True
            self.analysis.save(update_fields=["status"], force_update=True)
        else:
            self.analysis.save(update_fields=["status"])
        logger.debug("Checking status: %s", self.analysis.status)
        # send it to group
        async_to_sync(self.channel_layer.group_send)(
            self.room_group_name, {
                "type": 'send.message',
                "message": {str(self.analysis.id): self.analysis.status}
            }
        )

    @staticmethod
    def phase_identify(status_message):
        # phase patterns to match
        pre_checker_phase_pattern = "Pre-checking phase"        # P-modules
        testing_phase_pattern = "Testing phase"                 # S-Modules
        simulation_phase_pattern = "System emulation phase"     # L-Modules
        reporting_phase_pattern = "Reporting phase"             # P-Modules
        done_pattern = "Test ended on"
        failed_pattern = "EMBA failed in docker mode!"
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
        emba_s_mod_cnt, emba_p_mod_cnt, _emba_q_mod_cnt, emba_l_mod_cnt, emba_f_mod_cnt, _emba_d_mod_cnt = count_emba_modules(emba_module_dict)

        # calculate percentage
        max_module = -2
        phase_nmbr = -2
        if re.search(pattern=re.escape(pre_checker_phase_pattern), string=status_message["phase"]):
            max_module = emba_p_mod_cnt
            phase_nmbr = EMBA_P_PHASE
        elif re.search(pattern=re.escape(testing_phase_pattern), string=status_message["phase"]):
            max_module = emba_s_mod_cnt
            phase_nmbr = EMBA_S_PHASE
        elif re.search(pattern=re.escape(simulation_phase_pattern), string=status_message["phase"]):
            max_module = emba_l_mod_cnt
            phase_nmbr = EMBA_L_PHASE
        elif re.search(pattern=re.escape(reporting_phase_pattern), string=status_message["phase"]):
            max_module = emba_f_mod_cnt
            phase_nmbr = EMBA_F_PHASE
        elif re.search(pattern=re.escape(done_pattern), string=status_message["phase"]):
            max_module = 0
            phase_nmbr = EMBA_PHASE_CNT
        elif re.search(pattern=re.escape(failed_pattern), string=status_message["phase"]):
            max_module = -1
            phase_nmbr = EMBA_PHASE_CNT
        else:
            logger.info("Undefined pattern in logreader %s ", status_message["phase"])
            logger.info("Not updating status percentage")
        return max_module, phase_nmbr

    # update our dict whenever a new module is being processed
    def update_status(self, stream_item_list):
        percentage = 0
        max_module, phase_nmbr = self.phase_identify(self.status_msg)
        if max_module == 0:
            percentage = 100
            self.finish = True
        elif max_module > 0:
            self.module_cnt += 1
            self.module_cnt = self.module_cnt % max_module  # make sure it's in range
            percentage = phase_nmbr * (100 / EMBA_PHASE_CNT) + ((100 / EMBA_PHASE_CNT) / max_module) * self.module_cnt
        elif max_module == -1:
            percentage = 100
            self.finish = True
            logger.error("EMBA failed with  %s ", self.status_msg)
        else:
            logger.error("Undefined state in logreader %s ", self.status_msg)
            percentage = self.status_msg["percentage"]  # stays the same

        logger.debug("Status is %d, in phase %d, with modules %d", percentage, phase_nmbr, max_module)

        # set attributes of current message
        self.status_msg["module"] = stream_item_list[0]

        # ignore all Q-modules for percentage calc
        if not re.match(".*Q[0-9][0-9]", stream_item_list[0]):
            self.status_msg["percentage"] = percentage
        # ignore all D-modules for percentage calc
        elif not re.match(".*D[0-9][0-9]", stream_item_list[0]):
            self.status_msg["percentage"] = percentage

        # get copy of the current status message
        self.save_status()

    # update dictionary with phase changes
    def update_phase(self, stream_item_list):
        self.module_cnt = 0
        self.status_msg["phase"] = stream_item_list[1]
        if "Test ended" in stream_item_list[1]:
            self.finish = True
            self.status_msg["percentage"] = 100

        # get copy of the current status message
        self.save_status()

    def read_loop(self):
        """
        Infinite Loop for waiting for emba.log changes
            :param: None
            :exit condition: Not in this Function, but if emba has terminated this process is also killed
            :return: None
       """
        logger.info("read loop started for %s", self.firmware_id)

        # if file does not exist create it otherwise delete its content
        pat = f"{settings.EMBA_LOG_ROOT}/{self.firmware_id}/logreader.log"
        if not pathlib.Path(pat).exists():
            with open(pat, 'x', encoding='utf-8'):
                pass

        while not self.finish:
            # look for new events in log
            logger.debug("looking for events in %s", f"{self.analysis.path_to_logs}/emba.log")
            got_event = self.inotify_events(f"{self.analysis.path_to_logs}/emba.log")

            for eve in got_event:
                for flag in flags.from_mask(eve.mask):
                    # Ignore irrelevant flags TODO: add other possible flags
                    if flag is flags.CLOSE_NOWRITE or flag is flags.CLOSE_WRITE:
                        pass
                    # Act on file change
                    elif flag is flags.MODIFY:
                        # get the actual difference
                        tmp = self.get_diff(f"{self.analysis.path_to_logs}/emba.log")
                        logger.debug("Got diff-output: %s", tmp)
                        # send changes to frontend
                        self.input_processing(tmp)
                        # copy diff to tmp file
                        self.copy_file_content(tmp)

        self.cleanup()
        logger.info("read loop done for %s", self.firmware_id)
        # return

    def cleanup(self):
        """
        Called when logreader should be cleaned up
        """
        # inotify = INotify()
        # inotify.rm_watch(self.wd)
        logger.debug("Log reader cleaned up for %s", self.firmware_id)
        # TODO do cleanup of emba_new_<self.firmware_id>.log

    @classmethod
    def process_line(cls, inp, pat):

        """
        Regex function for lambda
            :param inp: String to apply regex to
            :param pat: Regex pattern
            :return: True if regex matches otherwise False
        """
        if re.match(pat, inp):
            return True
        return False

    def copy_file_content(self, diff):
        """
        Helper function to copy new emba log messages to temporary file continuously
            :param diff: new line in emba log
            :return: None
        """
        with open(f"{settings.EMBA_LOG_ROOT}/{self.firmware_id}/logreader.log", 'a+', encoding='utf-8') as diff_file:
            diff_file.write(diff)
        logger.debug("wrote file-diff")

    def get_diff(self, log_file):
        """
        Get diff between two files via difflib
        copied from stack overflow : https://stackoverflow.com/questions/15864641/python-difflib-comparing-files
            :param: None
            :return: result of difflib call without preceding symbols
        """
        # open the two files to get diff from
        logger.debug("getting diff from %s", log_file)
        with open(log_file, mode='r', encoding='utf-8') as old_file, open(f"{settings.EMBA_LOG_ROOT}/{self.firmware_id}/logreader.log", encoding='utf-8') as new_file:
            diff = difflib.ndiff(old_file.readlines(), new_file.readlines())
            return ''.join(x[2:] for x in diff if x.startswith('- '))

    def input_processing(self, tmp_inp):
        """
        RxPy Function for processing the file diffs and trigger send packet to frontend
            :param tmp_inp: file diff = new line in emba log
            :return: None
        """
        logger.debug("starting observers for log file %s", self.analysis.path_to_logs)

        status_pattern = "\\[\\*\\]*"
        phase_pattern = "\\[\\!\\]*"

        color_pattern = "\\x1b\\[.{1,5}m"

        cur_ar = tmp_inp.splitlines()

        # create observable
        source_stream = rx.from_iterable(cur_ar)

        # observer for status messages
        source_stream.pipe(
            ops.map(lambda s: re.sub(color_pattern, '', s)),
            ops.filter(lambda s: self.process_line(s, status_pattern)),
            ops.map(lambda a: a.split("- ")),
            ops.map(lambda t: t[1]),
            ops.map(lambda b: b.split(" ")),
            ops.filter(lambda c: c[1] == 'finished')
        ).subscribe(
            lambda x: [self.update_status(x)]    # , self.test_list1.append(x)]
        )

        # observer for phase messages
        source_stream.pipe(
            ops.map(lambda s: re.sub(color_pattern, '', s)),
            ops.filter(lambda u: self.process_line(u, phase_pattern)),
            ops.map(lambda v: v.split(" ", 1)),
            ops.filter(lambda w: w[1])
        ).subscribe(
            lambda x: [self.update_phase(x)]     # , self.test_list2.append(x)
        )

    @classmethod
    def inotify_events(cls, path):
        inotify = INotify()
        watch_flags = flags.CREATE | flags.DELETE | flags.MODIFY | flags.DELETE_SELF | flags.CLOSE_NOWRITE | flags.CLOSE_WRITE
        try:
            # add watch on file
            inotify.add_watch(path, watch_flags)
            return inotify.read()
        except builtins.Exception as error:
            logger.error("inotify_event error in %s:%s", path, error)
            return []


if __name__ == "__main__":
    PHASE = "\\[\\!\\]*"
    test_dir = pathlib.Path(__file__).resolve().parent.parent.parent
    status_msg = {
        "firmwarename": "LogTestFirmware",
        "percentage": 0,
        "module": "",
        "phase": "",
    }

    with open(f"{test_dir}/test/logreader/test-run-good.log", 'r', encoding='UTF-8') as test_file:
        for line in test_file:
            if re.match(PHASE, line) is not None:
                status_msg["phase"] = line
            LogReader.phase_identify(status_msg)
