from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags

from datetime import datetime
from decimal import Decimal


from .models import Subscriber, Newsletter, NewsletterRecipient
def _coerce_to_decimal(value, default=Decimal("0")):
    if isinstance(value, Decimal):
        return value
    if isinstance(value, (int, float)):
        return Decimal(str(value))
    try:
        return Decimal(str(value))
    except (TypeError, ValueError):
        return default


def calculate_final_price(price, discount_percent=0):
    price_value = _coerce_to_decimal(price, default=Decimal("0"))
    discount_value = _coerce_to_decimal(discount_percent, default=Decimal("0"))

    discount = Decimal(max(0, min(100, int(discount_value))))
    final = price_value * (Decimal("100") - discount) / Decimal("100")

    return final



class NewsletterService:
    
    @staticmethod
    def send_newsletter(newsletter):
        """Send a newsletter to all active subscribers."""
        subscribers = Subscriber.objects.filter(is_active=True, is_verified=True)
        recipients = []
        
        for subscriber in subscribers:
            recipient = NewsletterRecipient.objects.create(
                newsletter=newsletter,
                subscriber=subscriber,
                status='pending'
            )
            recipients.append(recipient)
        
        # Send emails (could be moved to Celery for async)
        for recipient in recipients:
            NewsletterService._send_email(recipient)
        
        newsletter.status = 'sent'
        newsletter.sent_at = datetime.now()
        newsletter.save()
    
    @staticmethod
    def _send_email(recipient):
        """Send a single newsletter email."""
        newsletter = recipient.newsletter
        subscriber = recipient.subscriber
        
        # Context for email template
        context = {
            'newsletter': newsletter,
            'subscriber': subscriber,
        }
        
        # Render HTML content
        html_content = render_to_string('newsletter/email.html', context)
        
        # Use plain text if provided, otherwise generate from HTML
        plain_text = newsletter.plain_text_content or strip_tags(html_content)
        
        email = EmailMultiAlternatives(
            subject=newsletter.subject,
            body=plain_text,
            from_email=None,  # Uses DEFAULT_FROM_EMAIL
            to=[subscriber.email],
        )
        email.attach_alternative(html_content, "text/html")
        
        try:
            email.send()
            recipient.status = 'sent'
            recipient.sent_at = datetime.now()
            recipient.save()
            return True
        except Exception as e:
            recipient.status = 'bounced'
            recipient.save()
            # Log error
            return False