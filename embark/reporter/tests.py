import secrets
from http import HTTPStatus
from django.test import TestCase
from django.test import Client

from users.models import User
from uploader.models import FirmwareAnalysis, LogZipFile


class TestAPI(TestCase):
    def setUp(self):
        self.client = Client()

        # Create regular user
        self.user = User.objects.create(username='bob', email='bob@example.com')
        self.user.set_password('bob-is-the-greatest')
        self.user.api_key = secrets.token_urlsafe(32)
        self.user.save()

        # Create superuser
        self.superuser = User.objects.create(username='superbob', email='superbob@example.com')
        self.superuser.set_password('superbob-is-the-greatest')
        self.superuser.api_key = secrets.token_urlsafe(32)
        self.superuser.is_superuser = True
        self.superuser.save()

        # Create running report
        self.analysis1 = FirmwareAnalysis.objects.create(user=self.user)

        # Create successful report without zip (regular user's)
        self.analysis2 = FirmwareAnalysis.objects.create(user=self.user, finished=True)

        # Create successful report with zip (regular user's)
        zip_file = LogZipFile.objects.create(user=self.user, file='/tmp/testfile')
        self.analysis3 = FirmwareAnalysis.objects.create(
            user=self.user,
            finished=True,
            zip_file=zip_file,
            duration='0:00:00.0'
        )

        # Create failed report (superuser's)
        self.analysis4 = FirmwareAnalysis.objects.create(
            user=self.superuser,
            finished=True,
            failed=True
        )

    def test_running_report(self):
        response = self.client.get(
            f'/status_report/{self.analysis1.id}',
            {'api_key': self.user.api_key}
        )
        self.assertEqual(response.status_code, HTTPStatus.ACCEPTED)
        self.assertEqual(response.json()['status'], 'running')

    def test_successful_report_no_zip(self):
        response = self.client.get(
            f'/status_report/{self.analysis2.id}',
            {'api_key': self.user.api_key}
        )
        self.assertEqual(response.status_code, HTTPStatus.CREATED)
        self.assertEqual(response.json()['status'], 'finished')

    def test_successful_report_with_zip(self):
        response = self.client.get(
            f'/status_report/{self.analysis3.id}',
            {'api_key': self.user.api_key}
        )
        response_json = response.json()

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(response_json['status'], 'finished')
        self.assertIn('download_url', response_json)

    def test_failed_report(self):
        response = self.client.get(
            f'/status_report/{self.analysis4.id}',
            {'api_key': self.superuser.api_key}
        )
        self.assertEqual(response.json()['status'], 'failed')

    def test_superuser_access(self):
        """
        Access to different user's analysis should be granted to the superuser
        """
        response = self.client.get(
            f'/status_report/{self.analysis3.id}',
            {'api_key': self.superuser.api_key}
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_regular_user_access(self):
        """
        Access to a different user's analysis should be denied
        """
        response = self.client.get(
            f'/status_report/{self.analysis4.id}',
            {'api_key': self.user.api_key}
        )
        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)
        self.assertEqual(response.json()['status'], 'forbidden')

    def test_invalid_api_key(self):
        response = self.client.get(
            f'/status_report/{self.analysis1.id}',
            {'api_key': 'wrong'}
        )
        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)

    def test_invalid_analysis_id(self):
        response = self.client.get(
            '/status_report/invalid',
            {'api_key': self.user.api_key}
        )
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
