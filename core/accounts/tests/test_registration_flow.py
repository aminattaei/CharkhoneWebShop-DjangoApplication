"""Regression tests for the registration and email-verification flow.

Creating a User used to trigger verification token generation and email sending
through a post_save signal. Registration therefore depended on a hidden side
effect, and a mail failure was swallowed while the user was still told to check
their inbox. Registration now orchestrates verification explicitly.
"""

from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core import mail
from django.db import transaction
from django.test import TestCase, TransactionTestCase, override_settings
from django.urls import reverse

from accounts.models import EmailVerificationToken
from accounts.services.verification import (
    VERIFICATION_MAX_AGE,
    build_verification_link,
    generate_verification_token,
    send_verification_email,
    verify_verification_token,
)

User = get_user_model()

LOCMEM = "django.core.mail.backends.locmem.EmailBackend"
REGISTER_URL = reverse("accounts:register")
VALID_PASSWORD = "a/@1234567"


def register(client, email="new@example.com", password=VALID_PASSWORD, **extra):
    data = {
        "email": email,
        "password": password,
        "password_confirmation": password,
        "privacy_agreed": "on",
    }
    data.update(extra)
    return client.post(REGISTER_URL, data, follow=False)


@override_settings(EMAIL_BACKEND=LOCMEM)
class RegistrationCreatesUserAndVerificationTests(TestCase):
    def setUp(self):
        mail.outbox = []

    # 1. registration creates the expected user
    def test_registration_creates_the_expected_user(self):
        register(self.client, "new@example.com")

        user = User.objects.get(email="new@example.com")
        self.assertTrue(user.check_password(VALID_PASSWORD))
        self.assertFalse(user.is_verified)
        self.assertTrue(user.is_active)
        # the customer profile is still created by the remaining post_save signal
        self.assertTrue(hasattr(user, "profile"))

    def test_registration_rejects_invalid_form_without_creating_anything(self):
        response = self.client.post(
            REGISTER_URL, {"email": "not-an-email", "password": "x"}
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(User.objects.count(), 0)
        self.assertEqual(EmailVerificationToken.objects.count(), 0)
        self.assertEqual(len(mail.outbox), 0)

    def test_registration_rejects_duplicate_email(self):
        User.objects.create_user(
            email="taken@example.com", password=VALID_PASSWORD
        )
        mail.outbox = []

        register(self.client, "taken@example.com")

        self.assertEqual(User.objects.filter(email="taken@example.com").count(), 1)
        self.assertEqual(len(mail.outbox), 0)

    # 2. a verification token is created correctly
    def test_registration_creates_one_usable_verification_token(self):
        register(self.client, "new@example.com")

        user = User.objects.get(email="new@example.com")
        rows = EmailVerificationToken.objects.filter(user=user, is_used=False)
        self.assertEqual(rows.count(), 1)

        row = rows.get()
        self.assertEqual(len(row.token_hash), 64)
        self.assertNotEqual(row.token_hash, user.email)
        # the 12 hour window is unchanged
        self.assertEqual(VERIFICATION_MAX_AGE, 12 * 3600)
        self.assertAlmostEqual(
            row.expires_at,
            row.created_at + timedelta(hours=12),
            delta=timedelta(seconds=5),
        )

    def test_emailed_token_verifies_the_new_user(self):
        register(self.client, "new@example.com")

        user = User.objects.get(email="new@example.com")
        token = extract_token_from_email()

        self.assertEqual(verify_verification_token(token), user.id)

    # 3. the verification email is attempted exactly once, at registration
    def test_registration_sends_exactly_one_verification_email(self):
        register(self.client, "new@example.com")

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["new@example.com"])
        self.assertIn("token=", mail.outbox[0].body)

    # 4. unrelated saves must not send another verification email
    def test_updating_the_user_does_not_send_another_email(self):
        register(self.client, "new@example.com")
        self.assertEqual(len(mail.outbox), 1)

        user = User.objects.get(email="new@example.com")
        user.first_name = "changed"
        user.last_reset_attempts = 3
        user.save()
        user.refresh_from_db()
        user.is_locked = True
        user.save()

        self.assertEqual(len(mail.outbox), 1, "no extra verification email expected")
        self.assertEqual(EmailVerificationToken.objects.filter(user=user).count(), 1)

    def test_creating_a_superuser_does_not_send_a_verification_email(self):
        mail.outbox = []

        User.objects.create_superuser(
            email="root@example.com", password=VALID_PASSWORD
        )

        self.assertEqual(len(mail.outbox), 0)
        self.assertEqual(EmailVerificationToken.objects.count(), 0)

    def test_bulk_creation_does_not_send_verification_emails(self):
        mail.outbox = []

        User.objects.bulk_create(
            [
                User(email="bulk1@example.com", password=VALID_PASSWORD),
                User(email="bulk2@example.com", password=VALID_PASSWORD),
            ]
        )

        self.assertEqual(len(mail.outbox), 0)
        self.assertEqual(EmailVerificationToken.objects.count(), 0)

    def test_duplicate_registration_is_rejected_without_new_token_or_email(self):
        register(self.client, "new@example.com")
        first_token = extract_token_from_email()
        mail.outbox = []

        response = register(self.client, "new@example.com")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(User.objects.filter(email="new@example.com").count(), 1)
        self.assertEqual(len(mail.outbox), 0)
        user = User.objects.get(email="new@example.com")
        self.assertEqual(
            EmailVerificationToken.objects.filter(user=user, is_used=False).count(), 1
        )
        # the token issued by the first registration is untouched
        self.assertEqual(verify_verification_token(first_token), user.id)

    # 5. an email failure is surfaced, not silently swallowed
    @patch(
        "accounts.services.verification.send_mail",
        side_effect=OSError("smtp down"),
    )
    def test_email_failure_still_registers_the_user(self, mock_send):
        register(self.client, "new@example.com")

        user = User.objects.get(email="new@example.com")
        self.assertTrue(user.check_password(VALID_PASSWORD))
        self.assertEqual(len(mail.outbox), 0)

    @patch(
        "accounts.services.verification.send_mail",
        side_effect=OSError("smtp down"),
    )
    def test_email_failure_keeps_a_recoverable_unused_token(self, mock_send):
        register(self.client, "new@example.com")

        user = User.objects.get(email="new@example.com")
        row = EmailVerificationToken.objects.get(user=user, is_used=False)
        self.assertFalse(row.is_used)
        # the account is not left in a verified state by a failed send
        self.assertFalse(user.is_verified)

    @patch(
        "accounts.services.verification.send_mail",
        side_effect=OSError("smtp down"),
    )
    def test_send_verification_email_reports_failure(self, mock_send):
        user = User.objects.create_user(
            email="resent@example.com", password=VALID_PASSWORD
        )

        sent = send_verification_email(user, "https://example.com/link")

        # assertIs, not assertFalse: returning None must not pass as a failure
        # signal, or the caller cannot tell "failed" from "no result".
        self.assertIs(sent, False)

    def test_send_verification_email_reports_success(self):
        user = User.objects.create_user(
            email="ok@example.com", password=VALID_PASSWORD
        )

        sent = send_verification_email(user, "https://example.com/link")

        self.assertIs(sent, True)
        self.assertEqual(len(mail.outbox), 1)

    @patch(
        "accounts.services.verification.send_mail",
        side_effect=OSError("smtp down"),
    )
    def test_user_can_still_receive_a_verification_email_after_a_failure(
        self, mock_send
    ):
        register(self.client, "new@example.com")
        user = User.objects.get(email="new@example.com")
        self.assertEqual(len(mail.outbox), 0)

        # a later attempt works once the mail backend recovers; the account was
        # never left in a state that blocks re-sending
        mock_send.side_effect = None
        resend_token = generate_verification_token(user)
        sent = send_verification_email(
            user, build_verification_link(None, resend_token)
        )

        self.assertTrue(sent)
        self.assertTrue(mock_send.called)
        self.assertEqual(verify_verification_token(resend_token), user.id)

    # 6. no password or token is ever written to the logs
    @patch(
        "accounts.services.verification.send_mail",
        side_effect=OSError("smtp down"),
    )
    def test_failure_logging_does_not_leak_password_or_token(self, mock_send):
        from accounts.services import verification as verification_module

        with self.assertLogs(verification_module.logger, level="DEBUG") as captured:
            register(self.client, "new@example.com")

        user = User.objects.get(email="new@example.com")
        row = EmailVerificationToken.objects.get(user=user, is_used=False)
        output = "\n".join(captured.output)

        self.assertNotIn(VALID_PASSWORD, output)
        self.assertNotIn(user.password, output)
        self.assertNotIn(row.token_hash, output)
        self.assertNotIn("verify:", output)

    def test_invalid_token_logging_does_not_leak_the_token(self):
        from accounts.services import verification as verification_module

        secret_looking_token = "verify:1:20260101000000:abcdef0123456789"

        with self.assertLogs(verification_module.logger, level="WARNING") as captured:
            self.assertIsNone(verify_verification_token(secret_looking_token))

        output = "\n".join(captured.output)
        self.assertNotIn(secret_looking_token, output)
        self.assertNotIn("20260101000000", output)
        # the rejection is still recorded, using a non-reversible fingerprint
        self.assertTrue(captured.output)


