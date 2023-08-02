from django.db import transaction
from djoser.serializers import UserCreateSerializer, UserSerializer
from drf_extra_fields.fields import Base64ImageField
from rest_framework import serializers

from recipes.models import (Favorite, Ingredient, ShoppingCart,
                            Recipe, RecipeIngredient, Tag)
from users.models import User


class CustomUserCreateSerializer(UserCreateSerializer):
    """[POST] Создание нового пользователя."""

    class Meta(UserCreateSerializer.Meta):
        fields = ('email', 'id', 'username', 'first_name',
                  'last_name', 'password')


class UserReadSerializer(UserSerializer):
    """[GET] Список пользователей."""
    is_subscribed = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ('id', 'email', 'username', 'first_name',
                  'last_name', 'password', 'is_subscribed')

    def get_is_subscribed(self, obj):
        request = self.context.get('request')
        if not request.user.is_authenticated:
            return False
        return obj.subscriber.filter(user=request.user).exists()


class RecipeSerializer(serializers.ModelSerializer):
    """[GET] Список рецептов без ингредиентов."""
    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')


class SubscriptionsSerializer(UserReadSerializer):
    """[GET] Список авторов на которых подписан пользователь."""
    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.IntegerField(source='recipes_count')

    class Meta:
        model = User
        fields = ('email', 'id', 'username', 'first_name',
                  'last_name', 'recipes', 'recipes_count', 'is_subscribed')

    def get_recipes_count(self, obj):
        return obj.recipes.count()

    def get_recipes(self, obj):
        request = self.context.get('request')
        limit = request.GET.get('recipes_limit')
        recipes = obj.recipes.all()
        if limit:
            recipes = recipes[:int(limit)]
        serializer = RecipeSerializer(recipes, many=True, read_only=True)
        return serializer.data


class FavoriteSerializer(serializers.ModelSerializer):
    """[GET] Список избранного."""
    class Meta:
        model = Favorite
        fields = ('id', 'user', 'recipe')


class ShoppingCartSerializer(serializers.ModelSerializer):
    """[GET] Список содержимого корзины покупок."""
    class Meta:
        model = ShoppingCart
        fields = ('id', 'user', 'recipe')


class SubscribeAuthorSerializer(serializers.ModelSerializer):
    """[POST, DELETE] Подписка и отписка на авторов."""
    email = serializers.ReadOnlyField(source='author.email')
    id = serializers.ReadOnlyField(source='author.id')
    username = serializers.ReadOnlyField(source='author.username')
    first_name = serializers.ReadOnlyField(source='author.first_name')
    last_name = serializers.ReadOnlyField(source='author.last_name')
    recipes = RecipeSerializer(
        many=True,
        read_only=True
    )
    recipes_count = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ('email', 'id', 'username', 'first_name',
                  'last_name', 'recipes', 'recipes_count')

    def validate(self, obj):
        request = self.context['request']
        author = obj['author']
        if request.user == author:
            raise serializers.ValidationError('Нельзя подписаться на себя')
        if obj.subscriber.filter(user=request.user).exists():
            raise serializers.ValidationError('Подписка уже оформлена')
        return obj

    def get_is_subscribed(self, obj):
        return (self.context.get('request').user.is_authenticated
                and obj.subscriber.filter(
                    user=self.context['request'].user).exists()
                )

    def get_recipes_count(self, obj):
        return obj.recipes.count()


class IngredientSerializer(serializers.ModelSerializer):
    """[GET] Список ингредиентов."""
    class Meta:
        model = Ingredient
        fields = ('id', 'name', 'measurement_unit')


class TagSerializer(serializers.ModelSerializer):
    """[GET] Список тегов."""
    class Meta:
        model = Tag
        fields = ('id', 'name', 'color', 'slug')


class RecipeIngredientSerializer(serializers.ModelSerializer):
    """[GET] Список ингредиентов с количеством для конкретного рецепта."""
    name = serializers.ReadOnlyField(source='ingredient.name')
    measurement_unit = serializers.ReadOnlyField(
        source='ingredient.measurement_unit'
    )

    class Meta:
        model = RecipeIngredient
        fields = ('id', 'name', 'measurement_unit', 'amount')


class RecipeCreateSerializer(serializers.ModelSerializer):
    """[GET, POST, PATCH, DELETE]Чтение, создание,
    изменение, удаление рецепта."""
    author = UserReadSerializer(read_only=True)
    image = Base64ImageField()
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()

    class Meta:
        model = Recipe
        fields = ('id', 'tags', 'author', 'ingredients',
                  'is_favorited', 'is_in_shopping_cart',
                  'name', 'image', 'text', 'cooking_time')

    def get_is_favorited(self, obj):
        user = self.context.get('request').user
        return obj.favorite_recipe.filter(user=user).exists()

    def get_is_in_shopping_cart(self, obj):
        user = self.context.get('request').user
        return obj.shoppingcart_recipe.filter(user=user).exists()

    def validate_tags(self, data):
        tags = self.initial_data.get('tags')
        if not tags:
            raise serializers.ValidationError('Нужно указать минимум 1 тег.')
        return data

    def validate_ingredients(self, data):
        ingredients = self.initial_data.get('ingredients')
        if not ingredients:
            raise serializers.ValidationError(
                'Нужно указать минимум 1 ингредиент.'
            )
        ingredient_ids = [ingredient['id'] for ingredient in ingredients]
        if len(ingredient_ids) != len(set(ingredient_ids)):
            raise serializers.ValidationError(
                'Ингредиенты должны быть уникальны.'
            )
        return data

    def create_and_update_recipe(self, recipe, ingredients):
        recipe_ingredients = []
        for ingredient in ingredients:
            recipe_ingredient = RecipeIngredient(
                recipe=recipe,
                ingredient_id=ingredient['id'],
                amount=int(ingredient['amount'])
            )
            recipe_ingredients.append(recipe_ingredient)
        RecipeIngredient.objects.bulk_create(recipe_ingredients)

    @transaction.atomic
    def create(self, validated_data):
        tags = validated_data.pop('tags', [])
        ingredients = validated_data.get('ingredients', [])
        recipe = Recipe.objects.create(
            author=self.context['request'].user,
            **validated_data
        )
        recipe.tags.set(tags)
        self.create_and_update_recipe(recipe, ingredients)
        return recipe

    @transaction.atomic
    def update(self, instance, validated_data):
        tags = validated_data.pop('tags', [])
        ingredients = validated_data.pop('ingredients', [])
        instance.tags.set(tags)
        instance.ingredients.clear()
        self.create_and_update_recipe(instance, ingredients)
        return super().update(instance, validated_data)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['ingredients'] = RecipeIngredientSerializer(
            instance.recipes.all(), many=True).data
        data['tags'] = TagSerializer(instance.tags, many=True).data
        return data

    def to_internal_value(self, data):
        internal_value = super().to_internal_value(data)
        ingredients = data.get('ingredients')
        internal_value['ingredients'] = ingredients
        tags = data.get('tags')
        internal_value['tags'] = tags
        return internal_value
