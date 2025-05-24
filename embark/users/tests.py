__copyright__ = 'Copyright 2021-2025 Siemens Energy AG, Copyright 2021 The AMOS Projects'
__author__ = 'Benedikt Kuehne, ashiven'
__license__ = 'MIT'

from http import HTTPStatus
import secrets
from django.conf import settings

from django.test import TestCase
from django.test import Client

from users.models import User


# class SeleniumTests(StaticLiveServerTestCase):
#     fixtures = ['user-data.json']
#
#     @classmethod
#     def setUpClass(cls):
#         super().setUpClass()
#         cls.driver = webdriver.Firefox()
#         cls.driver.implicitly_wait(10)
#
#     @classmethod
#     def tearDownClass(cls):
#         cls.driver.quit()
#         super().tearDownClass()
#
#     def test_register(self):
#         self.driver.get(f'{self.live_server_url}/register')
#         username_input = self.driver.find_element(By.NAME, "name")
#         username_input.send_keys('tester')
#         password_input = self.driver.find_element(By.NAME, "password")
#         password_input.send_keys('tester')
#         confirm_password_input = self.driver.find_element(By.NAME, "confirm_password")
#         confirm_password_input.send_keys('tester')
#         self.driver.find_element(By.XPATH, '//input[@value="Register"]').click()
#
#     def test_login(self):
#         self.driver.get(f'{self.live_server_url}/')
#         username_input = self.driver.find_element(By.NAME, "username")
#         username_input.send_keys('tester')
#         password_input = self.driver.find_element(By.NAME, "password")
#         password_input.send_keys('tester')
#         self.driver.find_element(By.XPATH, '//input[@value="Login"]').click()


class TestAPI(TestCase):
    def setUp(self):
        user = User.objects.create(username='test123')
        user.set_password('12345')
        user.api_key = secrets.token_urlsafe(32)
        user.save()
        self.client = Client()  # pylint: disable=attribute-defined-outside-init

    def test_api_key_generation(self):
        """
        Test that the API key is generated and saved correctly.
        """
        user_pw = '12345'
        self.client.login(username='test123', password=user_pw)
        response = self.client.get('/user/generate_api_key/', {})
        self.assertEqual(response.status_code, HTTPStatus.FOUND)

        user = User.objects.get(username='test123')

        self.assertNotEqual(user.api_key, '')
        self.assertNotEqual(user.api_key, None)
        self.assertEqual(len(user.api_key), 43)  # 32 bytes + 11 for the URL-safe base64 encoding

    def test_unauthenticated(self):
        """
        Test that the API testing endpoint returns 401 when not authenticated.
        """
        response = self.client.get('/user/api_test/', {})
        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)
        self.assertEqual(response.content, b'{"error": "Missing API key"}')

    def test_authenticated(self):
        """
        Test that the API testing endpoint returns 200 when authenticated.
        """
        user = User.objects.get(username='test123')
        response = self.client.get('/user/api_test/', headers={'Authorization': user.api_key})
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(response.content, b'{"message": "Hello, test123!"}')


class TestUsers(TestCase):
    def setUp(self):
        user = User.objects.create(username='testuser')
        user.set_password('12345')
        user.save()
        self.client = Client()  # pylint: disable=attribute-defined-outside-init

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
