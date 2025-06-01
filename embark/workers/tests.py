# Create your tests here.
__copyright__ = 'Copyright 2021-2025 Siemens Energy AG, Copyright 2021-2025 The AMOS Projects'
__author__ = 'Benedikt Kuehne, ashiven'
__license__ = 'MIT'

from http import HTTPStatus
import secrets
from django.conf import settings

from django.test import TestCase

from workers.models import Worker, Configuration
from workers.orchestrator import WorkerOrchestrator

"""
def test_orchestrator(request):
    orchestrator = WorkerOrchestrator()
    worker1 = Worker.objects.get(id=1)
    worker2 = Worker.objects.get(id=2)
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

    return JsonResponse({
        'free_workers': [worker.ip_address for worker in orchestrator.get_free_workers().values()],
        'busy_workers': [worker.ip_address for worker in orchestrator.get_busy_workers().values()],
        'specific_workers': orchestrator.get_specific_workers([worker2.ip_address])
    })
"""

class workerTests(TestCase):
    def setUp(self):
        Configuration.objects.create(
            user=None,  # Assuming user is not required for this test
            name='test_config',
            ssh_user='test_user',
            ssh_password='test_password',
            ip_range='192.111.111/32'
        )
        
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
        self.assertIn(worker2.ip_address, orchestrator.get_free_workers())
        
       
        