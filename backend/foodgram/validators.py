import re
from django.core.exceptions import ValidationError
from foodgram.settings import (INAPPROPRIATE_USERNAME,
                               MIN_COOKING_TIME,
                               MIN_INGREDIENT_AMOUNT,
                               MAX_COOKING_TIME,
                               MAX_INGREDIENT_AMOUNT)


def validate_username(username):
    pattern = r'^[a-zA-Z0-9_-]+$'
    inappropriate_usernames = set(INAPPROPRIATE_USERNAME.lower())
    if (not re.match(pattern, username)
            or username.lower() in inappropriate_usernames):
        raise ValidationError('Этот логин не приветствуется')


def validate_cooking_time(cooking_time):
    if cooking_time < MIN_COOKING_TIME:
        raise ValidationError('Время приготовления должно быть больше 0.')
    if cooking_time > MAX_COOKING_TIME:
        raise ValidationError('За такое время сгорит все что угодно.')


def validate_ingredient_amount(ingredient_amount):
    if ingredient_amount < MIN_INGREDIENT_AMOUNT:
        raise ValidationError('Количество ингредиента должно быть больше 0.')
    if ingredient_amount > MAX_INGREDIENT_AMOUNT:
        raise ValidationError('А не слипнется? Многовато ингредиента.')
