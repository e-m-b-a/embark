from django.test import TestCase
from django.test import Client
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
        # Right password would redirect to home
        response = self.client.post('/signin', {'email': 'testuser', 'password': '12345'})
        self.assertEqual(response.status_code, 302)

    def test_signin_wrong_password(self):
        # Right password would render the same page again with 200 status code
        response = self.client.post('/signin', {'email': 'testuser', 'password': '1234'})
        self.assertEqual(response.status_code, 200)

    def test_signin_wrong_body(self):
        # Signin api expects two keys in the body.
        # email and password. On getting wrong body.
        # it throws 200 status code with content: ""User data is invalid""
        response = self.client.post('/signin', {'username': 'testuser', 'password': '12345'})
        self.assertEqual(response.status_code, 200)
        print(response.content)
        self.assertEqual(response.content, "User data is invalid")
