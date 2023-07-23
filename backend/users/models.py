from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.core.exceptions import ValidationError
from django.db import models


def validate_username(value):
    inappropriate_usernames = ['admin', 'root', 'superuser']
    if value.lower() in inappropriate_usernames:
        raise ValidationError('Этот логин не приветствуется')


class User(AbstractUser):
    email = models.EmailField(
        max_length=254,
        unique=True,
        verbose_name='E-mail',
        help_text='Введите адрес электронной почты',
    )
    username = models.CharField(
        max_length=settings.USER_FIELD_LEN,
        unique=True,
        verbose_name='Логин',
        validators=(UnicodeUsernameValidator(), validate_username,)
    )
    first_name = models.CharField(
        max_length=settings.USER_FIELD_LEN,
        verbose_name='Имя',
        blank=False,
        help_text='Введите имя',
    )
    last_name = models.CharField(
        max_length=settings.USER_FIELD_LEN,
        verbose_name='Фамилия',
        blank=False,
        help_text='Введите фамилию',
    )
    password = models.CharField(
        max_length=settings.USER_FIELD_LEN,
        verbose_name='Пароль',
        blank=False,
    )

    class Meta:
        ordering = ('username',)
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'

    def __str__(self):
        return self.username


class Subscribe(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='subscriber',
        verbose_name='Подписчик',
    )
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='subscribing',
        verbose_name='Подписан',
    )

    class Meta:
        verbose_name = 'Подписка на авторов'
        verbose_name_plural = 'Подписки на авторов'
        ordering = ('user', 'author')
        constraints = [
            models.UniqueConstraint(
                fields=('user', 'author'),
                name='unique_subscribe',
            )
        ]

    def __str__(self):
        return self.author.username

    def clean(self):
        if self.user == self.author:
            raise ValidationError('Нельзя подписаться на себя.')
