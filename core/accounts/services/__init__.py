from .password_reset import request_password_reset, complete_password_reset
from .email import build_password_reset_link, send_password_reset_email
from .tokens import generate_reset_token, verify_reset_token, mark_token_used
from .verification import (
    EmailDeliveryError,
    build_verification_link,
    send_verification_email,
    generate_verification_token,
    verify_verification_token,
    mark_verification_token_used,
)

send_reset_email = send_password_reset_email

__all__ = [
    "request_password_reset",
    "complete_password_reset",
    "build_password_reset_link",
    "send_password_reset_email",
    "send_reset_email",
    "generate_reset_token",
    "verify_reset_token",
    "mark_token_used",
    "build_verification_link",
    "EmailDeliveryError",
    "send_verification_email",
    "generate_verification_token",
    "verify_verification_token",
    "mark_verification_token_used",
]
