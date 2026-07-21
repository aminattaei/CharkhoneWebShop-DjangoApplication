from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from datetime import timedelta

from accounts.models import PasswordResetToken
from accounts.utils import (
    generate_password_reset_token,
    verify_password_reset_token,
    mark_token_as_used,
)


class UsersManagersTests(TestCase):
    def test_create_user(self):
        User = get_user_model()
        user = User.objects.create_user(
            email="normal@user.com", password="a/@1234567"
        )
        self.assertEqual(user.email, "normal@user.com")
        self.assertTrue(user.is_active)
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        try:
            self.assertIsNone(user.username)
        except AttributeError:
            pass
        with self.assertRaises(TypeError):
            User.objects.create_user()
        with self.assertRaises(TypeError):
            User.objects.create_user(email="")
        with self.assertRaises(ValueError):
            User.objects.create_user(email="", password="a/@1234567")

    def test_create_superuser(self):
        User = get_user_model()
        admin_user = User.objects.create_superuser(
            email="super@user.com", password="a/@1234567"
        )
        self.assertEqual(admin_user.email, "super@user.com")
        self.assertTrue(admin_user.is_active)
        self.assertTrue(admin_user.is_staff)
        self.assertTrue(admin_user.is_superuser)
        try:
            self.assertIsNone(admin_user.username)
        except AttributeError:
            pass
        with self.assertRaises(ValueError):
            User.objects.create_superuser(
                email="super@user.com", password="foo", is_superuser=False
            )


class PasswordResetTokenTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            email="test@example.com", password="a/@1234567"
        )

    def test_generate_token(self):
        token = generate_password_reset_token(self.user)
        self.assertIsNotNone(token)
        self.assertEqual(PasswordResetToken.objects.count(), 1)
        db_token = PasswordResetToken.objects.first()
        self.assertEqual(db_token.user, self.user)
        self.assertFalse(db_token.is_used)

    def test_verify_valid_token(self):
        token = generate_password_reset_token(self.user)
        user_id = verify_password_reset_token(token)
        self.assertEqual(user_id, self.user.id)

    def test_verify_expired_token(self):
        token = generate_password_reset_token(self.user)
        db_token = PasswordResetToken.objects.first()
        db_token.expires_at = timezone.now() - timedelta(hours=1)
        db_token.save()
        user_id = verify_password_reset_token(token)
        self.assertIsNone(user_id)

    def test_verify_used_token(self):
        token = generate_password_reset_token(self.user)
        mark_token_as_used(token)
        user_id = verify_password_reset_token(token)
        self.assertIsNone(user_id)

    def test_verify_invalid_token(self):
        user_id = verify_password_reset_token("invalid.token.here")
        self.assertIsNone(user_id)

    def test_mark_token_as_used(self):
        token = generate_password_reset_token(self.user)
        mark_token_as_used(token)
        db_token = PasswordResetToken.objects.first()
        self.assertTrue(db_token.is_used)

    def test_new_token_deletes_old_unused(self):
        token1 = generate_password_reset_token(self.user)
        self.assertEqual(PasswordResetToken.objects.count(), 1)
        token2 = generate_password_reset_token(self.user)
        self.assertEqual(PasswordResetToken.objects.count(), 1)
        self.assertNotEqual(token1, token2)

    def test_password_reset_token_model_is_valid(self):
        db_token = PasswordResetToken.objects.create(
            user=self.user,
            token="test-token",
            expires_at=timezone.now() + timedelta(hours=48),
        )
        self.assertTrue(db_token.is_valid())

    def test_password_reset_token_model_is_expired(self):
        db_token = PasswordResetToken.objects.create(
            user=self.user,
            token="test-token",
            expires_at=timezone.now() - timedelta(hours=1),
        )
        self.assertFalse(db_token.is_valid())

    def test_password_reset_token_model_is_used(self):
        db_token = PasswordResetToken.objects.create(
            user=self.user,
            token="test-token",
            expires_at=timezone.now() + timedelta(hours=48),
            is_used=True,
        )
        self.assertFalse(db_token.is_valid())


class PasswordResetAPITests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            email="test@example.com", password="a/@1234567"
        )

    def test_request_reset_valid_email(self):
        response = self.client.post(
            '/accounts/request-reset/',
            {'email': 'test@example.com'},
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn('message', response.json())

    def test_request_reset_invalid_email(self):
        response = self.client.post(
            '/accounts/request-reset/',
            {'email': 'nonexistent@example.com'},
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)

    def test_request_reset_missing_email(self):
        response = self.client.post(
            '/accounts/request-reset/',
            {},
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 400)

    def test_reset_password_valid(self):
        token = generate_password_reset_token(self.user)
        response = self.client.post(
            '/accounts/reset-password/',
            {'token': token, 'new_password': 'NewP@ssw0rd123'},
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('NewP@ssw0rd123'))

    def test_reset_password_invalid_token(self):
        response = self.client.post(
            '/accounts/reset-password/',
            {'token': 'invalid', 'new_password': 'NewP@ssw0rd123'},
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 400)

    def test_reset_password_weak_password(self):
        token = generate_password_reset_token(self.user)
        response = self.client.post(
            '/accounts/reset-password/',
            {'token': token, 'new_password': '123'},
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 400)

    def test_reset_password_missing_fields(self):
        response = self.client.post(
            '/accounts/reset-password/',
            {},
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 400)
