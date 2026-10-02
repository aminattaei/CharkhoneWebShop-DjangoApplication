"""Error-handling contract for verification email delivery.

``send_verification_email`` used to wrap the whole send in ``except Exception``
and return a boolean. Two consequences followed from that:

* a programming error such as ``TypeError`` was indistinguishable from a mail
  server outage, so a real bug looked like a transient delivery problem and its
  traceback was discarded;
* the boolean was optional, and two of the three call sites ignored it, so a
  refused delivery still told the user the message was on its way.

Expected delivery failures now raise :class:`EmailDeliveryError`; everything
else propagates untouched.
"""

import smtplib
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.messages import get_messages
from django.core import mail
from django.core.exceptions import ImproperlyConfigured
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from accounts.models import EmailVerificationToken
from accounts.services import verification as verification_module
from accounts.services.verification import EmailDeliveryError, send_verification_email

User = get_user_model()

LOCMEM = "django.core.mail.backends.locmem.EmailBackend"
VALID_PASSWORD = "a/@1234567"
REQUEST_URL = reverse("accounts:verify-email")
RESEND_URL = reverse("accounts:verify-email-sent")
REGISTER_URL = reverse("accounts:register")
SEND_MAIL = "accounts.services.verification.send_mail"


def register(client, email="new@example.com", password=VALID_PASSWORD):
    return client.post(
        REGISTER_URL,
        {
            "email": email,
            "password": password,
            "password_confirmation": password,
            "privacy_agreed": "on",
        },
    )


@override_settings(EMAIL_BACKEND=LOCMEM)
class SuccessfulSendTests(TestCase):
    def setUp(self):
        mail.outbox = []
        self.user = User.objects.create_user(
            email="ok@example.com", password=VALID_PASSWORD
        )

    def test_successful_send_raises_nothing(self):
        self.assertIsNone(send_verification_email(self.user, "https://x.test/l"))

    def test_successful_send_delivers_one_message_to_the_user(self):
        send_verification_email(self.user, "https://x.test/l")

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["ok@example.com"])


@override_settings(EMAIL_BACKEND=LOCMEM)
class ExpectedDeliveryFailureTests(TestCase):
    """Failures that depend on the mail server, not on this code."""

    def setUp(self):
        mail.outbox = []
        self.user = User.objects.create_user(
            email="down@example.com", password=VALID_PASSWORD
        )

    def test_smtp_recipients_refused_raises_delivery_error(self):
        refusal = smtplib.SMTPRecipientsRefused({})
        with patch(SEND_MAIL, side_effect=refusal):
            with self.assertRaises(EmailDeliveryError) as ctx:
                send_verification_email(self.user, "https://x.test/l")

        self.assertIs(ctx.exception.__cause__, refusal)

    def test_smtp_server_disconnected_raises_delivery_error(self):
        with patch(SEND_MAIL, side_effect=smtplib.SMTPServerDisconnected("gone")):
            with self.assertRaises(EmailDeliveryError):
                send_verification_email(self.user, "https://x.test/l")

    def test_connection_refused_raises_delivery_error(self):
        # OSError covers the socket layer: refused, DNS failure, timeout.
        with patch(SEND_MAIL, side_effect=ConnectionRefusedError("no route")):
            with self.assertRaises(EmailDeliveryError):
                send_verification_email(self.user, "https://x.test/l")

    def test_timeout_raises_delivery_error(self):
        with patch(SEND_MAIL, side_effect=TimeoutError("timed out")):
            with self.assertRaises(EmailDeliveryError):
                send_verification_email(self.user, "https://x.test/l")

    def test_delivery_error_message_does_not_contain_the_link(self):
        link = "https://x.test/l?token=SUPERSECRETTOKEN"
        with patch(SEND_MAIL, side_effect=OSError("smtp down")):
            with self.assertRaises(EmailDeliveryError) as ctx:
                send_verification_email(self.user, link)

        self.assertNotIn("SUPERSECRETTOKEN", str(ctx.exception))
        self.assertNotIn("token=", str(ctx.exception))


