"""Regression tests for newsletter unsubscribe authorization.

Unsubscribing used to be authorized by an ``?email=`` parameter, so anyone who
knew a subscriber's address could cancel their subscription. Authorization now
requires a signed, time-limited token that carries only the subscriber pk.
"""

import re
import time
from unittest.mock import patch

from django.contrib import messages as django_messages
from django.core import mail
from django.core.signing import TimestampSigner, b62_encode
from django.test import TestCase, override_settings
from django.urls import reverse

from website.models import Newsletter, NewsletterRecipient, Subscriber
from website.services import NewsletterService
from website.unsubscribe_tokens import (
    UNSUBSCRIBE_SALT,
    UNSUBSCRIBE_TOKEN_MAX_AGE,
    build_unsubscribe_url,
    generate_unsubscribe_token,
    unsubscribe_token_subject,
)

LOCMEM = "django.core.mail.backends.locmem.EmailBackend"

MSG_INVALID_LINK = "لینک لغو اشتراک نامعتبر یا منقضی شده است."
MSG_UNSUBSCRIBED = "اشتراک شما با موفقیت لغو شد."
MSG_NO_ACTIVE = "اشتراک فعالی با این ایمیل پیدا نشد."


class AgedSigner(TimestampSigner):
    """Unsubscribe signer whose embedded timestamp is in the past."""

    def __init__(self, age_seconds):
        super().__init__(salt=UNSUBSCRIBE_SALT)
        self.age_seconds = age_seconds

    def timestamp(self):
        return b62_encode(int(time.time()) - self.age_seconds)


def messages_from(response):
    return [str(m) for m in django_messages.get_messages(response.wsgi_request)]


