import hashlib
from contextlib import contextmanager
from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.signing import SignatureExpired
from django.test import TestCase

from accounts.models import EmailVerificationToken, PasswordResetToken
from accounts.services.tokens import (
    TOKEN_MAX_AGE,
    generate_reset_token,
    mark_token_used,
    signer,
    verify_reset_token,
)
from accounts.services.verification import (
    VERIFICATION_MAX_AGE,
    generate_verification_token,
    mark_verification_token_used,
    verify_verification_token,
)

User = get_user_model()


@contextmanager
def time_travelled_to(moment):
    """Move both clocks the token lifecycle reads.

    A token expires when either the signing timestamp is older than the max age
    (compared against ``time.time()`` inside Django's signer) or the stored row
    passes ``is_valid()`` (which reads ``django.utils.timezone.now()``). Both
    have to move together to simulate a real point in time. No time-freezing
    library is available in this project, so both are patched.
    """
    with patch(
        "django.core.signing.time.time", return_value=moment.timestamp()
    ), patch("django.utils.timezone.now", return_value=moment):
        yield


class PasswordResetTokenLifecycleTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="test@example.com", password="testpass123"
        )
        self.token = generate_reset_token(self.user)
        self.row = PasswordResetToken.objects.get(user=self.user)

    # 1. a newly generated token is valid
    def test_token_is_valid_immediately_after_creation(self):
        self.assertEqual(verify_reset_token(self.token), self.user.id)

    # 2. the database never stores the usable token
    def test_stored_value_is_a_hash_and_not_the_token(self):
        stored = self.row.token_hash

        self.assertNotEqual(stored, self.token)
        self.assertEqual(len(stored), 64)
        self.assertTrue(all(c in "0123456789abcdef" for c in stored))
        # The token still works even though the raw token itself is not stored.
        self.assertEqual(verify_reset_token(self.token), self.user.id)

    # 3. the stored row is not a reusable credential on its own
    def test_stored_hash_does_not_verify_without_the_signed_token(self):
        self.assertIsNone(verify_reset_token(self.row.token_hash))

    # 4. stored expiration is approximately 48 hours after creation
    def test_stored_expiration_is_approximately_48_hours(self):
        self.assertAlmostEqual(
            self.row.expires_at,
            self.row.created_at + timedelta(hours=48),
            delta=timedelta(seconds=5),
        )

    def test_max_age_constant_is_48_hours(self):
        self.assertEqual(TOKEN_MAX_AGE, 48 * 3600)

    # 5. the token stays valid before the 48 hour window closes
    def test_token_remains_valid_just_before_48_hours(self):
        moment = self.row.created_at + timedelta(hours=47, minutes=59)

        with time_travelled_to(moment):
            user_id = verify_reset_token(self.token)

        self.assertEqual(user_id, self.user.id)

    def test_token_remains_valid_while_stored_row_is_valid(self):
        with time_travelled_to(self.row.created_at):
            self.assertTrue(self.row.is_valid())
            self.assertEqual(verify_reset_token(self.token), self.user.id)

    # 6. boundary: at exactly 48 hours the token is already invalid
    def test_token_is_invalid_at_exactly_48_hours(self):
        moment = self.row.created_at + timedelta(hours=48)

        with time_travelled_to(moment):
            self.assertIsNone(verify_reset_token(self.token))

    def test_stored_row_is_no_longer_valid_at_exactly_48_hours(self):
        with time_travelled_to(self.row.created_at + timedelta(hours=48)):
            self.assertFalse(self.row.is_valid())

    def test_signature_age_check_rejects_at_48_hours(self):
        # The signer treats max_age as exclusive (it expires when age > max_age),
        # and the stored timestamp is truncated to whole seconds, so a token
        # reaching 48 hours has an age of at least the max age.
        with time_travelled_to(self.row.created_at + timedelta(hours=48)):
            with self.assertRaises(SignatureExpired):
                signer.unsign(self.token, max_age=TOKEN_MAX_AGE)

    # 7. the token is invalid after 48 hours
    def test_token_is_invalid_after_48_hours(self):
        for delta in (
            timedelta(hours=48, seconds=1),
            timedelta(hours=49),
            timedelta(days=8),
        ):
            with self.subTest(delta=delta):
                with time_travelled_to(self.row.created_at + delta):
                    self.assertIsNone(verify_reset_token(self.token))

    # 8. a used token is invalid
    def test_used_token_is_invalid(self):
        self.assertTrue(mark_token_used(self.token))

        self.assertIsNone(verify_reset_token(self.token))

    def test_mark_token_used_returns_false_when_already_used(self):
        self.assertTrue(mark_token_used(self.token))
        self.assertFalse(mark_token_used(self.token))

    def test_token_is_single_use(self):
        self.assertEqual(verify_reset_token(self.token), self.user.id)
        mark_token_used(self.token)

        self.assertIsNone(verify_reset_token(self.token))

    # 9. tampered tokens are invalid
    def test_tampered_token_is_invalid(self):
        appended = self.token + "x"
        middle = len(self.token) // 2
        swapped = (
            self.token[:middle]
            + ("a" if self.token[middle] != "a" else "b")
            + self.token[middle + 1 :]
        )
        truncated = self.token[:-1]

        for label, candidate in (
            ("appended", appended),
            ("swapped middle", swapped),
            ("truncated", truncated),
        ):
            with self.subTest(tampering=label):
                self.assertIsNone(verify_reset_token(candidate))

    def test_random_token_is_invalid(self):
        for candidate in ("", "not-a-token", hashlib.sha256(b"x").hexdigest()):
            with self.subTest(candidate=candidate):
                self.assertIsNone(verify_reset_token(candidate))

    # 10. superseding behaviour is unchanged
    def test_new_token_invalidates_previous_unused_tokens(self):
        first = generate_reset_token(self.user)
        second = generate_reset_token(self.user)

        self.assertIsNone(verify_reset_token(first))
        self.assertEqual(verify_reset_token(second), self.user.id)


class EmailVerificationTokenLifecycleTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="verify@example.com", password="testpass123"
        )
        self.token = generate_verification_token(self.user)
        # Creating the user already issued one via the post_save signal; the row
        # for the token under test is the only one still unused.
        self.row = EmailVerificationToken.objects.get(
            user=self.user, is_used=False
        )

    def test_token_is_valid_immediately_after_creation(self):
        self.assertEqual(verify_verification_token(self.token), self.user.id)

    def test_stored_value_is_a_hash_and_not_the_token(self):
        self.assertNotEqual(self.row.token_hash, self.token)
        self.assertEqual(len(self.row.token_hash), 64)

    def test_stored_expiration_is_approximately_12_hours(self):
        self.assertEqual(VERIFICATION_MAX_AGE, 12 * 3600)
        self.assertAlmostEqual(
            self.row.expires_at,
            self.row.created_at + timedelta(hours=12),
            delta=timedelta(seconds=5),
        )

    def test_token_remains_valid_just_before_12_hours(self):
        with time_travelled_to(self.row.created_at + timedelta(hours=11, minutes=59)):
            self.assertEqual(verify_verification_token(self.token), self.user.id)

    def test_token_is_invalid_at_exactly_12_hours(self):
        with time_travelled_to(self.row.created_at + timedelta(hours=12)):
            self.assertIsNone(verify_verification_token(self.token))

    def test_token_is_invalid_after_12_hours(self):
        with time_travelled_to(self.row.created_at + timedelta(hours=13)):
            self.assertIsNone(verify_verification_token(self.token))

    def test_used_token_is_invalid(self):
        self.assertTrue(mark_verification_token_used(self.token))

        self.assertIsNone(verify_verification_token(self.token))

    def test_marking_already_used_token_returns_false(self):
        self.assertTrue(mark_verification_token_used(self.token))
        self.assertFalse(mark_verification_token_used(self.token))

    def test_token_is_single_use(self):
        self.assertEqual(verify_verification_token(self.token), self.user.id)
        mark_verification_token_used(self.token)

        self.assertIsNone(verify_verification_token(self.token))

    def test_tampered_token_is_invalid(self):
        self.assertIsNone(verify_verification_token(self.token + "x"))
        self.assertIsNone(verify_verification_token(self.token[:-1]))
        self.assertIsNone(verify_verification_token("not-a-token"))

    def test_new_token_invalidates_previous_unused_tokens(self):
        first = generate_verification_token(self.user)
        second = generate_verification_token(self.user)

        self.assertIsNone(verify_verification_token(first))
        self.assertEqual(verify_verification_token(second), self.user.id)