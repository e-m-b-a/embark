from django.test import TestCase
from django.test import Client

from http import HTTPStatus

from users.models import User


class TestUsers(TestCase):
    def setUp(self) -> None:
        user = User.objects.create(username='testuser')
        user.set_password('12345')
        user.save()
        self.client = Client()

    def test_signup(self):
        pass

    def test_signin(self):
        """
        Right password would redirect to home. This request gives a 302 status code i.e
        HTTPStatus.FOUND
        Returns:

        """
        response = self.client.post('/signin', {'email': 'testuser', 'password': '12345'})
        self.assertEqual(response.status_code, HTTPStatus.FOUND)

    def test_signin_wrong_password(self):
        """
        Wrongcd  password would render the same page again with 200 status code
        Returns:

        """
        response = self.client.post('/signin', {'email': 'testuser', 'password': '1234'})
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_signin_wrong_body(self):
        """
        Signin api expects two keys in the body.
        email and password. On getting wrong body.
        it throws 200 status code with content: ""User data is invalid""

        Returns:

        """

        response = self.client.post('/signin', {'username': 'testuser', 'password': '12345'})
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(response.content.decode("utf-8"), "User data is invalid")
