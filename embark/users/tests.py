from http import HTTPStatus
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.webdriver import WebDriver
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.http import HttpResponseRedirect

from django.test import TestCase
from django.test import Client

from users.models import User


class SeleniumTests(StaticLiveServerTestCase):
    fixtures = ['user-data.json']

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.selenium = WebDriver()
        cls.selenium.implicitly_wait(10)

    @classmethod
    def tearDownClass(cls):
        cls.selenium.quit()
        super().tearDownClass()

    def test_register(self):
        self.selenium.get(f'{self.live_server_url}/register')
        username_input = self.selenium.find_element(By.NAME, "username")
        username_input.send_keys('tester')
        password_input = self.selenium.find_element(By.NAME, "password")
        password_input.send_keys('tester')
        confirm_password_input = self.selenium.find_element(By.NAME, "confirm_password")
        confirm_password_input.send_keys('tester')
        self.selenium.find_element(By.XPATH, '//input[@value="Register"]').click()

    def test_login(self):
        self.selenium.get(f'{self.live_server_url}/')
        username_input = self.selenium.find_element(By.NAME, "username")
        username_input.send_keys('tester')
        password_input = self.selenium.find_element(By.NAME, "password")
        password_input.send_keys('tester')
        self.selenium.find_element(By.XPATH, '//input[@value="Login"]').click()


class TestUsers(TestCase):
    def __init__(self):
        super().__init__(self)
        user = User.objects.create(username='testuser')
        user.set_password('12345')
        user.save()
        self.client = Client()

    def test_signup(self):
        """
        Right signup would redirect to home.
        Returns:

        """
        response = self.client.post('/signup', {'username': 'testuser1', 'password': '12345', 'confirm_password': '12345'})
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_signin(self):
        """
        Right password would redirect to home.
        Returns: redirect (302) to mainDashboard

        """
        response = self.client.post('/signin', {'username': 'testuser1', 'password': '12345'})
        self.assertEqual(response.status_code, HttpResponseRedirect)

    def test_signin_wrong_password(self):
        """
        Wrongcd  password would render the same page again with 200 status code.
        Returns:

        """
        response = self.client.post('/signin', {'username': 'testuser', 'password': '1234'})
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_signin_wrong_body(self):
        """
        Signin api expects two keys in the body.
        email and password. On getting wrong body.
        it would render the same page again with 200 status code.
        Returns:

        """
        response = self.client.post('/signin', {'email': 'testuser', 'password': '12345'})
        self.assertEqual(response.status_code, HTTPStatus.OK)
