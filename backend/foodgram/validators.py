import re

from django.conf import settings
from django.core.exceptions import ValidationError


def validate_username(username):
    if not re.match(settings.USERNAME_PATTERN, username):
        invalid_symbols = ''.join(
            set(re.sub(settings.USERNAME_PATTERN, '', username))
        )
        raise ValidationError(f'Логин "{username}" содержит неподходящие'
                              f' символы: {invalid_symbols}')
    if username.lower() in settings.INAPPROPRIATE_USERNAMES:
        raise ValidationError(f'Такой логин: "{username}" недопустим')
    return username
