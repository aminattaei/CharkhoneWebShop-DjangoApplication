import hashlib
import re
from contextlib import contextmanager
from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core import mail
from django.core.signing import SignatureExpired
from django.test import TestCase, override_settings
from django.urls import reverse

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
    build_verification_link,
    generate_verification_token,
    mark_verification_token_used,
    send_verification_email,
    verify_verification_token,
)
from accounts.services.verification import signer as verification_signer

User = get_user_model()

LOCMEM = "django.core.mail.backends.locmem.EmailBackend"


def swap_middle_character(token):
    """Flip one character in the middle of a token without knowing its layout."""
    middle = len(token) // 2
    replacement = "a" if token[middle] != "a" else "b"
    return token[:middle] + replacement + token[middle + 1 :]


def extract_token_from_email():
    """Pull the token out of the verification link in the last sent email."""
    body = mail.outbox[-1].body
    match = re.search(r"token=([^\s]+)", body)
    assert match, "verification link not found in the email body"
    return match.group(1)


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
        candidates = {
            "appended": self.token + "x",
            "swapped middle": swap_middle_character(self.token),
            "truncated": self.token[:-1],
        }

        for label, candidate in candidates.items():
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

    # 1. a newly generated token is valid
    def test_token_is_valid_immediately_after_creation(self):
        self.assertEqual(verify_verification_token(self.token), self.user.id)

    # 2. the token identifies the user it was issued for
    def test_token_verifies_the_issuing_user_only(self):
        other = User.objects.create_user(
            email="other@example.com", password="testpass123"
        )

        self.assertEqual(verify_verification_token(self.token), self.user.id)
        self.assertNotEqual(verify_verification_token(self.token), other.id)

    # 3. a token issued for one user cannot verify another user
    def test_user_a_token_cannot_verify_user_b(self):
        user_b = User.objects.create_user(
            email="b@example.com", password="testpass123"
        )
        token_for_a = generate_verification_token(user_b)

        verified_id = verify_verification_token(token_for_a)

        self.assertEqual(verified_id, user_b.id)
        self.assertNotEqual(verified_id, self.user.id)
        # Verifying A must leave both users untouched.
        self.assertFalse(self.user.is_verified)
        self.assertFalse(user_b.is_verified)

    # 4. the token stays valid before the 12 hour window closes
    def test_token_remains_valid_just_before_12_hours(self):
        moment = self.row.created_at + timedelta(hours=11, minutes=59)

        with time_travelled_to(moment):
            user_id = verify_verification_token(self.token)

        self.assertEqual(user_id, self.user.id)

    # 5. boundary: at exactly 12 hours the token is already invalid
    def test_token_is_invalid_at_exactly_12_hours(self):
        moment = self.row.created_at + timedelta(hours=12)

        with time_travelled_to(moment):
            self.assertIsNone(verify_verification_token(self.token))

    def test_stored_row_is_no_longer_valid_at_exactly_12_hours(self):
        with time_travelled_to(self.row.created_at + timedelta(hours=12)):
            self.assertFalse(self.row.is_valid())

    def test_signature_age_check_rejects_at_12_hours(self):
        # The signer expires a token when age > max_age, and the embedded
        # timestamp is truncated to whole seconds, so a token that has reached
        # 12 hours is past the allowed age.
        with time_travelled_to(self.row.created_at + timedelta(hours=12)):
            with self.assertRaises(SignatureExpired):
                verification_signer.unsign(self.token, max_age=VERIFICATION_MAX_AGE)

    # 6. the token is invalid after 12 hours
    def test_token_is_invalid_after_12_hours(self):
        for delta in (
            timedelta(hours=12, seconds=1),
            timedelta(hours=13),
            timedelta(days=8),
        ):
            with self.subTest(delta=delta):
                with time_travelled_to(self.row.created_at + delta):
                    self.assertIsNone(verify_verification_token(self.token))

    # 7. stored expiration is approximately 12 hours after creation
    def test_stored_expiration_is_approximately_12_hours(self):
        self.assertEqual(VERIFICATION_MAX_AGE, 12 * 3600)
        self.assertAlmostEqual(
            self.row.expires_at,
            self.row.created_at + timedelta(hours=12),
            delta=timedelta(seconds=5),
        )

    # 8. a used token is rejected
    def test_used_token_is_rejected(self):
        self.assertTrue(mark_verification_token_used(self.token))

        self.assertIsNone(verify_verification_token(self.token))

    def test_marking_already_used_token_returns_false(self):
        self.assertTrue(mark_verification_token_used(self.token))
        self.assertFalse(mark_verification_token_used(self.token))

    def test_token_is_single_use(self):
        self.assertEqual(verify_verification_token(self.token), self.user.id)
        mark_verification_token_used(self.token)

        self.assertIsNone(verify_verification_token(self.token))

    # 9. tampered tokens are rejected
    def test_tampered_token_is_rejected(self):
        candidates = {
            "appended": self.token + "x",
            "swapped middle": swap_middle_character(self.token),
            "truncated": self.token[:-1],
        }

        for label, candidate in candidates.items():
            with self.subTest(tampering=label):
                self.assertIsNone(verify_verification_token(candidate))

    # 10. random tokens are rejected
    def test_random_token_is_rejected(self):
        candidates = (
            "",
            "not-a-token",
            "verify:1:20260101000000",
            hashlib.sha256(b"guess").hexdigest(),
        )

        for candidate in candidates:
            with self.subTest(candidate=candidate):
                self.assertIsNone(verify_verification_token(candidate))

    # 11. the database stores only a one way hash of the token
    def test_database_stores_only_a_hash_of_the_token(self):
        stored = self.row.token_hash

        self.assertNotEqual(stored, self.token)
        self.assertEqual(len(stored), 64)
        self.assertTrue(all(c in "0123456789abcdef" for c in stored))

        # The raw payload the token carries is not recoverable from the row.
        raw_payload = verification_signer.unsign(self.token)
        self.assertNotIn(raw_payload, stored)

        # A bare stored hash is not a usable credential on its own.
        self.assertIsNone(verify_verification_token(stored))

        # Yet the emailed token still works through the public API.
        self.assertEqual(verify_verification_token(self.token), self.user.id)

    # 12. superseding behaviour is unchanged
    def test_new_token_invalidates_previous_unused_tokens(self):
        first = generate_verification_token(self.user)
        second = generate_verification_token(self.user)

        self.assertIsNone(verify_verification_token(first))
        self.assertEqual(verify_verification_token(second), self.user.id)