@override_settings(EMAIL_BACKEND=LOCMEM)
class UnexpectedExceptionTests(TestCase):
    """Bugs and deployment problems must not masquerade as delivery failures."""

    def setUp(self):
        mail.outbox = []
        self.user = User.objects.create_user(
            email="bug@example.com", password=VALID_PASSWORD
        )

    def test_type_error_propagates_unwrapped(self):
        with patch(SEND_MAIL, side_effect=TypeError("unsupported operand")):
            with self.assertRaises(TypeError) as ctx:
                send_verification_email(self.user, "https://x.test/l")

        self.assertNotIsInstance(ctx.exception, EmailDeliveryError)

    def test_attribute_error_propagates_unwrapped(self):
        with patch(SEND_MAIL, side_effect=AttributeError("'NoneType' ...")):
            with self.assertRaises(AttributeError) as ctx:
                send_verification_email(self.user, "https://x.test/l")

        self.assertNotIsInstance(ctx.exception, EmailDeliveryError)

    def test_runtime_error_propagates_unwrapped(self):
        with patch(SEND_MAIL, side_effect=RuntimeError("mail layer blew up")):
            with self.assertRaises(RuntimeError) as ctx:
                send_verification_email(self.user, "https://x.test/l")

        self.assertNotIsInstance(ctx.exception, EmailDeliveryError)

    def test_misconfigured_backend_propagates(self):
        # A broken EMAIL_BACKEND is deterministic, not transient. Swallowing it
        # would keep a misconfigured deployment looking healthy indefinitely.
        with patch(
            SEND_MAIL, side_effect=ImproperlyConfigured("bad EMAIL_BACKEND")
        ):
            with self.assertRaises(ImproperlyConfigured) as ctx:
                send_verification_email(self.user, "https://x.test/l")

        self.assertNotIsInstance(ctx.exception, EmailDeliveryError)


@override_settings(EMAIL_BACKEND=LOCMEM)
class RegistrationWhenDeliveryFailsTests(TestCase):
    def setUp(self):
        mail.outbox = []

    @patch(SEND_MAIL, side_effect=smtplib.SMTPRecipientsRefused({}))
    def test_registration_still_creates_the_account(self, mock_send):
        register(self.client, "new@example.com")

        user = User.objects.get(email="new@example.com")
        self.assertTrue(user.check_password(VALID_PASSWORD))
        self.assertEqual(len(mail.outbox), 0)

    @patch(SEND_MAIL, side_effect=smtplib.SMTPRecipientsRefused({}))
    def test_failed_send_does_not_activate_the_account(self, mock_send):
        register(self.client, "new@example.com")

        user = User.objects.get(email="new@example.com")
        self.assertFalse(user.is_verified)
        self.assertIsNone(user.deactivated_at)

    @patch(SEND_MAIL, side_effect=smtplib.SMTPRecipientsRefused({}))
    def test_registration_stays_consistent_and_recoverable(self, mock_send):
        register(self.client, "new@example.com")

        user = User.objects.get(email="new@example.com")
        # exactly one unused token survives, so a later resend can still work
        tokens = EmailVerificationToken.objects.filter(user=user, is_used=False)
        self.assertEqual(tokens.count(), 1)

    @patch(SEND_MAIL, side_effect=smtplib.SMTPRecipientsRefused({}))
    def test_registration_warns_the_user_instead_of_claiming_success(
        self, mock_send
    ):
        response = register(self.client, "new@example.com")

        texts = [str(m) for m in get_messages(response.wsgi_request)]
        self.assertTrue(any("ارسال ایمیل تایید ممکن نشد" in t for t in texts))
        self.assertFalse(any("ایمیل خود را بررسی کنید" in t for t in texts))

    @patch(SEND_MAIL, side_effect=smtplib.SMTPRecipientsRefused({}))
    def test_registration_still_logs_the_user_in(self, mock_send):
        # Existing business rule, deliberately unchanged by this fix.
        register(self.client, "new@example.com")

        user = User.objects.get(email="new@example.com")
        self.assertEqual(
            int(self.client.session["_auth_user_id"]), user.pk
        )

    @patch(SEND_MAIL, side_effect=smtplib.SMTPRecipientsRefused({}))
    def test_no_duplicate_email_is_sent_when_delivery_fails(self, mock_send):
        register(self.client, "new@example.com")

        self.assertEqual(mock_send.call_count, 1)
        self.assertEqual(len(mail.outbox), 0)

    @patch(SEND_MAIL, side_effect=RuntimeError("mail layer blew up"))
    def test_unexpected_error_is_not_reported_as_a_delivery_problem(
        self, mock_send
    ):
        # The user is committed before the send, so an unexpected error leaves
        # the account in place and surfaces as a 500 rather than as a "your mail
        # probably did not send" message.
        with self.assertRaises(RuntimeError):
            register(self.client, "new@example.com")

        user = User.objects.get(email="new@example.com")
        self.assertFalse(user.is_verified)


