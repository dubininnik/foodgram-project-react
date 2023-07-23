from django.db import transaction
from djoser.serializers import (SetPasswordSerializer,
                                UserCreateSerializer,
                                UserSerializer)
from rest_framework import serializers

from drf_extra_fields.fields import Base64ImageField
from recipes.models import (Ingredient, Recipe,
                            RecipeIngredient, Tag)
from users.models import Subscribe, User


class CustomUserCreateSerializer(UserCreateSerializer):
    """[POST] Создание нового пользователя."""
    password = serializers.CharField(
        style={
            'input_type': 'password',
        },
        write_only=True,
    )

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
        return Subscribe.objects.filter(
            user=request.user, author=obj).exists()


class CustomSetPasswordSerializer(SetPasswordSerializer):
    """[POST] Изменение пароля пользователя."""
    new_password = serializers.CharField(write_only=True)
    current_password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        return super().validate(attrs)


class RecipeSerializer(serializers.ModelSerializer):
    """[GET] Список рецептов без ингредиентов."""
    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')


class SubscriptionsSerializer(serializers.ModelSerializer):
    """[GET] Список авторов на которых подписан пользователь."""
    is_subscribed = serializers.SerializerMethodField()
    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.IntegerField(source='recipes_count')

    class Meta:
        model = User
        fields = ('email', 'id', 'username', 'first_name',
                  'last_name', 'recipes', 'recipes_count', 'is_subscribed')

    def get_is_subscribed(self, obj):
        return obj

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        user = self.context.get('request').user
        is_subscribed = False
        if user.is_authenticated:
            is_subscribed = Subscribe.objects.filter(
                user=user,
                author=instance
            ).exists()
        representation['is_subscribed'] = is_subscribed
        return representation

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
        if (self.context['request'].user == obj):
            raise serializers.ValidationError({'errors': 'Ошибка подписки.'})
        return obj

    def get_is_subscribed(self, obj):
        return (self.context.get('request').user.is_authenticated
                and Subscribe.objects.filter(user=self.context['request'].user,
                                             author=obj).exists()
                )

    def get_recipes_count(self, obj):
        return obj.recipes.count()


class IngredientSerializer(serializers.ModelSerializer):
    """[GET] Список ингредиентов."""
    class Meta:
        model = Ingredient
        fields = ('name', 'measurement_unit')
        read_only_fields = ('name', 'measurement_unit')


class TagSerializer(serializers.ModelSerializer):
    """[GET] Список тегов."""
    class Meta:
        model = Tag
        fields = ('name', 'color', 'slug')
        read_only_fields = ('name', 'color', 'slug')


class RecipeIngredientSerializer(serializers.ModelSerializer):
    """[GET] Список ингредиентов с количеством для конкретного рецепта."""
    ingredient_id = serializers.ReadOnlyField(source='ingredient.id')
    name = serializers.ReadOnlyField(source='ingredient.name')
    measurement_unit = serializers.ReadOnlyField(
        source='ingredient.measurement_unit'
    )

    class Meta:
        model = RecipeIngredient
        fields = ('ingredient_id', 'name', 'measurement_unit', 'amount')


class RecipeReadSerializer(serializers.ModelSerializer):
    """[GET] Список рецептов с ингредиентами."""
    tags = TagSerializer(many=True, read_only=True)
    author = UserReadSerializer(read_only=True)
    ingredients = RecipeIngredientSerializer(
        many=True,
        read_only=True,
        source='recipes'
    )
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
        return obj.shopping_recipe.filter(user=user).exists()


class RecipeCreateSerializer(serializers.ModelSerializer):
    """[POST, PATCH, DELETE] Создание, изменение и удаление рецепта."""
    tags = serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.all(),
        write_only=True
    )
    author = UserReadSerializer(read_only=True)
    ingredients = serializers.PrimaryKeyRelatedField(
        queryset=Ingredient.objects.all(),
        write_only=True
    )
    image = Base64ImageField()

    class Meta:
        model = Recipe
        fields = ('id', 'ingredients', 'tags', 'image',
                  'name', 'text', 'cooking_time', 'author')

    def tag_validate(self, attrs):
        if not attrs.get('tags'):
            raise serializers.ValidationError('Нужно указать минимум 1 тег.')

    def ingredient_validate(self, attrs):
        if not attrs.get('ingredients'):
            raise serializers.ValidationError(
                'Нужно указать минимум 1 ингредиент.'
            )
        ingredient_ids = [item['id'] for item in attrs.get('ingredients')]
        if len(ingredient_ids) != len(set(ingredient_ids)):
            raise serializers.ValidationError(
                'Ингредиенты должны быть уникальны.'
            )
        return attrs

    def set_recipe_tags(self, recipe, tags):
        recipe.tags.set(tags)

    def set_recipe_ingredients(self, recipe, ingredients):
        RecipeIngredient.objects.filter(recipe=recipe).delete()
        recipe_ingredients = [
            RecipeIngredient(
                recipe=recipe,
                ingredient_id=ingredient['id'],
                amount=ingredient['amount']
            ) for ingredient in ingredients
        ]
        RecipeIngredient.objects.bulk_create(recipe_ingredients)

    @transaction.atomic
    def create(self, validated_data):
        tags = validated_data.pop('tags')
        ingredients = validated_data.pop('ingredients')
        recipe = Recipe.objects.create(
            author=self.context['request'].user,
            **validated_data)
        self.set_recipe_tags(recipe, tags)
        self.set_recipe_ingredients(recipe, ingredients)
        return recipe

    @transaction.atomic
    def update(self, instance, validated_data):
        tags = validated_data.pop('tags')
        ingredients = validated_data.pop('ingredients')
        instance = super().update(instance, validated_data)
        self.set_recipe_tags(instance, tags)
        self.set_recipe_ingredients(instance, ingredients)
        return instance

    def to_representation(self, instance):
        return RecipeReadSerializer(instance, context=self.context).data