@override_settings(EMAIL_BACKEND=LOCMEM)
class UnsubscribeTokenTests(TestCase):
    def setUp(self):
        self.subscriber = Subscriber.objects.create(
            email="reader@example.com", is_active=True
        )
        self.other = Subscriber.objects.create(
            email="other@example.com", is_active=True
        )
        self.url = reverse("website:newsletter_unsubscribe")

    # 1. valid token works
    def test_valid_token_unsubscribes_subscriber(self):
        token = generate_unsubscribe_token(self.subscriber.pk)

        response = self.client.post(self.url, {"token": token})

        self.subscriber.refresh_from_db()
        self.assertEqual(response.status_code, 302)
        self.assertFalse(self.subscriber.is_active)
        self.assertIn(MSG_UNSUBSCRIBED, messages_from(response))

    def test_get_shows_confirmation_page_without_unsubscribing(self):
        token = generate_unsubscribe_token(self.subscriber.pk)

        response = self.client.get(self.url, {"token": token})

        self.subscriber.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "website/newsletter/unsubscribe.html")
        self.assertTrue(self.subscriber.is_active)

    # 2. invalid token fails
    def test_invalid_token_fails(self):
        response = self.client.post(self.url, {"token": "not-a-token"})

        self.subscriber.refresh_from_db()
        self.assertEqual(response.status_code, 302)
        self.assertTrue(self.subscriber.is_active)
        self.assertIn(MSG_INVALID_LINK, messages_from(response))

    def test_random_subscriber_id_without_signature_fails(self):
        response = self.client.post(self.url, {"token": str(self.subscriber.pk)})

        self.subscriber.refresh_from_db()
        self.assertTrue(self.subscriber.is_active)
        self.assertIn(MSG_INVALID_LINK, messages_from(response))

    def test_token_signed_with_foreign_salt_fails(self):
        foreign = TimestampSigner(salt="some-other-salt")
        token = foreign.sign(str(self.subscriber.pk))

        self.client.post(self.url, {"token": token})

        self.subscriber.refresh_from_db()
        self.assertTrue(self.subscriber.is_active)

    def test_missing_token_fails(self):
        response = self.client.post(self.url, {})

        self.subscriber.refresh_from_db()
        self.assertTrue(self.subscriber.is_active)
        self.assertIn(MSG_INVALID_LINK, messages_from(response))

    # 3. tampered token fails
    def test_tampered_token_fails(self):
        token = generate_unsubscribe_token(self.subscriber.pk)
        tampered = token[:-2] + ("ab" if not token.endswith("ab") else "cd")

        response = self.client.post(self.url, {"token": tampered})

        self.subscriber.refresh_from_db()
        self.assertTrue(self.subscriber.is_active)
        self.assertIn(MSG_INVALID_LINK, messages_from(response))

    # 4. expired token fails
    def test_expired_token_fails(self):
        aged = AgedSigner(UNSUBSCRIBE_TOKEN_MAX_AGE + 60)
        token = aged.sign(str(self.subscriber.pk))

        response = self.client.post(self.url, {"token": token})

        self.subscriber.refresh_from_db()
        self.assertTrue(self.subscriber.is_active)
        self.assertIn(MSG_INVALID_LINK, messages_from(response))

    def test_token_inside_max_age_is_accepted(self):
        fresh_enough = AgedSigner(UNSUBSCRIBE_TOKEN_MAX_AGE - 300)
        token = fresh_enough.sign(str(self.subscriber.pk))

        self.client.post(self.url, {"token": token})

        self.subscriber.refresh_from_db()
        self.assertFalse(self.subscriber.is_active)

    def test_get_with_expired_token_is_rejected(self):
        aged = AgedSigner(UNSUBSCRIBE_TOKEN_MAX_AGE + 60)
        token = aged.sign(str(self.subscriber.pk))

        response = self.client.get(self.url, {"token": token})

        self.assertEqual(response.status_code, 302)
        self.assertIn(MSG_INVALID_LINK, messages_from(response))

    # 5. token for A cannot unsubscribe B
    def test_token_for_one_subscriber_cannot_unsubscribe_another(self):
        token = generate_unsubscribe_token(self.other.pk)

        self.client.post(self.url, {"token": token})

        self.subscriber.refresh_from_db()
        self.other.refresh_from_db()
        self.assertTrue(self.subscriber.is_active)
        self.assertFalse(self.other.is_active)

    def test_client_supplied_subscriber_id_is_not_trusted(self):
        token = generate_unsubscribe_token(self.subscriber.pk)

        self.client.post(self.url, {"token": token, "subscriber_id": self.other.pk})

        self.other.refresh_from_db()
        self.assertTrue(self.other.is_active)

    # 6. the old email parameter can no longer unsubscribe anyone
    def test_plain_email_get_parameter_cannot_unsubscribe(self):
        response = self.client.get(self.url, {"email": self.subscriber.email})

        self.subscriber.refresh_from_db()
        self.assertEqual(response.status_code, 302)
        self.assertTrue(self.subscriber.is_active)
        self.assertIn(MSG_INVALID_LINK, messages_from(response))

    def test_plain_email_post_parameter_cannot_unsubscribe(self):
        response = self.client.post(self.url, {"email": self.subscriber.email})

        self.subscriber.refresh_from_db()
        self.assertTrue(self.subscriber.is_active)
        self.assertIn(MSG_INVALID_LINK, messages_from(response))

    def test_email_plus_valid_token_still_uses_the_token(self):
        token = generate_unsubscribe_token(self.other.pk)

        self.client.post(self.url, {"token": token, "email": self.subscriber.email})

        self.subscriber.refresh_from_db()
        self.other.refresh_from_db()
        self.assertTrue(self.subscriber.is_active)
        self.assertFalse(self.other.is_active)

    # 7. state changes on success
    def test_successful_unsubscribe_sets_state(self):
        from django.utils import timezone

        before = timezone.now()
        token = generate_unsubscribe_token(self.subscriber.pk)

        self.client.post(self.url, {"token": token})

        self.subscriber.refresh_from_db()
        self.assertFalse(self.subscriber.is_active)
        self.assertIsNotNone(self.subscriber.unsubscribed_at)
        self.assertGreaterEqual(self.subscriber.unsubscribed_at, before)
        self.assertLessEqual(self.subscriber.unsubscribed_at, timezone.now())

    # 8. repeated unsubscribe is safe
    def test_repeated_unsubscribe_is_safe(self):
        token = generate_unsubscribe_token(self.subscriber.pk)

        first = self.client.post(self.url, {"token": token})
        self.subscriber.refresh_from_db()
        first_stamp = self.subscriber.unsubscribed_at

        second = self.client.post(self.url, {"token": token})
        self.subscriber.refresh_from_db()

        self.assertFalse(self.subscriber.is_active)
        self.assertEqual(first_stamp, self.subscriber.unsubscribed_at)
        self.assertIn(MSG_UNSUBSCRIBED, messages_from(first))
        self.assertIn(MSG_NO_ACTIVE, messages_from(second))

    def test_unsubscribe_token_for_deleted_subscriber_is_handled(self):
        pk = self.subscriber.pk
        token = generate_unsubscribe_token(pk)
        Subscriber.objects.filter(pk=pk).delete()

        response = self.client.post(self.url, {"token": token})

        self.assertEqual(response.status_code, 302)
        self.assertIn(MSG_NO_ACTIVE, messages_from(response))

    # 9. email generation uses a token, never the raw email
    def test_unsubscribe_url_contains_token_and_not_email(self):
        url = build_unsubscribe_url(self.subscriber.pk)

        self.assertIn("token=", url)
        self.assertNotIn(self.subscriber.email, url)
        self.assertNotIn("email=", url)

    def test_generated_token_resolves_to_subscriber_pk(self):
        token = generate_unsubscribe_token(self.subscriber.pk)

        self.assertEqual(unsubscribe_token_subject(token), self.subscriber.pk)

    def test_newsletter_email_uses_token_link(self):
        newsletter = Newsletter.objects.create(
            subject="اخبار", preview_text="خلاصه", content="<p>متن</p>"
        )
        recipient = NewsletterRecipient.objects.create(
            newsletter=newsletter, subscriber=self.subscriber
        )

        NewsletterService._send_email(recipient)

        self.assertEqual(len(mail.outbox), 1)
        html_body = mail.outbox[0].alternatives[0][0]
        match = re.search(r"unsubscribe/\?token=([^\s\"'<>]+)", html_body)
        self.assertIsNotNone(match, "unsubscribe link not found in email HTML")
        token = match.group(1)

        self.assertNotIn(self.subscriber.email, token)
        self.assertNotIn("email=", token)
        self.assertEqual(unsubscribe_token_subject(token), self.subscriber.pk)

    def test_unsubscribe_token_does_not_leak_email(self):
        token = generate_unsubscribe_token(self.subscriber.pk)

        self.assertNotIn(self.subscriber.email, token)


class NewsletterEmailTemplatePathTests(TestCase):
    """Regression: _send_email must render the real template without stubbing."""

    @override_settings(EMAIL_BACKEND=LOCMEM)
    def test_send_email_renders_real_template_without_stubbing(self):
        subscriber = Subscriber.objects.create(
            email="render@example.com", is_active=True, is_verified=True
        )
        newsletter = Newsletter.objects.create(
            subject="اخبار", preview_text="خلاصه", content="<p>متن</p>"
        )
        recipient = NewsletterRecipient.objects.create(
            newsletter=newsletter, subscriber=subscriber
        )

        # No patch on render_to_string — the service must find the template
        # on its own.
        NewsletterService._send_email(recipient)

        self.assertEqual(len(mail.outbox), 1)
        body = mail.outbox[0].body
        self.assertIn(newsletter.subject, body)
        self.assertIn("Unsubscribe", body)