from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user_model
from datetime import datetime
from django.core.validators import EmailValidator
import html
import re
import urllib.parse


User = get_user_model()


class HTMLSanitizer(html.parser.HTMLParser):
    """Minimal HTML sanitizer for newsletter content.

    Strips dangerous tags, event-handler attributes, and non-http URL schemes
    while preserving the safe formatting elements a newsletter author needs.
    """

    ALLOWED_TAGS = {
        "p", "div", "span", "br", "hr",
        "h1", "h2", "h3", "h4", "h5", "h6",
        "strong", "em", "u", "b", "i", "small",
        "a", "ul", "ol", "li",
        "img", "table", "tr", "td", "th", "thead", "tbody",
    }

    ALLOWED_ATTRS = {
        "a": {"href", "title", "target"},
        "img": {"src", "alt", "title", "width", "height"},
        "*": {"class"},
    }

    SAFE_PROTOCOLS = ("http", "https", "mailto")

    def __init__(self):
        super().__init__()
        self.output = []
        self._skip_tag = None
        self._skip_depth = 0

    def _safe_url(self, value):
        if not value:
            return False
        scheme = urllib.parse.urlparse(value).scheme.lower()
        return scheme in self.SAFE_PROTOCOLS

    def _filtered_attrs(self, tag, attrs):
        allowed = self.ALLOWED_ATTRS.get("*", set()) | self.ALLOWED_ATTRS.get(
            tag, set()
        )
        result = []
        for name, value in attrs:
            if name not in allowed:
                continue
            if name in ("href", "src") and not self._safe_url(value):
                continue
            result.append(
                f' {name}="{html.escape(value, quote=True)}"'
                if value is not None
                else f" {name}"
            )
        return result

    def handle_starttag(self, tag, attrs):
        if tag not in self.ALLOWED_TAGS:
            self._skip_tag = tag
            self._skip_depth = 1
            return
        if self._skip_tag:
            self._skip_depth += 1
            return
        parts = self._filtered_attrs(tag, attrs)
        self.output.append(f"<{tag}{''.join(parts)}>")

    def handle_endtag(self, tag):
        if self._skip_tag:
            if tag == self._skip_tag:
                self._skip_depth -= 1
                if self._skip_depth == 0:
                    self._skip_tag = None
            return
        if tag in self.ALLOWED_TAGS:
            self.output.append(f"</{tag}>")

    def handle_startendtag(self, tag, attrs):
        if tag not in self.ALLOWED_TAGS or self._skip_tag:
            return
        parts = self._filtered_attrs(tag, attrs)
        self.output.append(f"<{tag}{''.join(parts)}/>")

    def handle_data(self, data):
        if not self._skip_tag:
            self.output.append(html.escape(data, quote=True))

    def get_html(self):
        return "".join(self.output)


def sanitize_newsletter_html(content):
    """Sanitize newsletter HTML at the model boundary.

    The newsletter content field is intentionally rich HTML authored by staff.
    This function preserves safe formatting while removing active-content
    vectors (script, event handlers, javascript:/data: URLs, etc.).
    """
    if not content:
        return content
    parser = HTMLSanitizer()
    parser.feed(content)
    return parser.get_html()


class ContactModel(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField()
    subject = models.CharField(max_length=200)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)
    

    class Meta:
        ordering = ['-created_at']
        verbose_name = _("Contact")
        verbose_name_plural = _("Contacts")

    def __str__(self):
        return f"{self.name} / {self.created_at} / {self.is_read}" 


class Subscriber(models.Model):
    """
    Model for storing newsletter subscribers.
    """
    email = models.EmailField(
        unique=True,
        validators=[EmailValidator()],
        verbose_name="Email Address"
    )
    name = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name="Full Name"
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="Active"
    )
    is_verified = models.BooleanField(
        default=False,
        verbose_name="Verified"
    )
    verification_token = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name="Verification Token"
    )
    subscribed_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Subscribed At"
    )
    unsubscribed_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="Unsubscribed At"
    )
    
    class Meta:
        ordering = ['-subscribed_at']
        verbose_name = "Subscriber"
        verbose_name_plural = "Subscribers"
    
    def __str__(self):
        return self.email
    
    def unsubscribe(self):
        """Unsubscribe the subscriber."""
        self.is_active = False
        self.unsubscribed_at = timezone.now()
        self.save(update_fields=["is_active", "unsubscribed_at"])


class Newsletter(models.Model):
    """
    Model for creating and managing newsletters.
    """
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('scheduled', 'Scheduled'),
        ('partially_sent', 'Partially Sent'),
        ('sent', 'Sent'),
        ('failed', 'Failed'),
    ]
    
    subject = models.CharField(
        max_length=255,
        verbose_name="Subject"
    )
    preview_text = models.CharField(
        max_length=255,
        blank=True,
        help_text="Preview text shown in email clients",
        verbose_name="Preview Text"
    )
    content = models.TextField(
        verbose_name="HTML Content"
    )
    plain_text_content = models.TextField(
        blank=True,
        verbose_name="Plain Text Content"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='draft',
        verbose_name="Status"
    )
    scheduled_for = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="Scheduled For"
    )
    sent_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="Sent At"
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='newsletters',
        verbose_name="Created By"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Created At"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Updated At"
    )
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Newsletter"
        verbose_name_plural = "Newsletters"
    
    def __str__(self):
        return self.subject
    
    def send(self):
        """Send the newsletter to all active subscribers."""
        from .services import NewsletterService
        NewsletterService.send_newsletter(self)
    
    def get_recipient_count(self):
        """Get the number of active subscribers."""
        return Subscriber.objects.filter(is_active=True).count()

    def save(self, *args, **kwargs):
        if self.content:
            self.content = sanitize_newsletter_html(self.content)
        super().save(*args, **kwargs)


class NewsletterRecipient(models.Model):
    """`
    Track which subscribers received which newsletters.
    """
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('sent', 'Sent'),
        ('opened', 'Opened'),
        ('clicked', 'Clicked'),
        ('bounced', 'Bounced'),
    ]
    
    newsletter = models.ForeignKey(
        Newsletter,
        on_delete=models.CASCADE,
        related_name='recipients'
    )
    subscriber = models.ForeignKey(
        Subscriber,
        on_delete=models.CASCADE,
        related_name='received_newsletters'
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name="Status"
    )
    sent_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="Sent At"
    )
    opened_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="Opened At"
    )
    clicked_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="Clicked At"
    )
    
    class Meta:
        unique_together = ['newsletter', 'subscriber']
        verbose_name = "Newsletter Recipient"
        verbose_name_plural = "Newsletter Recipients"
    
    def __str__(self):
        return f"{self.newsletter.subject} - {self.subscriber.email}"