@override_settings(EMAIL_BACKEND=LOCMEM)
class ResendWhenDeliveryFailsTests(TestCase):
    def setUp(self):
        mail.outbox = []
        self.user = User.objects.create_user(
            email="again@example.com", password=VALID_PASSWORD
        )

    @patch(SEND_MAIL, side_effect=smtplib.SMTPRecipientsRefused({}))
    def test_resend_does_not_crash_when_delivery_fails(self, mock_send):
        response = self.client.post(RESEND_URL, {"email": "again@example.com"})

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], RESEND_URL)
        self.assertEqual(len(mail.outbox), 0)

    @patch(SEND_MAIL, side_effect=smtplib.SMTPRecipientsRefused({}))
    def test_request_verification_does_not_crash_when_delivery_fails(
        self, mock_send
    ):
        response = self.client.post(REQUEST_URL, {"email": "again@example.com"})

        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(mail.outbox), 0)

    @patch(SEND_MAIL, side_effect=smtplib.SMTPRecipientsRefused({}))
    def test_failure_does_not_reveal_whether_the_account_exists(self, mock_send):
        # A fresh client per request, so queued messages from the first attempt
        # cannot leak into the second and mask a difference.
        registered = Client().post(RESEND_URL, {"email": "again@example.com"})
        unknown = Client().post(RESEND_URL, {"email": "nobody@example.com"})

        self.assertEqual(registered.status_code, unknown.status_code)
        self.assertEqual(registered["Location"], unknown["Location"])
        self.assertEqual(
            [str(m) for m in get_messages(registered.wsgi_request)],
            [str(m) for m in get_messages(unknown.wsgi_request)],
        )

    @patch(SEND_MAIL, side_effect=smtplib.SMTPRecipientsRefused({}))
    def test_failure_is_recorded_server_side(self, mock_send):
        with self.assertLogs("accounts.views.verification_views", level="WARNING"):
            self.client.post(RESEND_URL, {"email": "again@example.com"})

    @patch(SEND_MAIL, side_effect=smtplib.SMTPRecipientsRefused({}))
    def test_a_single_token_survives_a_failed_resend(self, mock_send):
        self.client.post(RESEND_URL, {"email": "again@example.com"})

        tokens = EmailVerificationToken.objects.filter(
            user=self.user, is_used=False
        )
        self.assertEqual(tokens.count(), 1)


@override_settings(EMAIL_BACKEND=LOCMEM)
class NoSensitiveDataInLogsTests(TestCase):
    def setUp(self):
        mail.outbox = []
        self.user = User.objects.create_user(
            email="leaky@example.com", password=VALID_PASSWORD
        )
        self.secret_link = "https://x.test/l?token=verify:1:20260101000000:abcdef"

    def test_log_does_not_contain_the_token(self):
        with patch(SEND_MAIL, side_effect=smtplib.SMTPRecipientsRefused({})):
            with self.assertLogs(verification_module.logger, level="DEBUG") as cap:
                with self.assertRaises(EmailDeliveryError):
                    send_verification_email(self.user, self.secret_link)

        output = "\n".join(cap.output)
        self.assertNotIn("abcdef", output)
        self.assertNotIn("verify:", output)
        self.assertNotIn("token=", output)

    def test_log_does_not_contain_the_password(self):
        with patch(SEND_MAIL, side_effect=smtplib.SMTPRecipientsRefused({})):
            with self.assertLogs(verification_module.logger, level="DEBUG") as cap:
                with self.assertRaises(EmailDeliveryError):
                    send_verification_email(self.user, self.secret_link)

        output = "\n".join(cap.output)
        self.assertNotIn(VALID_PASSWORD, output)
        self.assertNotIn(self.user.password, output)

    def test_failure_is_still_recorded(self):
        with patch(SEND_MAIL, side_effect=smtplib.SMTPRecipientsRefused({})):
            with self.assertLogs(verification_module.logger, level="ERROR") as cap:
                with self.assertRaises(EmailDeliveryError):
                    send_verification_email(self.user, self.secret_link)

        self.assertTrue(cap.output)
        self.assertIn("leaky@example.com", "\n".join(cap.output))
