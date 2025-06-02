# Create your tests here.
__copyright__ = 'Copyright 2021-2025 Siemens Energy AG, Copyright 2021-2025 The AMOS Projects'
__author__ = 'Benedikt Kuehne, ashiven'
__license__ = 'MIT'

import secrets
from django.test import TestCase, Client

from workers.models import Worker, Configuration
from workers.orchestrator import WorkerOrchestrator
from users.models import User


class TestOrchestrator(TestCase):
    def setUp(self):
        user = User.objects.create(username='test123')
        user.set_password('12345')
        user.api_key = secrets.token_urlsafe(32)
        user.save()
        self.client = Client()
        Configuration.objects.create(user=user, name='test_config', ssh_user='test_user', ssh_password='test_password', ip_range='192.111.111/32')  # nosec
        test_worker1 = Worker.objects.create(name='test_worker1', ip_address='192.111.111', system_info={}, reachable=True)
        test_worker2 = Worker.objects.create(name='test_worker2', ip_address='192.111.112', system_info={}, reachable=True)
        test_worker1.configurations.add(Configuration.objects.first())
        test_worker2.configurations.add(Configuration.objects.first())

    def test_worker_creation(self):
        """
        Test that a worker can be created and saved correctly.
        """
        worker = Worker.objects.get(name='test_worker1')
        self.assertEqual(worker.name, 'test_worker1')
        self.assertEqual(worker.ip_address, '192.111.111')
        self.assertTrue(worker.reachable)

    def test_orchestrator_add_worker(self):
        """
        Test that a worker can be added to the orchestrator.
        """
        orchestrator = WorkerOrchestrator()
        worker = Worker.objects.get(name='test_worker1')
        orchestrator.add_worker(worker)
        self.assertIn(worker.ip_address, orchestrator.get_free_workers())

    def test_orchestrator_assign_worker(self):
        """
        Test that a worker can be assigned a task in the orchestrator.
        """
        orchestrator = WorkerOrchestrator()
        worker = Worker.objects.get(name='test_worker1')
        orchestrator.add_worker(worker)
        task = 'test_task1'
        orchestrator.assign_worker(worker, task)
        self.assertIn(worker.ip_address, orchestrator.get_busy_workers())
        self.assertEqual(orchestrator.get_busy_workers()[worker.ip_address].job_id, task)

    def test_orchestrator_basic_logic(self):
        """
        Test the basic logic of the orchestrator.
        """
        orchestrator = WorkerOrchestrator()
        worker1 = Worker.objects.get(name="test_worker1")
        worker2 = Worker.objects.get(name="test_worker2")
        orchestrator.add_worker(worker1)
        orchestrator.add_worker(worker2)
        task1 = "test_task_1"
        task2 = "test_task_2"
        orchestrator.assign_worker(worker1, task1)
        orchestrator.assign_worker(worker2, task2)
        orchestrator.release_worker(worker1)
        orchestrator.release_worker(worker2)
        orchestrator.assign_worker(worker2, task1)
        orchestrator.remove_worker(worker1)
        self.assertIn(worker2.ip_address, orchestrator.get_busy_workers())
        self.assertNotIn(worker1.ip_address, orchestrator.get_free_workers())
        orchestrator.release_worker(worker2)
        self.assertIn(worker2.ip_address, orchestrator.get_free_workers())


    def test_fifo_assign_task(self):
        """
        Test that tasks are assigned in FIFO order.
        """
        orchestrator = WorkerOrchestrator()
        worker1 = Worker.objects.get(name="test_worker1")
        worker2 = Worker.objects.get(name="test_worker2")
        orchestrator.add_worker(worker1)
        orchestrator.add_worker(worker2)

        task1 = "task_1"
        task2 = "task_2"
        task3 = "task_3"

        orchestrator.assign_task(task1)
        orchestrator.assign_task(task2)
        orchestrator.assign_task(task3)

        self.assertEqual(orchestrator.get_busy_workers()[worker1.ip_address].job_id, task1)
        self.assertEqual(orchestrator.get_busy_workers()[worker2.ip_address].job_id, task2)
        self.assertEqual(orchestrator.queue_tasks[0], task3)
        orchestrator.release_worker(worker1)
        self.assertEqual(orchestrator.get_busy_workers()[worker1.ip_address].job_id, task3)
        orchestrator.release_worker(worker1)
        orchestrator.assign_task(task2)
        self.assertEqual(orchestrator.get_busy_workers()[worker1.ip_address].job_id, task2)

