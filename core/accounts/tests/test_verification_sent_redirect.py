"""Regression tests for the verification "email sent" redirect.

Both verification flows redirected to "accounts:verify_email_sent" while the
URL pattern is registered as "verify-email-sent", so every POST raised
NoReverseMatch and returned HTTP 500 after the email had already been sent.
"""

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import NoReverseMatch, reverse

User = get_user_model()

LOCMEM = "django.core.mail.backends.locmem.EmailBackend"
REQUEST_VERIFICATION_URL = reverse("accounts:verify-email")
RESEND_VERIFICATION_URL = reverse("accounts:verify-email-sent")
EXPECTED_REDIRECT_URL = reverse("accounts:verify-email-sent")


@override_settings(EMAIL_BACKEND=LOCMEM)
class VerificationSentRedirectTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="someone@example.com", password="testpass123"
        )
        # Cleared after user creation so only emails sent by the view under
        # test are counted.
        mail.outbox = []

    # the URL name used by the views must actually resolve
    def test_underscored_url_name_does_not_exist(self):
        # Guards the original defect: this name was never registered.
        with self.assertRaises(NoReverseMatch):
            reverse("accounts:verify_email_sent")

    def test_hyphenated_url_name_resolves_to_the_sent_page(self):
        self.assertEqual(reverse("accounts:verify-email-sent"), EXPECTED_REDIRECT_URL)
        self.assertEqual(EXPECTED_REDIRECT_URL, "/accounts/verify-email/sent/")

    # RequestVerificationView.post
    def test_request_verification_redirects_to_sent_page(self):
        response = self.client.post(
            REQUEST_VERIFICATION_URL, {"email": self.user.email}
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], EXPECTED_REDIRECT_URL)
        self.assertEqual(len(mail.outbox), 1)

    def test_request_verification_redirects_for_unknown_email(self):
        response = self.client.post(
            REQUEST_VERIFICATION_URL, {"email": "nobody@example.com"}
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], EXPECTED_REDIRECT_URL)

    def test_request_verification_redirects_when_email_field_is_blank(self):
        response = self.client.post(REQUEST_VERIFICATION_URL, {"email": "  "})

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "NoReverseMatch", status_code=200)

    # ResendVerificationView.post
    def test_resend_verification_redirects_to_sent_page(self):
        response = self.client.post(
            RESEND_VERIFICATION_URL, {"email": self.user.email}
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], EXPECTED_REDIRECT_URL)
        self.assertEqual(len(mail.outbox), 1)

    def test_resend_verification_redirects_for_unknown_email(self):
        response = self.client.post(
            RESEND_VERIFICATION_URL, {"email": "nobody@example.com"}
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], EXPECTED_REDIRECT_URL)

    def test_resend_verification_redirects_when_email_field_is_blank(self):
        response = self.client.post(RESEND_VERIFICATION_URL, {"email": ""})

        self.assertEqual(response.status_code, 200)

    # both flows stay quiet for an already verified account
    def test_no_email_but_successful_redirect_for_verified_account(self):
        self.user.is_verified = True
        self.user.save()

        for url in (REQUEST_VERIFICATION_URL, RESEND_VERIFICATION_URL):
            with self.subTest(url=url):
                response = self.client.post(url, {"email": self.user.email})

                self.assertEqual(response.status_code, 302)
                self.assertEqual(response["Location"], EXPECTED_REDIRECT_URL)

        self.assertEqual(len(mail.outbox), 0)