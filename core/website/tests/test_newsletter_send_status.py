"""Newsletter send results must be reported accurately.

``send_newsletter`` looped over recipients and then unconditionally wrote
``status = 'sent'`` with ``sent_at`` stamped, without looking at any outcome.
A newsletter where every single address bounced was therefore persisted as
fully sent, which is exactly the opposite of what happened.

The status is now derived from the recipient rows, which already recorded the
individual outcomes, so the newsletter-level summary reflects reality:

* every recipient delivered -> ``sent``, ``sent_at`` set
* some delivered, some bounced -> ``partially_sent``, ``sent_at`` set
* nothing delivered -> ``failed``, ``sent_at`` empty
"""

from unittest.mock import patch

from django.core import mail
from django.test import TestCase, override_settings

from website.models import Newsletter, NewsletterRecipient, Subscriber
from website.services import NewsletterService

LOCMEM = "django.core.mail.backends.locmem.EmailBackend"


def make_subscribers(count, **kwargs):
    return [
        Subscriber.objects.create(
            email=f"sub{i}@example.com",
            is_active=kwargs.get("is_active", True),
            is_verified=kwargs.get("is_verified", True),
        )
        for i in range(count)
    ]


def send_with_failures(newsletter, failing_emails):
    """Run a real send where only the given recipient addresses fail.

    services.py renders 'newsletter/email.html', which lives under
    shop/newsletter/ on disk, so the template lookup is stubbed to isolate the
    delivery-status behaviour from that separate template-path bug.
    """

    def fake_send(self, *args, **kwargs):
        if self.to[0] in failing_emails:
            raise Exception("smtp refused")
        return 1

    with patch("website.services.render_to_string", return_value="<p>html</p>"):
        with patch("django.core.mail.EmailMultiAlternatives.send", fake_send):
            NewsletterService.send_newsletter(newsletter)
    newsletter.refresh_from_db()


def send_all_successfully(newsletter):
    send_with_failures(newsletter, set())


@override_settings(EMAIL_BACKEND=LOCMEM)
class AllRecipientsSucceedTests(TestCase):
    def setUp(self):
        mail.outbox = []
        self.newsletter = Newsletter.objects.create(
            subject="اخبار", preview_text="خلاصه", content="<p>متن</p>"
        )
        make_subscribers(3)

    def test_every_recipient_row_is_marked_sent(self):
        send_all_successfully(self.newsletter)

        rows = NewsletterRecipient.objects.filter(newsletter=self.newsletter)
        self.assertEqual(rows.count(), 3)
        self.assertEqual(rows.filter(status="sent").count(), 3)
        self.assertEqual(rows.filter(status="bounced").count(), 0)

    def test_every_recipient_row_records_sent_at(self):
        send_all_successfully(self.newsletter)

        for row in NewsletterRecipient.objects.filter(newsletter=self.newsletter):
            self.assertIsNotNone(row.sent_at)

    def test_status_is_sent(self):
        send_all_successfully(self.newsletter)

        self.assertEqual(self.newsletter.status, "sent")

    def test_sent_at_is_populated(self):
        send_all_successfully(self.newsletter)

        self.assertIsNotNone(self.newsletter.sent_at)

    def test_unverified_and_inactive_subscribers_are_not_recipients(self):
        Subscriber.objects.create(
            email="unverified@example.com", is_active=True, is_verified=False
        )
        Subscriber.objects.create(
            email="inactive@example.com", is_active=False, is_verified=True
        )

        send_all_successfully(self.newsletter)

        rows = NewsletterRecipient.objects.filter(newsletter=self.newsletter)
        self.assertEqual(rows.count(), 3)


