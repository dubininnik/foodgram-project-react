import re
from django.core.exceptions import ValidationError
from django.conf import settings


def validate_username(username):
    pattern = settings.PATTERN
    inappropriate_usernames = settings.INAPPROPRIATE_USERNAME
    if not re.match(pattern, username):
        invalid_symbols = re.sub(pattern, '', username)
        raise ValidationError(f'Логин "{username}" содержит неподходящие'
                              f' символы: {invalid_symbols}')
    if username.lower() in inappropriate_usernames:
        raise ValidationError(f'Такой логин "{username}" недопустим')
    return username
