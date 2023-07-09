from django.contrib.auth.password_validation import validate_password
from django.db import transaction
from djoser.serializers import UserCreateSerializer, UserSerializer
from rest_framework import serializers

from api.fields import Base64ImageField
from recipes.models import (Favorite, Ingredient, Recipe,
                            RecipeIngredient, ShoppingCart, Tag)
from users.models import Subscribe, User


class UserCreateSerializer(UserCreateSerializer):
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
                  'last_name', 'password')

    def get_is_subscribed(self, obj):
        request = self.context.get('request')
        if request and not request.user.is_anonymous:
            return Subscribe.objects.filter(
                user=request.user, author=obj).exists()
        return False


class SetPasswordSerializer(serializers.Serializer):
    """[POST] Изменение пароля пользователя."""
    new_password = serializers.CharField(write_only=True)
    current_password = serializers.CharField(write_only=True)

    def validate(self, data):
        new_password = data.get('new_password')
        try:
            validate_password(new_password)
        except Exception as error:
            raise serializers.ValidationError(
                {'new_password': list(error)}
            )
        return data

    def update(self, instance, validated_data):
        if not instance.check_password(validated_data['current_password']):
            raise serializers.ValidationError(
                {'current_password': 'Неверный пароль.'}
            )
        if (validated_data['current_password']
                == validated_data['new_password']):
            raise serializers.ValidationError(
                {'new_password': 'Новый пароль должен отличаться от текущего.'}
            )
        instance.set_password(validated_data['new_password'])
        instance.save()
        return validated_data


class RecipeSerializer(serializers.ModelSerializer):
    """[GET] Список рецептов без ингредиентов."""
    image = Base64ImageField(
        required=False,
        allow_null=True,
    )
    name = serializers.ReadOnlyField()
    cooking_time = serializers.ReadOnlyField()

    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')


class SubscriptionsSerializer(serializers.ModelSerializer):
    """[GET] Список авторов на которых подписан пользователь."""
    is_subscribed = serializers.SerializerMethodField()
    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ('email', 'id', 'username', 'first_name',
                  'last_name', 'recipes', 'recipes_count', 'is_subscribed')

    def get_is_subscribed(self, obj):
        user = self.context.get('request').user
        return user.is_authenticated and user.subscriber.filter(
            user=user, author=obj
        ).exists()

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
        fields = '__all__'


class TagSerializer(serializers.ModelSerializer):
    """[GET] Список тегов."""
    class Meta:
        model = Tag
        fields = '__all__'


class RecipeIngredientSerializer(serializers.ModelSerializer):
    """[GET] Список ингредиентов с количеством для конкретного рецепта."""
    id = serializers.ReadOnlyField(source='ingredient.id')
    name = serializers.ReadOnlyField(source='ingredient.name')
    measurement_unit = serializers.ReadOnlyField(
        source='ingredient.measurement_unit'
    )

    class Meta:
        model = RecipeIngredient
        fields = ('id', 'name', 'measurement_unit', 'amount')


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
    image = Base64ImageField(
        required=False,
        allow_null=True
    )

    class Meta:
        model = Recipe
        fields = ('id', 'tags', 'author', 'ingredients',
                  'is_favorited', 'is_in_shopping_cart',
                  'name', 'image', 'text', 'cooking_time')

    def get_is_favorited(self, obj):
        user = self.context.get('request').user
        return user.is_authenticated and Favorite.objects.filter(
            user=user, recipe=obj
        ).exists()

    def get_is_in_shopping_cart(self, obj):
        user = self.context.get('request').user
        return user.is_authenticated and ShoppingCart.objects.filter(
            user=user, recipe=obj
        ).exists()


class RecipeIngredientCreateSerializer(serializers.ModelSerializer):
    """Ингредиент и количество для создания рецепта."""
    id = serializers.IntegerField()

    class Meta:
        model = RecipeIngredient
        fields = ('id', 'amount')


class RecipeCreateSerializer(serializers.ModelSerializer):
    """[POST, PATCH, DELETE] Создание, изменение и удаление рецепта."""
    tags = serializers.ListField(
        child=serializers.PrimaryKeyRelatedField(queryset=Tag.objects.all()),
        write_only=True
    )
    author = UserReadSerializer(read_only=True)
    id = serializers.ReadOnlyField()
    ingredients = serializers.ListField(
        child=RecipeIngredientCreateSerializer(),
        write_only=True
    )
    image = Base64ImageField()

    class Meta:
        model = Recipe
        fields = ('id', 'ingredients', 'tags', 'image',
                  'name', 'text', 'cooking_time', 'author')
        extra_kwargs = {
            'ingredients': {'required': True, 'allow_blank': False},
            'tags': {'required': True, 'allow_blank': False},
            'name': {'required': True, 'allow_blank': False},
            'text': {'required': True, 'allow_blank': False},
            'image': {'required': True, 'allow_blank': False},
        }

    def validate(self, attrs):
        if 'cooking_time' not in attrs or attrs['cooking_time'] is None:
            raise serializers.ValidationError(
                'cooking_time - Обязательное поле.'
            )
        if not attrs.get('tags'):
            raise serializers.ValidationError('Нужно указать минимум 1 тег.')
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

    def tags_and_ingredients_set(self, recipe, tags, ingredients):
        recipe.tags.set(tags)
        RecipeIngredient.objects.bulk_create(
            [
                RecipeIngredient(
                    recipe=recipe,
                    ingredient_id=ingredient['id'],
                    amount=ingredient['amount']
                ) for ingredient in ingredients
            ]
        )

    @transaction.atomic
    def create(self, validated_data):
        tags = validated_data.pop('tags')
        ingredients = validated_data.pop('ingredients')
        recipe = Recipe.objects.create(
            author=self.context['request'].user,
            **validated_data)
        self.tags_and_ingredients_set(recipe, tags, ingredients)
        return recipe

    @transaction.atomic
    def update(self, instance, validated_data):
        tags_data = validated_data.pop('tags')
        ingredients_data = validated_data.pop('ingredients')
        instance = super().update(instance, validated_data)
        instance.tags.clear()
        instance.tags.add(*tags_data)
        instance.ingredients.clear()
        for ingredient_data in ingredients_data:
            RecipeIngredient.objects.update_or_create(
                recipe=instance,
                ingredient_id=ingredient_data['id'],
                defaults={'amount': ingredient_data['amount']}
            )
        return instance

    def to_representation(self, instance):
        return RecipeReadSerializer(instance, context=self.context).data
