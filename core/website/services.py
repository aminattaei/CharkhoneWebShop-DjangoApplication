import logging

from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.html import strip_tags
from django.db import IntegrityError

from .models import Subscriber, Newsletter, NewsletterRecipient

logger = logging.getLogger(__name__)


class NewsletterService:

    #: Recipient states that mean the message reached the subscriber. "opened"
    #: and "clicked" are later stages of a delivery that already happened, so
    #: they count as delivered.
    DELIVERED_STATUSES = ("sent", "opened", "clicked")

    #: Recipient states that mean delivery definitively failed.
    FAILED_STATUSES = ("bounced",)

    @staticmethod
    def send_newsletter(newsletter):
        """Send a newsletter to all active subscribers.

        A rejected address does not abort the run: every remaining subscriber
        is still attempted and each outcome is recorded on its recipient row.
        The newsletter status is derived from those rows afterwards, so it
        reports what actually happened instead of assuming success.
        """
        subscribers = Subscriber.objects.filter(is_active=True, is_verified=True)
        recipients = []

        for subscriber in subscribers:
            recipient, created = NewsletterRecipient.objects.get_or_create(
                newsletter=newsletter,
                subscriber=subscriber,
                defaults={'status': 'pending'}
            )
            if created:
                recipients.append(recipient)

        for recipient in recipients:
            NewsletterService._send_email(recipient)

        NewsletterService._update_status(newsletter)

    @staticmethod
    def _update_status(newsletter):
        """Derive the newsletter status and sent_at from the recipient rows.

        Reading the rows rather than the loop's return values keeps the status
        truthful across re-sends, where recipients already recorded by an
        earlier run count too.
        """
        rows = NewsletterRecipient.objects.filter(newsletter=newsletter)
        delivered = rows.filter(
            status__in=NewsletterService.DELIVERED_STATUSES
        ).count()
        failed = rows.filter(status__in=NewsletterService.FAILED_STATUSES).count()

        if failed and delivered:
            status = 'partially_sent'
        elif failed:
            status = 'failed'
        else:
            status = 'sent'

        newsletter.status = status
        # sent_at records that a dispatch actually took place, so it stays
        # empty when the message reached nobody at all.
        newsletter.sent_at = timezone.now() if delivered else None
        newsletter.save()
        logger.info(
            "خبرنامه %s ارسال شد: %s موفق، %s ناموفق، وضعیت %s",
            newsletter.pk,
            delivered,
            failed,
            status,
        )

    @staticmethod
    def _send_email(recipient):
        """Send a single newsletter email."""
        from .unsubscribe_tokens import build_unsubscribe_url

        newsletter = recipient.newsletter
        subscriber = recipient.subscriber

        unsubscribe_url = build_unsubscribe_url(subscriber.pk)
        
        context = {
            'newsletter': newsletter,
            'subscriber': subscriber,
            'unsubscribe_url': unsubscribe_url,
        }
        
        html_content = render_to_string('newsletter/email.html', context)
        
        plain_text = newsletter.plain_text_content or strip_tags(html_content)
        
        email = EmailMultiAlternatives(
            subject=newsletter.subject,
            body=plain_text,
            from_email=None,
            to=[subscriber.email],
        )
        email.attach_alternative(html_content, "text/html")
        
        try:
            email.send()
            recipient.status = 'sent'
            recipient.sent_at = timezone.now()
            recipient.save()
            return True
        except Exception as e:
            recipient.status = 'bounced'
            recipient.save()
            logger.warning(
                "ارسال خبرنامه به %s ناموفق بود: %s", subscriber.email, e
            )
            return False