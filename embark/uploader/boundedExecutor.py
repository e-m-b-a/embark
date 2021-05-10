import logging
from concurrent.futures.thread import ThreadPoolExecutor
from subprocess import Popen
from threading import BoundedSemaphore


class boundedExecutor:
    """
        class boundedExecutor
        This class is a wrapper of ExecuterThreadPool to enable a limited queue
        Used to handle concurrent emba analysis as well as emba.log analyzer
    """

    def __init__(self, bound, max_workers):

        # assign the threadpool max_worker_threads
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        # create semaphore to track queue state
        self.semaphore = BoundedSemaphore(bound + max_workers)

        # emba directories
        self.emba_script_location = "/app/emba/emba.sh"
        self.emba_log_location = "/app/emba/log_%s"

    """
        run shell commands from python script as subprocess, waits for termination and evaluates returncode
        
        :param cmd: shell command to be executed
        
        :return: 
    """

    def run_shell_cmd(self, cmd):

        # TODO emba.log analyzer needs to be started
        emba_process = Popen(cmd, shell=True)
        emba_process.wait()

        # get return code to evaluate: 0 = display help, 1 = failure
        # TODO: propagate returncode to frontend
        if emba_process.returncode == 0:
            # display help
            print("display help")
            pass
        elif emba_process.returncode == 1:
            # error occured consult log
            print("error occured consult log")
            pass
        else:
            # dunno
            print("dunno")
            pass

    """
        run_shell_cmd but elevated

        :param cmd: shell command to be executed elevated

        :return: 
    """
    def run_shell_cmd_elavated(self, cmd):
        self.run_shell_cmd("sudo" + cmd)

    """
        submit firmware + metadata for emba execution

        params: firmware object (TODO)

        return: emba process future on success, None on failure
    """
    def submit_firmware(self, firmware):

        # TODO extract information from parameter / define proper interface
        image_file_location = 0
        image_file_name = "img"
        log_file_location = 0

        # evaluate meta information
        real_emba_log_location = (self.emba_log_location, image_file_name)
        emba_flags = "-D -i -g -s -z -W"

        # build command
        emba_cmd = ("%s -f %s -l %s %s", real_emba_log_location, image_file_location, log_file_location, emba_flags)

        # submit command to executorthreadpool
        emba_fut = self.executor.submit(self.run_shell_cmd, emba_cmd)

        if not emba_fut:
            # TODO handle full queue / where handle full queue
            return emba_fut

        return emba_fut

    """
        same as concurrent.futures.Executor#submit, but with queue

        params: see concurrent.futures.Executor#submit
        
        return: future on success, None on full queue
    """

    def submit(self, fn, *args, **kwargs):

        # check if semaphore can be acquired, if not queue is full
        queue_not_full = self.semaphore.acquire(blocking=False)
        if not queue_not_full:
            logging.error("Executor queue full")
            return None

        try:
            future = self.executor.submit(fn, *args, **kwargs)
        except Exception as e:
            logging.error("Executor task could not be submitted")
            self.semaphore.release()
            raise e
        else:
            future.add_done_callback(lambda x: self.semaphore.release())
            return future

    """See concurrent.futures.Executor#shutdown"""

    def shutdown(self, wait=True):
        self.executor.shutdown(wait)
