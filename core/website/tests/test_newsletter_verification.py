"""Regression tests for newsletter email verification token handling.

Bug under test: SubscribeView stored ``hash_token(signed_token)`` while
ConfirmSubscriptionView looked the subscriber up with ``hash_token(raw_token)``,
so the lookup could never match and verification always failed.
"""

import re
import time
from datetime import datetime

from django.contrib import messages as django_messages
from django.core import mail
from django.core.signing import TimestampSigner, b62_encode
from django.test import TestCase, override_settings

from website.models import Subscriber
from website.views import (
    NEWSLETTER_VERIFICATION_MAX_AGE,
    hash_token,
    signer,
)

LOCMEM = "django.core.mail.backends.locmem.EmailBackend"

MSG_INVALID_TOKEN = "توکن تایید نامعتبر یا منقضی شده است."
MSG_EMPTY_TOKEN = "توکن تایید نامعتبر است."
MSG_NOT_FOUND = "عضویت پیدا نشد."
MSG_VERIFIED = "عضویت شما در خبرنامه با موفقیت تایید شد."
MSG_ALREADY_VERIFIED = "عضویت شما قبلاً تایید شده است."


class AgedSigner(TimestampSigner):
    """Signer that produces tokens whose embedded timestamp is in the past.

    ``Signer.__init__`` derives its salt from the class module and name, so the
    salt must be pinned to the one used by ``website.views.signer`` for the
    generated tokens to be accepted by the view.
    """

    def __init__(self, age_seconds):
        super().__init__(salt="django.core.signing.TimestampSigner")
        self.age_seconds = age_seconds

    def timestamp(self):
        return b62_encode(int(time.time()) - self.age_seconds)


def make_signed_token(subscriber_pk, signed_by=None):
    raw_token = f"newsletter:{subscriber_pk}:{datetime.now().timestamp()}"
    active_signer = signed_by or signer
    return active_signer.sign(raw_token)


def extract_token_from_email():
    """Pull the signed token out of the verification link in the last email."""
    body = mail.outbox[-1].body
    match = re.search(r"token=([^\s]+)", body)
    assert match, "verification link not found in email body"
    return match.group(1)


