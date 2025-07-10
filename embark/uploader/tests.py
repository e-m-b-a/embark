__copyright__ = 'Copyright 2021-2025 Siemens Energy AG, Copyright 2025 The AMOS Projects'
__author__ = 'SirGankalot, ClProsser'
__license__ = 'MIT'

import secrets
import os

from unittest.mock import patch

from rest_framework.test import APIClient
from rest_framework.test import APITestCase
from rest_framework import status

from users.models import User


BASE_URL = "/api/uploader/"


class TestUploader(APITestCase):
    def setUp(self):
        user = User.objects.create(username='testuser')
        user.api_key = secrets.token_urlsafe(32)
        user.save()

        self.client = APIClient()  # pylint: disable=attribute-defined-outside-init
        self.client.credentials(HTTP_AUTHORIZATION=user.api_key)

    def test_uploader__not_authenticated(self):
        """
        Test that the API returns 401 when not authenticated.:

        """
        client = APIClient()
        response = client.post(BASE_URL, {})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_uploader__invalid_parameters(self):
        """
        Test that the API returns 400 when nothing is provided.:

        """
        response = self.client.post(BASE_URL, {})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data, {'status': 'error', 'message': 'No file provided or wrong key'})

    def test_uploader__invalid_file(self):
        """
        Test that the API returns 400 when a non file object is provided.:

        """
        response = self.client.post(BASE_URL, {"file": "abc"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data, {'status': 'error', 'message': 'Invalid file provided'})

    @patch("uploader.executor.submit_firmware")
    def test_uploader__successful_queue(self, mock):
        """
        Test that the API returns 200 when a file and valid api key is provided.:

        """
        mock.return_value = True

        file_name = "dummy.txt"
        with open(file_name, 'w+', encoding='utf-8') as file:
            pass

        with open(file_name, 'r', encoding='utf-8') as file:
            response = self.client.post(BASE_URL, {"file": file})

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["status"], 'success')
        self.assertEqual(len(str(response.data["id"])), 36)

        os.remove(file_name)
