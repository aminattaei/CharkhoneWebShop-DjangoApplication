import pytest

from django.contrib.auth import get_user_model

User = get_user_model()

# @pytest.mark.django_db
# def test_my_user():
#     me = User.objects.get(email='admin@admin.com')
#     assert me.is_superuser