@override_settings(EMAIL_BACKEND=LOCMEM)
class RegistrationTransactionTests(TransactionTestCase):
    """The verification email must be attempted only after the commit."""

    reset_sequences = True

    def test_registration_commits_the_user_before_sending_the_email(self):
        observed = {}

        def observe(user, link):
            observed["user_pk"] = user.pk
            observed["emails_before_send"] = len(mail.outbox)
            raise RuntimeError("mail layer blew up")

        with patch(
            "accounts.views.account_views.send_verification_email", side_effect=observe
        ):
            with self.assertRaises(RuntimeError):
                register(self.client, "aftercommit@example.com")

        # The user and its token were committed before the send was attempted,
        # so a failure in the mail layer cannot roll back the registration.
        user = User.objects.get(email="aftercommit@example.com")
        self.assertEqual(observed["user_pk"], user.pk)
        self.assertEqual(observed["emails_before_send"], 0)
        self.assertEqual(
            EmailVerificationToken.objects.filter(user=user, is_used=False).count(), 1
        )

    def test_rolled_back_registration_leaves_no_user_and_no_token(self):
        with self.assertRaises(RuntimeError):
            with transaction.atomic():
                User.objects.create_user(
                    email="rolledback@example.com", password=VALID_PASSWORD
                )
                generate_verification_token(
                    User.objects.get(email="rolledback@example.com")
                )
                raise RuntimeError("boom")

        self.assertEqual(User.objects.filter(email="rolledback@example.com").count(), 0)
        self.assertEqual(EmailVerificationToken.objects.count(), 0)


def extract_token_from_email():
    import re

    body = mail.outbox[-1].body
    match = re.search(r"token=([^\s]+)", body)
    assert match, "verification link not found in the email body"
    return match.group(1)