@override_settings(EMAIL_BACKEND=LOCMEM)
class OneRecipientFailsTests(TestCase):
    def setUp(self):
        mail.outbox = []
        self.newsletter = Newsletter.objects.create(
            subject="اخبار", preview_text="خلاصه", content="<p>متن</p>"
        )
        self.subscribers = make_subscribers(3)

    def test_status_is_partially_sent(self):
        send_with_failures(self.newsletter, {self.subscribers[1].email})

        self.assertEqual(self.newsletter.status, "partially_sent")

    def test_the_failure_is_recorded_on_its_own_row(self):
        send_with_failures(self.newsletter, {self.subscribers[1].email})

        rows = NewsletterRecipient.objects.filter(newsletter=self.newsletter)
        bounced = rows.get(subscriber=self.subscribers[1])
        self.assertEqual(bounced.status, "bounced")

    def test_a_failed_delivery_does_not_get_a_sent_at(self):
        send_with_failures(self.newsletter, {self.subscribers[1].email})

        bounced = NewsletterRecipient.objects.get(
            newsletter=self.newsletter, subscriber=self.subscribers[1]
        )
        self.assertIsNone(bounced.sent_at)

    def test_remaining_recipients_are_still_sent(self):
        # The run must not stop at the first rejected address.
        send_with_failures(self.newsletter, {self.subscribers[0].email})

        rows = NewsletterRecipient.objects.filter(newsletter=self.newsletter)
        self.assertEqual(rows.filter(status="sent").count(), 2)
        self.assertEqual(rows.filter(status="bounced").count(), 1)

    def test_sent_at_is_populated_because_something_was_delivered(self):
        send_with_failures(self.newsletter, {self.subscribers[1].email})

        self.assertIsNotNone(self.newsletter.sent_at)


@override_settings(EMAIL_BACKEND=LOCMEM)
class MultipleRecipientsFailTests(TestCase):
    def setUp(self):
        mail.outbox = []
        self.newsletter = Newsletter.objects.create(
            subject="اخبار", preview_text="خلاصه", content="<p>متن</p>"
        )
        self.subscribers = make_subscribers(5)

    def test_status_is_partially_sent_when_one_still_succeeds(self):
        failing = {s.email for s in self.subscribers[:4]}
        send_with_failures(self.newsletter, failing)

        self.assertEqual(self.newsletter.status, "partially_sent")

    def test_each_failure_is_recorded_individually(self):
        failing = {s.email for s in self.subscribers[:4]}
        send_with_failures(self.newsletter, failing)

        rows = NewsletterRecipient.objects.filter(newsletter=self.newsletter)
        self.assertEqual(rows.filter(status="bounced").count(), 4)
        self.assertEqual(rows.filter(status="sent").count(), 1)

    def test_the_single_success_is_recorded_with_its_sent_at(self):
        send_with_failures(
            self.newsletter, {s.email for s in self.subscribers[:4]}
        )

        winner = NewsletterRecipient.objects.get(
            newsletter=self.newsletter, subscriber=self.subscribers[4]
        )
        self.assertEqual(winner.status, "sent")
        self.assertIsNotNone(winner.sent_at)


@override_settings(EMAIL_BACKEND=LOCMEM)
class AllRecipientsFailTests(TestCase):
    def setUp(self):
        mail.outbox = []
        self.newsletter = Newsletter.objects.create(
            subject="اخبار", preview_text="خلاصه", content="<p>متن</p>"
        )
        self.subscribers = make_subscribers(3)

    def test_status_is_failed(self):
        send_with_failures(self.newsletter, {s.email for s in self.subscribers})

        self.assertEqual(self.newsletter.status, "failed")

    def test_status_is_not_sent(self):
        send_with_failures(self.newsletter, {s.email for s in self.subscribers})

        self.assertNotEqual(self.newsletter.status, "sent")

    def test_sent_at_is_left_empty(self):
        send_with_failures(self.newsletter, {s.email for s in self.subscribers})

        self.assertIsNone(self.newsletter.sent_at)

    def test_every_row_is_bounced(self):
        send_with_failures(self.newsletter, {s.email for s in self.subscribers})

        rows = NewsletterRecipient.objects.filter(newsletter=self.newsletter)
        self.assertEqual(rows.filter(status="bounced").count(), 3)

    def test_a_previous_sent_at_is_cleared_when_a_resend_delivers_nothing(self):
        self.newsletter.sent_at = "2026-01-01T00:00:00Z"
        self.newsletter.save()

        send_with_failures(self.newsletter, {s.email for s in self.subscribers})

        self.assertIsNone(self.newsletter.sent_at)


