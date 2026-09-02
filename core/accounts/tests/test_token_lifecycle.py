import hashlib
import time
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone

from accounts.models import PasswordResetToken, EmailVerificationToken
from accounts.services.tokens import (
    generate_reset_token,
    verify_reset_token,
    mark_token_used,
    TOKEN_MAX_AGE,
)
from accounts.services.verification import (
    generate_verification_token,
    verify_verification_token,
    mark_verification_token_used,
    VERIFICATION_MAX_AGE,
)

User = get_user_model()


class PasswordResetTokenLifecycleTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="test@example.com", password="testpass123"
        )

    def test_token_is_valid_immediately_after_creation(self):
        token = generate_reset_token(self.user)
        user_id = verify_reset_token(token)
        self.assertEqual(user_id, self.user.id)

    def test_token_invalid_after_expiration(self):
        token = generate_reset_token(self.user)
        with patch("django.utils.timezone.now") as mock_now:
            mock_now.return_value = timezone.now() + timezone.timedelta(seconds=TOKEN_MAX_AGE + 100)
            user_id = verify_reset_token(token)
        self.assertIsNone(user_id)

    def test_token_can_be_marked_as_used(self):
        token = generate_reset_token(self.user)
        result = mark_token_used(token)
        self.assertTrue(result)
        user_id = verify_reset_token(token)
        self.assertIsNone(user_id)

    def test_marking_already_used_token_returns_false(self):
        token = generate_reset_token(self.user)
        mark_token_used(token)
        result = mark_token_used(token)
        self.assertFalse(result)

    def test_verify_invalid_token_returns_none(self):
        user_id = verify_reset_token("invalid-token")
        self.assertIsNone(user_id)

    def test_token_is_single_use(self):
        token = generate_reset_token(self.user)
        user_id = verify_reset_token(token)
        self.assertEqual(user_id, self.user.id)
        mark_token_used(token)
        user_id = verify_reset_token(token)
        self.assertIsNone(user_id)

    def test_new_token_invalidates_previous_unused_tokens(self):
        token1 = generate_reset_token(self.user)
        token2 = generate_reset_token(self.user)
        user_id = verify_reset_token(token1)
        self.assertIsNone(user_id)
        user_id = verify_reset_token(token2)
        self.assertEqual(user_id, self.user.id)

    def test_token_storage_uses_hash_not_raw_token(self):
        token = generate_reset_token(self.user)
        raw_token = token.split(":")[-1]
        stored_tokens = PasswordResetToken.objects.filter(user=self.user)
        for stored in stored_tokens:
            self.assertNotEqual(stored.token_hash, raw_token)
            self.assertEqual(len(stored.token_hash), 64)

    def test_token_expiry_is_48_hours(self):
        token = generate_reset_token(self.user)
        stored = PasswordResetToken.objects.get(token_hash__startswith=hashlib.sha256(token.encode()).hexdigest()[:16])
        expected_expiry = timezone.now() + timezone.timedelta(hours=48)
        self.assertAlmostEqual(stored.expires_at, expected_expiry, delta=timezone.timedelta(seconds=10))


class EmailVerificationTokenLifecycleTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="verify@example.com", password="testpass123"
        )

    def test_token_is_valid_immediately_after_creation(self):
        token = generate_verification_token(self.user)
        user_id = verify_verification_token(token)
        self.assertEqual(user_id, self.user.id)

    def test_token_invalid_after_expiration(self):
        token = generate_verification_token(self.user)
        with patch("django.utils.timezone.now") as mock_now:
            mock_now.return_value = timezone.now() + timezone.timedelta(seconds=VERIFICATION_MAX_AGE + 100)
            user_id = verify_verification_token(token)
        self.assertIsNone(user_id)

    def test_token_can_be_marked_as_used(self):
        token = generate_verification_token(self.user)
        result = mark_verification_token_used(token)
        self.assertTrue(result)
        user_id = verify_verification_token(token)
        self.assertIsNone(user_id)

    def test_marking_already_used_token_returns_false(self):
        token = generate_verification_token(self.user)
        mark_verification_token_used(token)
        result = mark_verification_token_used(token)
        self.assertFalse(result)

    def test_verify_invalid_token_returns_none(self):
        user_id = verify_verification_token("invalid-token")
        self.assertIsNone(user_id)

    def test_token_is_single_use(self):
        token = generate_verification_token(self.user)
        user_id = verify_verification_token(token)
        self.assertEqual(user_id, self.user.id)
        mark_verification_token_used(token)
        user_id = verify_verification_token(token)
        self.assertIsNone(user_id)

    def test_new_token_invalidates_previous_unused_tokens(self):
        token1 = generate_verification_token(self.user)
        token2 = generate_verification_token(self.user)
        user_id = verify_verification_token(token1)
        self.assertIsNone(user_id)
        user_id = verify_verification_token(token2)
        self.assertEqual(user_id, self.user.id)

    def test_token_expiry_is_12_hours(self):
        token = generate_verification_token(self.user)
        raw_token = token.split(":")[1] if ":" in token else token
        stored = EmailVerificationToken.objects.get(token_hash__startswith=hashlib.sha256(raw_token.encode()).hexdigest()[:16])
        expected_expiry = timezone.now() + timezone.timedelta(hours=12)
        self.assertAlmostEqual(stored.expires_at, expected_expiry, delta=timezone.timedelta(seconds=10))