"""Regression tests for atomic consumption of password reset tokens.

The reset API used to change the password and only then call
``mark_token_used``, ignoring whether the claim succeeded. Two concurrent
requests carrying the same token could therefore both change the password and
both report success.
"""

import threading
import unittest
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.db import connection
from django.test import TestCase, TransactionTestCase
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import PasswordResetToken
from accounts.services import complete_password_reset, generate_reset_token
from accounts.services.password_reset import PasswordResetResult
from accounts.services.tokens import claim_reset_token

User = get_user_model()

RESET_URL = "/accounts/api/v1/reset-password/"


def raw_token_of(token):
    from accounts.services.tokens import signer

    return signer.unsign(token)


class PasswordResetSuccessTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email="test@example.com", password="oldpass123"
        )

    # 1. normal valid reset
    def test_valid_token_resets_password_and_consumes_token(self):
        token = generate_reset_token(self.user)

        response = self.client.post(
            RESET_URL,
            {"token": token, "new_password": "newpass1234"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("newpass1234"))
        self.assertFalse(
            PasswordResetToken.objects.get(user=self.user, is_used=True).is_valid()
        )

    def test_valid_token_resets_failed_reset_attempts(self):
        self.user.failed_reset_attempts = 3
        self.user.save()
        token = generate_reset_token(self.user)

        self.client.post(
            RESET_URL,
            {"token": token, "new_password": "newpass1234"},
            format="json",
        )

        self.user.refresh_from_db()
        self.assertEqual(self.user.failed_reset_attempts, 0)

    # 2. invalid token
    def test_invalid_token_is_rejected_and_password_unchanged(self):
        generate_reset_token(self.user)

        response = self.client.post(
            RESET_URL,
            {"token": "invalid-token", "new_password": "newpass1234"},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("نامعتبر", response.data["detail"])
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("oldpass123"))

    # 3. expired token
    def test_expired_token_is_rejected_and_password_unchanged(self):
        token = generate_reset_token(self.user)
        PasswordResetToken.objects.filter(user=self.user).update(
            expires_at=timezone.now() - timezone.timedelta(minutes=1)
        )

        response = self.client.post(
            RESET_URL,
            {"token": token, "new_password": "newpass1234"},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("منقضی", response.data["detail"])
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("oldpass123"))

    # 4. already used token
    def test_already_used_token_is_rejected(self):
        token = generate_reset_token(self.user)
        self.client.post(
            RESET_URL,
            {"token": token, "new_password": "firstpass123"},
            format="json",
        )

        response = self.client.post(
            RESET_URL,
            {"token": token, "new_password": "secondpass12"},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn(
            response.data["detail"],
            ("توکن نامعتبر یا منقضی شده است.", "توکن قبلاً استفاده شده است."),
        )
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("firstpass123"))

    # 5. a token is consumable exactly once
    def test_token_can_only_be_consumed_once(self):
        token = generate_reset_token(self.user)

        first = complete_password_reset(token, "firstpass123")
        second = complete_password_reset(token, "secondpass12")

        self.assertTrue(first.ok)
        self.assertFalse(second.ok)
        self.assertEqual(second.status_code, 400)
        self.assertEqual(
            PasswordResetToken.objects.filter(user=self.user, is_used=True).count(), 1
        )

    def test_claim_reset_token_succeeds_only_once(self):
        token = generate_reset_token(self.user)

        self.assertEqual(claim_reset_token(token), self.user.id)
        self.assertIsNone(claim_reset_token(token))

    def test_locked_account_is_rejected_without_consuming_token(self):
        token = generate_reset_token(self.user)
        self.user.is_locked = True
        self.user.save()

        response = self.client.post(
            RESET_URL,
            {"token": token, "new_password": "newpass1234"},
            format="json",
        )

        self.assertEqual(response.status_code, 403)
        self.assertFalse(
            PasswordResetToken.objects.get(user=self.user).is_used,
            "a locked account must not burn the reset token",
        )

    # 8. a failed password update must not consume the token
    def test_failed_password_update_rolls_back_token_consumption(self):
        token = generate_reset_token(self.user)

        with unittest.mock.patch.object(User, "save", side_effect=RuntimeError("db")):
            with self.assertRaises(RuntimeError):
                complete_password_reset(token, "newpass1234")

        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("oldpass123"))
        self.assertFalse(
            PasswordResetToken.objects.get(user=self.user).is_used,
            "token must return to unused when the password update fails",
        )

        retry = complete_password_reset(token, "newpass1234")
        self.assertTrue(retry.ok)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("newpass1234"))


class ResetEndpointDelegationTests(TestCase):
    """The endpoint must not change a password outside the atomic service.

    Without this the view could set the password first and ignore whether the
    token claim succeeded, which is the race this fix removes. The behavioural
    proof is the threaded test below, which needs PostgreSQL row locking.
    """

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email="delegate@example.com", password="oldpass123"
        )

    @patch("accounts.api.v1.views.complete_password_reset")
    def test_endpoint_delegates_to_atomic_service(self, mock_complete):
        mock_complete.return_value = PasswordResetResult(
            ok=False,
            status_code=400,
            detail="توکن قبلاً استفاده شده است.",
        )

        response = self.client.post(
            RESET_URL,
            {"token": "some-token", "new_password": "newpass1234"},
            format="json",
        )

        mock_complete.assert_called_once_with("some-token", "newpass1234")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["detail"], "توکن قبلاً استفاده شده است.")

    @patch("accounts.api.v1.views.complete_password_reset")
    def test_endpoint_reports_success_from_service_result(self, mock_complete):
        mock_complete.return_value = PasswordResetResult(
            ok=True,
            status_code=200,
            detail="رمز عبور با موفقیت تغییر کرد.",
        )

        response = self.client.post(
            RESET_URL,
            {"token": "some-token", "new_password": "newpass1234"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["detail"], "رمز عبور با موفقیت تغییر کرد.")


class ConcurrentPasswordResetTests(TransactionTestCase):
    """Real thread interleaving, which requires SELECT FOR UPDATE support."""

    reset_sequences = True

    def setUp(self):
        self.user = User.objects.create_user(
            email="race@example.com", password="oldpass123"
        )

    @unittest.skipUnless(
        connection.features.has_select_for_update,
        "requires a backend with SELECT FOR UPDATE support",
    )
    def test_concurrent_resets_of_same_token_only_one_succeeds(self):
        token = generate_reset_token(self.user)
        passwords = ("firstpass123", "secondpass12")
        barrier = threading.Barrier(len(passwords))
        results = {}
        lock = threading.Lock()

        def attempt(password):
            barrier.wait(timeout=10)
            result = complete_password_reset(token, password)
            with lock:
                results[password] = result

        threads = [
            threading.Thread(target=attempt, args=(password,))
            for password in passwords
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=20)

        succeeded = [p for p, r in results.items() if r.ok]
        failed = [p for p, r in results.items() if not r.ok]
        self.assertEqual(len(results), len(passwords), "both attempts must finish")
        self.assertEqual(len(succeeded), 1, f"exactly one attempt may succeed: {results}")
        self.assertEqual(len(failed), 1)

        self.user.refresh_from_db()
        winner, loser = succeeded[0], failed[0]
        self.assertTrue(self.user.check_password(winner))
        self.assertFalse(
            self.user.check_password(loser),
            "only the winning password may be valid after a race",
        )
        self.assertEqual(
            PasswordResetToken.objects.filter(user=self.user, is_used=True).count(), 1
        )