@override_settings(EMAIL_BACKEND=LOCMEM)
class ResendReflectsActualStateTests(TestCase):
    """A re-send must not claim success for recipients it never touched."""

    def setUp(self):
        mail.outbox = []
        self.newsletter = Newsletter.objects.create(
            subject="اخبار", preview_text="خلاصه", content="<p>متن</p>"
        )

    def test_resend_with_no_new_subscribers_keeps_the_true_status(self):
        subscribers = make_subscribers(2)
        send_with_failures(
            self.newsletter, {s.email for s in subscribers}
        )
        self.assertEqual(self.newsletter.status, "failed")

        # Nobody new: every recipient row already exists, so nothing is sent.
        make_subscribers(0)
        Subscriber.objects.create(
            email="late@example.com", is_active=True, is_verified=True
        )
        Subscriber.objects.filter(email="late@example.com").update(is_verified=True)

        send_all_successfully(self.newsletter)

        # The two earlier bounces still stand, so the newsletter is partial
        # rather than being reported as fully sent.
        self.assertEqual(self.newsletter.status, "partially_sent")

    def test_later_delivery_states_still_count_as_delivered(self):
        subscribers = make_subscribers(2)
        send_with_failures(
            self.newsletter, {s.email for s in subscribers}
        )
        NewsletterRecipient.objects.filter(
            newsletter=self.newsletter, subscriber=subscribers[0]
        ).update(status="opened")

        send_all_successfully(self.newsletter)

        self.assertEqual(self.newsletter.status, "partially_sent")


@override_settings(EMAIL_BACKEND=LOCMEM)
class NoSubscribersTests(TestCase):
    def setUp(self):
        mail.outbox = []
        self.newsletter = Newsletter.objects.create(
            subject="اخبار", preview_text="خلاصه", content="<p>متن</p>"
        )

    def test_send_with_no_subscribers_does_not_report_a_failure(self):
        NewsletterService.send_newsletter(self.newsletter)
        self.newsletter.refresh_from_db()

        # Nothing to deliver and nothing failed, so the run succeeded.
        self.assertEqual(self.newsletter.status, "sent")

    def test_no_recipient_rows_are_created(self):
        NewsletterService.send_newsletter(self.newsletter)

        self.assertEqual(
            NewsletterRecipient.objects.filter(newsletter=self.newsletter).count(), 0
        )


@override_settings(EMAIL_BACKEND=LOCMEM)
class EmailFailureHandlingTests(TestCase):
    """Every delivery outcome must be recorded the same way."""

    def setUp(self):
        mail.outbox = []
        self.newsletter = Newsletter.objects.create(
            subject="اخبار", preview_text="خلاصه", content="<p>متن</p>"
        )
        self.subscribers = make_subscribers(2)

    def _existing_recipient(self):
        """A recipient row created outside send_newsletter."""
        return NewsletterRecipient.objects.create(
            newsletter=self.newsletter, subscriber=self.subscribers[0]
        )

    def test_send_email_returns_true_on_success(self):
        recipient = self._existing_recipient()

        with patch("website.services.render_to_string", return_value="<p>h</p>"):
            self.assertIs(NewsletterService._send_email(recipient), True)

    def test_send_email_returns_false_and_records_bounced_on_failure(self):
        recipient = self._existing_recipient()

        with patch("website.services.render_to_string", return_value="<p>h</p>"):
            with patch(
                "django.core.mail.EmailMultiAlternatives.send",
                side_effect=Exception("smtp refused"),
            ):
                result = NewsletterService._send_email(recipient)

        self.assertIs(result, False)
        recipient.refresh_from_db()
        self.assertEqual(recipient.status, "bounced")

    def test_a_timeout_is_recorded_as_a_delivery_failure(self):
        import smtplib

        recipient = self._existing_recipient()

        with patch("website.services.render_to_string", return_value="<p>h</p>"):
            with patch(
                "django.core.mail.EmailMultiAlternatives.send",
                side_effect=smtplib.SMTPRecipientsRefused({}),
            ):
                result = NewsletterService._send_email(recipient)

        self.assertIs(result, False)
        recipient.refresh_from_db()
        self.assertEqual(recipient.status, "bounced")

    def test_failures_do_not_stop_the_remaining_recipients(self):
        failing = {self.subscribers[0].email}

        def fake_send(self, *args, **kwargs):
            if self.to[0] in failing:
                raise Exception("smtp refused")
            return 1

        Subscriber.objects.create(
            email="other@example.com", is_active=True, is_verified=True
        )

        with patch("website.services.render_to_string", return_value="<p>h</p>"):
            with patch("django.core.mail.EmailMultiAlternatives.send", fake_send):
                NewsletterService.send_newsletter(self.newsletter)
        self.newsletter.refresh_from_db()

        rows = NewsletterRecipient.objects.filter(newsletter=self.newsletter)
        # three subscribers exist: one bounces, the other two are still sent
        self.assertEqual(rows.filter(status="bounced").count(), 1)
        self.assertEqual(rows.filter(status="sent").count(), 2)
        self.assertEqual(self.newsletter.status, "partially_sent")