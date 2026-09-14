from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin
from django.contrib.sessions.models import Session

from .models import (
    Profile,
    PasswordResetToken,
    EmailVerificationToken,
)

User = get_user_model()


# ============================================================
# Django Admin Configuration
# ============================================================

admin.site.site_title = "Charkhoneh Site Admin (DEV)"
admin.site.site_header = "Charkhoneh Administration"
admin.site.index_title = "Charkhoneh Site Administration"


# ============================================================
# User Admin
# ============================================================

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    """
    Custom admin configuration for the custom User model.
    """

    model = User

    list_display = (
        "id",
        "email",
        "type",
        "is_staff",
        "is_superuser",
        "is_active",
        "is_verified",
        "is_locked",
    )

    list_filter = (
        "type",
        "is_staff",
        "is_superuser",
        "is_active",
        "is_verified",
        "is_locked",
    )

    search_fields = (
        "email",
    )

    ordering = (
        "email",
    )

    fieldsets = (
        (
            "Authentication",
            {
                "fields": (
                    "email",
                    "password",
                ),
            },
        ),
        (
            "Account Status",
            {
                "fields": (
                    "is_active",
                    "is_verified",
                    "is_locked",
                ),
            },
        ),
        (
            "Permissions",
            {
                "fields": (
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                    "type",
                ),
            },
        ),
        (
            "Security",
            {
                "fields": (
                    "failed_reset_attempts",
                    "last_reset_attempt",
                ),
            },
        ),
        (
            "Important Dates",
            {
                "fields": (
                    "last_login",
                    "deactivated_at",
                    "created_date",
                    "updated_date",
                ),
            },
        ),
    )

    readonly_fields = (
        "last_login",
        "created_date",
        "updated_date",
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": (
                    "wide",
                ),
                "fields": (
                    "email",
                    "password1",
                    "password2",
                    "is_staff",
                    "is_active",
                    "is_superuser",
                    "is_verified",
                    "type",
                ),
            },
        ),
    )


# ============================================================
# Profile Admin
# ============================================================

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    """
    Admin configuration for user profiles.
    """

    list_display = (
        "id",
        "user",
        "first_name",
        "last_name",
        "national_id",
        "phone_number",
    )

    search_fields = (
        "user__email",
        "first_name",
        "last_name",
        "national_id",
        "phone_number",
    )

    ordering = (
        "id",
    )


# ============================================================
# Password Reset Token Admin
# ============================================================

@admin.register(PasswordResetToken)
class PasswordResetTokenAdmin(admin.ModelAdmin):
    """
    Admin configuration for password reset tokens.
    """

    list_display = (
        "id",
        "user",
        "created_at",
        "expires_at",
        "is_used",
    )

    list_filter = (
        "is_used",
        "created_at",
        "expires_at",
    )

    search_fields = (
        "user__email",
    )

    readonly_fields = (
        "user",
        "token_hash",
        "created_at",
        "expires_at",
    )


# ============================================================
# Django Session Admin
# ============================================================

@admin.register(Session)
class SessionAdmin(admin.ModelAdmin):
    """
    Admin configuration for Django sessions.
    """

    def session_data(self, obj):
        return obj.get_decoded()

    session_data.short_description = "Session Data"

    list_display = (
        "session_key",
        "session_data",
        "expire_date",
    )

    readonly_fields = (
        "session_key",
        "session_data",
        "expire_date",
    )

    search_fields = (
        "session_key",
    )

# ============================================================
# Email Verification Token Admin
# ============================================================

@admin.register(EmailVerificationToken)
class EmailVerificationTokenAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "created_at",
        "expires_at",
        "is_used",
    )

    list_filter = (
        "is_used",
        "created_at",
        "expires_at",
    )

    search_fields = (
        "user__email",
    )

    readonly_fields = (
        "user",
        "token_hash",
        "created_at",
        "expires_at",
    )