@override_settings(EMAIL_BACKEND=LOCMEM)
class NewsletterVerificationTests(TestCase):
    def setUp(self):
        self.subscriber = Subscriber.objects.create(
            email="reader@example.com", is_active=True
        )
        self.other_subscriber = Subscriber.objects.create(
            email="someone-else@example.com", is_active=True
        )
        self.verify_url = "/newsletter/verify/"

    def _issue_token_for(self, subscriber):
        """Issue a token the same way SubscribeView does and persist its hash."""
        signed_token = make_signed_token(subscriber.pk)
        subscriber.verification_token = hash_token(signed_token)
        subscriber.save(update_fields=["verification_token"])
        return signed_token

    def _verify(self, token):
        response = self.client.get(self.verify_url, {"token": token})
        self.subscriber.refresh_from_db()
        return response

    @staticmethod
    def _messages(response):
        return [str(m) for m in django_messages.get_messages(response.wsgi_request)]

    # 1. valid signed token verifies the subscriber
    def test_valid_signed_token_verifies_subscriber(self):
        token = self._issue_token_for(self.subscriber)

        response = self._verify(token)

        self.assertEqual(response.status_code, 302)
        self.assertTrue(self.subscriber.is_verified)
        self.assertIn(MSG_VERIFIED, self._messages(response))

    # 2. invalid / garbage token is rejected
    def test_invalid_token_is_rejected(self):
        response = self._verify("not-a-real-token")

        self.assertEqual(response.status_code, 302)
        self.assertFalse(self.subscriber.is_verified)
        self.assertIn(MSG_INVALID_TOKEN, self._messages(response))

    def test_empty_token_is_rejected(self):
        response = self.client.get(self.verify_url, {"token": ""})

        self.assertFalse(self.subscriber.is_verified)
        self.assertIn(MSG_EMPTY_TOKEN, self._messages(response))

    # 3. tampered token is rejected
    def test_tampered_token_is_rejected(self):
        token = self._issue_token_for(self.subscriber)
        tampered = token[:-2] + ("ab" if not token.endswith("ab") else "cd")

        response = self._verify(tampered)

        self.assertFalse(self.subscriber.is_verified)
        self.assertIn(MSG_INVALID_TOKEN, self._messages(response))

    def test_token_signed_with_foreign_secret_is_rejected(self):
        foreign = TimestampSigner(key=b"a-different-secret-key")
        forged = make_signed_token(self.subscriber.pk, signed_by=foreign)
        self.subscriber.verification_token = hash_token(forged)
        self.subscriber.save(update_fields=["verification_token"])

        response = self._verify(forged)

        self.assertFalse(self.subscriber.is_verified)
        self.assertIn(MSG_INVALID_TOKEN, self._messages(response))

    def test_valid_signature_for_unknown_subscriber_is_not_found(self):
        # Correctly signed, but no subscriber has this token hash stored.
        unknown_subscriber_pk = self.subscriber.pk + 999
        stray = make_signed_token(unknown_subscriber_pk)

        response = self._verify(stray)

        self.assertFalse(self.subscriber.is_verified)
        self.assertIn(MSG_NOT_FOUND, self._messages(response))

    # 4. expired token is rejected, 12 hour window is not weakened
    def test_expired_token_is_rejected(self):
        aged = AgedSigner(NEWSLETTER_VERIFICATION_MAX_AGE + 60)
        expired = make_signed_token(self.subscriber.pk, signed_by=aged)
        self.subscriber.verification_token = hash_token(expired)
        self.subscriber.save(update_fields=["verification_token"])

        response = self._verify(expired)

        self.assertFalse(self.subscriber.is_verified)
        self.assertIn(MSG_INVALID_TOKEN, self._messages(response))

    def test_token_just_inside_max_age_still_verifies(self):
        fresh_enough = AgedSigner(NEWSLETTER_VERIFICATION_MAX_AGE - 300)
        token = make_signed_token(self.subscriber.pk, signed_by=fresh_enough)
        self.subscriber.verification_token = hash_token(token)
        self.subscriber.save(update_fields=["verification_token"])

        response = self._verify(token)

        self.assertTrue(self.subscriber.is_verified)
        self.assertIn(MSG_VERIFIED, self._messages(response))

    def test_max_age_is_twelve_hours(self):
        self.assertEqual(NEWSLETTER_VERIFICATION_MAX_AGE, 12 * 3600)

    # 5. a token must not verify an unrelated subscriber
    def test_token_does_not_verify_unrelated_subscriber(self):
        token = self._issue_token_for(self.subscriber)

        self._verify(token)

        self.other_subscriber.refresh_from_db()
        self.assertFalse(self.other_subscriber.is_verified)
        self.assertIsNone(self.other_subscriber.verification_token)

    def test_one_subscribers_token_cannot_verify_another_subscriber(self):
        attacker_token = self._issue_token_for(self.subscriber)

        self._verify(attacker_token)

        self.subscriber.refresh_from_db()
        self.other_subscriber.refresh_from_db()
        self.assertTrue(self.subscriber.is_verified)
        self.assertFalse(self.other_subscriber.is_verified)

    # 6. already verified subscriber
    def test_already_verified_subscriber_is_reported_not_reverified(self):
        token = self._issue_token_for(self.subscriber)
        self.subscriber.is_verified = True
        self.subscriber.save(update_fields=["is_verified"])

        response = self._verify(token)

        self.assertTrue(self.subscriber.is_verified)
        self.assertIn(MSG_ALREADY_VERIFIED, self._messages(response))
        self.assertNotIn(MSG_VERIFIED, self._messages(response))

    # 7. only the hash is stored, never the plaintext token
    def test_stored_verification_token_is_a_hash_not_plaintext(self):
        token = self._issue_token_for(self.subscriber)

        stored = self.subscriber.verification_token
        self.assertNotEqual(stored, token)
        self.assertEqual(stored, hash_token(token))
        self.assertEqual(len(stored), 64)
        self.assertNotIn(token, stored)
        raw_payload = signer.unsign(token)
        self.assertNotIn(raw_payload, stored)

    def test_stored_verification_token_does_not_match_hash_of_raw_token(self):
        token = self._issue_token_for(self.subscriber)
        raw_payload = signer.unsign(token)

        self.assertNotEqual(
            self.subscriber.verification_token,
            hash_token(raw_payload),
        )


@override_settings(EMAIL_BACKEND=LOCMEM)
class SubscribeViewTokenStorageTests(TestCase):
    """The token emitted by SubscribeView must verify end to end."""

    def test_emailed_token_hash_matches_database_and_verifies(self):
        response = self.client.post(
            "/newsletter/subscribe/", {"email": "new-reader@example.com"}
        )
        self.assertEqual(response.status_code, 302)

        subscriber = Subscriber.objects.get(email="new-reader@example.com")
        token = extract_token_from_email()

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(subscriber.verification_token, hash_token(token))
        self.assertNotEqual(subscriber.verification_token, token)
        self.assertFalse(subscriber.is_verified)

        self.client.get("/newsletter/verify/", {"token": token})

        subscriber.refresh_from_db()
        self.assertTrue(subscriber.is_verified)

    def test_subscribe_does_not_store_plaintext_token(self):
        self.client.post(
            "/newsletter/subscribe/", {"email": "another@example.com"}
        )

        subscriber = Subscriber.objects.get(email="another@example.com")
        token = extract_token_from_email()
        raw_payload = signer.unsign(token)

        self.assertNotEqual(subscriber.verification_token, token)
        self.assertNotEqual(subscriber.verification_token, raw_payload)