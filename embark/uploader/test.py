from django.test import TestCase


class TestCase(TestCase):

    def setUp(self):
        print("Running tests")

    def test_sum(self):
        assert sum([1, 2, 3]) == 6, "Should be 6"

    def test_sum_tuple(self):
        assert sum((1, 2, 3)) == 6, "Should be 6"
