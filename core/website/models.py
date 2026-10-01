from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user_model
from datetime import datetime
from django.core.validators import EmailValidator


User = get_user_model()

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