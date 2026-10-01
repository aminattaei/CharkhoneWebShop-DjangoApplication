from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.db import IntegrityError

from .models import Subscriber, Newsletter, NewsletterRecipient


class NewsletterService:
    
    @staticmethod
    def send_newsletter(newsletter):
        """Send a newsletter to all active subscribers."""
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
        
        newsletter.status = 'sent'
        from django.utils import timezone
        newsletter.sent_at = timezone.now()
        newsletter.save()
    
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
            from django.utils import timezone
            recipient.sent_at = timezone.now()
            recipient.save()
            return True
        except Exception as e:
            recipient.status = 'bounced'
            recipient.save()
            return False