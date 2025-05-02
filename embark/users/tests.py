__copyright__ = 'Copyright 2021-2025 Siemens Energy AG'
__author__ = 'Benedikt Kuehne'
__license__ = 'MIT'

from http import HTTPStatus
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.http import HttpResponseRedirect
from django.conf import settings

from django.test import TestCase
from django.test import Client

from users.models import User


class TestUsers(TestCase):
    def setUp(self):
        user = User.objects.create(username='testuser')
        user.set_password('12345')
        user.save()
        self.client = Client()

    def test_register(self):
        """
        Right register would redirect to home.
        Returns:

        """
        response = self.client.post('/user/register/', {'username': 'testuser1', 'password': '12345', 'confirm_password': '12345'})
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_login(self):
        """
        Right password would redirect to home.
        Returns: redirect (302) to mainDashboard

        """
        response = self.client.post(settings.LOGIN_URL, {'username': 'testuser', 'password': '12345'})
        self.assertEqual(response.status_code, HTTPStatus.FOUND)

    def test_register__wrong_password(self):
        """
        Wrong password would render the same page again with 200 status code.
        Returns:

        """
        response = self.client.post(settings.LOGIN_URL, {'username': 'testuser', 'password': '1234'})
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_register__wrong_body(self):
        """
        Register api expects two keys in the body.
        email and password. On getting wrong body.
        it would render the same page again with 200 status code.
        Returns:

        """
        response = self.client.post(settings.LOGIN_URL, {'email': 'testuser', 'password': '12345'})
        self.assertEqual(response.status_code, HTTPStatus.OK)
