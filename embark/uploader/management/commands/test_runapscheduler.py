__copyright__ = 'Copyright 2021-2025 Siemens Energy AG, Copyright 2021 The AMOS Projects'
__author__ = 'm-1-k-3, Maximilian Wagner, Benedikt Kuehne'
__license__ = 'MIT'

import time

from django.test import TransactionTestCase

from uploader.models import ResourceTimestamp
from uploader.management.commands.runapscheduler import resource_tracker, delete_old_job_executions


class UnpackerTest(TransactionTestCase):

    def setUp(self):
        # nothing to do here
        pass

    def test_resource_entry_store(self):
        init_len = len(ResourceTimestamp.objects.all())

        resource_tracker()

        self.assertEqual(init_len + 1, len(ResourceTimestamp.objects.all()),
                         "resource_tracker() does not store entry properly")

    def test_resource_entry_store_delete(self):

        old_jobs = 5
        new_jobs = 5

        for _ in range(old_jobs):
            resource_tracker()

        # make jobs old jobs
        time.sleep(1)

        for _ in range(new_jobs):
            resource_tracker()

        # delete at least all old jobs
        delete_old_job_executions(max_age=1)

        self.assertLessEqual(len(ResourceTimestamp.objects.all()), new_jobs,
                             "delete_old_job_executions() does not delete properly")
