from django.test import TestCase

from uploader.boundedexecutor import BoundedExecutor, MAX_WORKERS, MAX_QUEUE


class TestBoundedExecutor(TestCase):

    def setUp(self):
        pass

    # TODO: add timeout
    def test_non_blocking_overflow(self):

        fut_list = []

        for _ in range(MAX_WORKERS + MAX_QUEUE):
            # if testing under windows use "timeout /T 5" instead of "sleep 5"
            fut = BoundedExecutor.submit(BoundedExecutor.run_emba_cmd, "sleep 5")
            self.assertIsNotNone(fut)
            fut_list.append(fut)

        for _ in range(MAX_WORKERS):
            fut = BoundedExecutor.submit(BoundedExecutor.run_emba_cmd, "sleep 5")
            self.assertIsNone(fut)

        for fut in fut_list:
            fut.result()
