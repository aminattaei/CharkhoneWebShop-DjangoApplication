from django.core.cache import cache
from rest_framework.throttling import ScopedRateThrottle


class ResetRequestThrottle(ScopedRateThrottle):
    scope = 'password_reset_request'


class ResetAttemptThrottle(ScopedRateThrottle):
    scope = 'password_reset_attempt'


class EmailBasedThrottle:
    RATE = '3/hour'
    DURATION = 3600

    def allow_request(self, request, view):
        email = request.data.get('email', '').lower()
        if not email:
            return True
        key = f'reset_throttle_{email}'
        count = cache.get(key, 0)
        if count >= 3:
            return False
        cache.set(key, count + 1, self.DURATION)
        return True

    def wait(self):
        return None
