from django.test import TestCase
from django.test import Client
from users.models import User


class TestUsers(TestCase):
    def setUp(self) -> None:
        pass

    def test_signup(self):
        pass

    def test_signin(self):
        user = User.objects.create(username='testuser')
        user.set_password('12345')
        user.save()

        c = Client()

        response = c.post('/login/', {'username': 'john', 'password': 'smith'})
        print(response.status_code)
