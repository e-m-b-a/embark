from django.test import TestCase

from .boundedExecutor import boundedExecutor


class test_boundedExecutor(TestCase):

    def setUp(self):
        self.boundExecutor = boundedExecutor(bound=2, max_workers=2)

    # TODO: add timeout
    def test_non_blocking_overflow(self):

        fut_list = []

        for _ in range(4):
            # if testing under windows use "timeout /T 5" instead of "sleep 5"
            fut = self.boundExecutor.submit(self.boundExecutor.run_shell_cmd, "sleep 5")
            self.assertIsNotNone(fut)
            fut_list.append(fut)

        for _ in range(2):
            fut = self.boundExecutor.submit(self.boundExecutor.run_shell_cmd, "sleep 5")
            self.assertIsNone(fut)

        for fut in fut_list:
            fut.result()