@override_settings(EMAIL_BACKEND=LOCMEM)
class EmailedVerificationTokenTests(TestCase):
    """The token a user actually receives must be the one that verifies them.

    Creating a User no longer sends a verification email on its own; the
    registration flow does it explicitly, so these tests issue the token the
    same way that flow does.
    """

    def _register_like_signup(self, email):
        """Create a user and send its verification email through the services."""
        user = User.objects.create_user(email=email, password="testpass123")
        link = build_verification_link(
            None, generate_verification_token(user)
        )
        send_verification_email(user, link)
        return user, extract_token_from_email()

    def test_token_from_the_sent_email_verifies_the_user(self):
        user, emailed_token = self._register_like_signup("emailed@example.com")
        row = EmailVerificationToken.objects.get(user=user, is_used=False)

        # The emailed token is the real credential, not the stored hash.
        self.assertNotEqual(row.token_hash, emailed_token)
        self.assertEqual(verify_verification_token(emailed_token), user.id)

        response = self.client.get(
            reverse("accounts:verify-email-confirm"), {"token": emailed_token}
        )

        self.assertEqual(response.status_code, 302)
        user.refresh_from_db()
        self.assertTrue(user.is_verified)
        self.assertTrue(
            EmailVerificationToken.objects.get(user=user).is_used,
            "confirming the email must consume the token",
        )

    def test_emailed_token_cannot_be_replayed_after_confirmation(self):
        self._register_like_signup("replay@example.com")
        emailed_token = extract_token_from_email()
        url = reverse("accounts:verify-email-confirm")

        self.client.get(url, {"token": emailed_token})
        replay = self.client.get(url, {"token": emailed_token})

        self.assertEqual(replay.status_code, 302)
        self.assertTrue(
            EmailVerificationToken.objects.get(
                user__email="replay@example.com"
            ).is_used,
            "replaying a confirmation must not change the consumed token",
        )

    def test_tampered_emailed_token_does_not_verify_the_user(self):
        user, emailed_token = self._register_like_signup("tampered@example.com")

        response = self.client.get(
            reverse("accounts:verify-email-confirm"),
            {"token": swap_middle_character(emailed_token)},
        )

        self.assertEqual(response.status_code, 302)
        user.refresh_from_db()
        self.assertFalse(user.is_verified)
        self.assertFalse(
            EmailVerificationToken.objects.get(user=user).is_used,
            "a rejected token must stay unused",
        )