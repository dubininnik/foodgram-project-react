from django.conf import settings
from django.core.validators import (MaxValueValidator,
                                    MinValueValidator,
                                    RegexValidator)
from django.db import models
from django.db import models

from users.models import User


class Ingredient(models.Model):
    name = models.CharField(
        max_length=settings.DEFAULT_MAX_LENGTH,
        verbose_name='Название ингридиента',
    )
    measurement_unit = models.CharField(
        max_length=settings.DEFAULT_MAX_LENGTH,
        verbose_name='Единица измерения',
    )

    class Meta:
        verbose_name = 'Ингридиент'
        verbose_name_plural = 'Ингридиенты'
        ordering = ('name',)
        constraints = [
            models.UniqueConstraint(
                fields=('name', 'measurement_unit'),
                name='unique_ingredient'
            )
        ]

    def __str__(self):
        return self.name


class Tag(models.Model):
    name = models.CharField(
        max_length=settings.DEFAULT_MAX_LENGTH_TAG_NAME,
        verbose_name='Название тега',
    )
    color = models.CharField(
        max_length=settings.DEFAULT_MAX_LENGTH_TAG_COLOR,
        unique=True,
        verbose_name='Цвет в HEX',
        validators=[
            RegexValidator(
                settings.HEX_PATTERN,
                message='Поле должно содержать HEX цвета'
            )
        ]
    )
    slug = models.SlugField(
        max_length=settings.DEFAULT_MAX_LENGTH,
        unique=True,
        verbose_name='Slug тэга',
    )

    class Meta:
        verbose_name = 'Тег'
        verbose_name_plural = 'Теги'
        ordering = ('name',)

    def __str__(self):
        return self.name


class Recipe(models.Model):
    name = models.CharField(
        max_length=settings.DEFAULT_MAX_LENGTH,
        verbose_name='Название рецепта',
    )
    image = models.ImageField(
        upload_to='recipes/',
        verbose_name='Изображение',
    )
    text = models.TextField(
        verbose_name='Описание рецепта',
    )
    ingredients = models.ManyToManyField(
        'Ingredient',
        through='RecipeIngredient',
        through_fields=('recipe', 'ingredient'),
        verbose_name='Ингредиенты',
    )
    tags = models.ManyToManyField(
        'Tag',
        verbose_name='Теги'
    )
    cooking_time = models.PositiveSmallIntegerField(
        validators=[
            MinValueValidator(settings.MIN_COOKING_TIME,
                              message='Время приготовления должно'
                              ' быть больше 0.'),
            MaxValueValidator(settings.MAX_COOKING_TIME,
                              message='За такое время сгорит все'
                              ' что угодно.')
        ],
        verbose_name='Время приготовления в минутах',
    )
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name='Автор рецепта',
    )

    class Meta:
        ordering = ('name',)
        verbose_name = 'Рецепт'
        verbose_name_plural = 'Рецепты'
        default_related_name = 'recipes'

    def __str__(self):
        return self.name


class RecipeIngredient(models.Model):
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name='recipes',
        verbose_name='Рецепт',
    )
    ingredient = models.ForeignKey(
        Ingredient,
        on_delete=models.CASCADE,
        related_name='ingredients',
        verbose_name='Ингредиент',
    )
    amount = models.PositiveSmallIntegerField(
        validators=[
            MinValueValidator(settings.MIN_INGREDIENT_AMOUNT,
                              message='Количество ингредиента должно'
                              ' быть больше 0.'),
            MaxValueValidator(settings.MAX_INGREDIENT_AMOUNT,
                              message='А не слипнется? Многовато'
                              ' ингредиента.')
        ],
        verbose_name='Количество',
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=('recipe', 'ingredient'),
                name='unique_combination',
            )
        ]
        verbose_name = 'Ингредиент рецепта'
        verbose_name_plural = 'Ингредиенты рецепта'

    def _str__(self):
        return f'{self.ingredient} - {self.amount}'


class AbstractFavoriteShoppingCart(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
    )
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
    )

    class Meta:
        abstract = True
        ordering = ('user',)
        constraints = [
            models.UniqueConstraint(
                fields=('user', 'recipe'),
                name='%(class)s_unique_user_recipe'
            )
        ]
        default_related_name = '%(class)s_recipe'

    def __str__(self):
        return f'{self.user} - {self.recipe} [{self._meta.verbose_name}]'


class Favorite(AbstractFavoriteShoppingCart):
    class Meta(AbstractFavoriteShoppingCart.Meta):
        verbose_name = 'Избранное'
        verbose_name_plural = 'Избранные'


class ShoppingCart(AbstractFavoriteShoppingCart):
    class Meta(AbstractFavoriteShoppingCart.Meta):
        verbose_name = 'Список покупок'
        verbose_name_plural = 'Списки покупок'
