from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ('username', 'first_name', 'last_name', 'password')

    GUEST = 'guest'
    AUTHORIZED = 'authorized'
    ADMIN = 'admin'

    USER_ROLES = [
        (GUEST, 'guest'),
        (AUTHORIZED, 'authorized'),
        (ADMIN, 'admin'),
    ]

    email = models.EmailField(
        max_length=254,
        unique=True,
        verbose_name='E-mail',
    )
    username = models.CharField(
        max_length=150,
        unique=True,
        verbose_name='Логин',
        blank=False,
    )
    first_name = models.CharField(
        max_length=150,
        verbose_name='Имя',
        blank=False,
    )
    last_name = models.CharField(
        max_length=150,
        verbose_name='Фамилия',
        blank=False,
    )
    password = models.CharField(
        max_length=150,
        verbose_name='Пароль',
    )
    role = models.CharField(
        max_length=10,
        choices=USER_ROLES,
        default='guest',
        verbose_name='Роль пользователя',
    )

    @property
    def is_guest(self):
        return self.role == self.GUEST

    @property
    def is_authorized(self):
        return self.role == self.AUTHORIZED

    @property
    def is_admin(self):
        return self.role == self.ADMIN or self.is_superuser

    class Meta:
        ordering = ['id']
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
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'author'],
                name='unique_subscribe',
            )
        ]

    def __str__(self):
        return f'{self.user.username} - {self.author.username}'
