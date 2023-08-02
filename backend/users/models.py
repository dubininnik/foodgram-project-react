from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.db import models

from foodgram.validators import validate_username


class User(AbstractUser):
    email = models.EmailField(
        max_length=settings.DEFAULT_MAX_LENGTH,
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
        help_text='Введите имя',
    )
    last_name = models.CharField(
        max_length=settings.USER_FIELD_LEN,
        verbose_name='Фамилия',
        help_text='Введите фамилию',
    )
    password = models.CharField(
        max_length=settings.USER_FIELD_LEN,
        verbose_name='Пароль',
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
            ),
            models.CheckConstraint(
                check=~models.Q(user=models.F('author')),
                name='subscribe_user_not_author',
            ),
        ]

    def __str__(self):
        return f'{self.user} подписан на {self.author}'
