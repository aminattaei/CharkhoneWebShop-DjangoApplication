import json
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import PasswordResetToken
from accounts.services import generate_reset_token

User = get_user_model()


class RequestPasswordResetTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email='test@example.com', password='testpass123'
        )

    @patch('accounts.views.send_reset_email')
    def test_request_reset_with_existing_email(self, mock_send_email):
        response = self.client.post(
            '/accounts/api/request-reset/',
            {'email': 'test@example.com'},
            format='json',
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn('detail', response.data)
        mock_send_email.assert_called_once()

    def test_request_reset_with_nonexistent_email(self):
        response = self.client.post(
            '/accounts/api/request-reset/',
            {'email': 'nonexistent@example.com'},
            format='json',
        )
        self.assertEqual(response.status_code, 200)


class ResetPasswordTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email='test@example.com', password='oldpass123'
        )

    def test_reset_with_invalid_token(self):
        response = self.client.post(
            '/accounts/api/reset-password/',
            {'token': 'invalid-token', 'new_password': 'newpass123'},
            format='json',
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn('نامعتبر', response.data['detail'])

    @patch('accounts.views.verify_reset_token')
    def test_reset_with_valid_token(self, mock_verify):
        mock_verify.return_value = self.user.id
        response = self.client.post(
            '/accounts/api/reset-password/',
            {'token': 'valid-token', 'new_password': 'newpass1234'},
            format='json',
        )
        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('newpass1234'))

    @patch('accounts.views.verify_reset_token')
    def test_reset_with_locked_account(self, mock_verify):
        mock_verify.return_value = self.user.id
        self.user.is_locked = True
        self.user.save()
        response = self.client.post(
            '/accounts/api/reset-password/',
            {'token': 'valid-token', 'new_password': 'newpass1234'},
            format='json',
        )
        self.assertEqual(response.status_code, 403)
        self.assertIn('قفل', response.data['detail'])
