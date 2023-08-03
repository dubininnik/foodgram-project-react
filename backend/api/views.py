from django.db.models import F, Sum
from django.http import HttpResponse
from django_filters.rest_framework import DjangoFilterBackend
from djoser.views import UserViewSet as DjoserViewSet
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.viewsets import ReadOnlyModelViewSet

from .filters import IngredientFilter, RecipeFilter
from .mixins import CreateDeleteMixin
from .permissions import IsAuthorOrAdminOrReadOnly
from .serializers import (FavoriteSerializer, IngredientSerializer,
                          RecipeCreateSerializer, ShoppingCartSerializer,
                          SubscribeAuthorSerializer, SubscriptionSerializer,
                          TagSerializer)
from recipes.models import (Favorite, Ingredient, Recipe,
                            RecipeIngredient, ShoppingCart, Tag)
from users.models import Subscribe, User


class UserViewSet(CreateDeleteMixin, DjoserViewSet):
    queryset = User.objects.all()
    permission_classes = (AllowAny, IsAuthorOrAdminOrReadOnly)

    @action(detail=False,
            methods=['get'],
            permission_classes=[IsAuthenticated])
    def subscriptions(self, request):
        queryset = User.objects.filter(subscribing__user=request.user)
        page = self.paginate_queryset(queryset)
        serializer = SubscriptionSerializer(
            [subscription.author for subscription in page],
            many=True,
            context={'request': request}
        )
        return self.get_paginated_response(serializer.data)

    @action(detail=True,
            methods=['post'],
            permission_classes=[IsAuthenticated])
    def subscribe(self, request, id):
        data = {'user': self.request.user.id, 'author': id}
        return self.create_obj(SubscribeAuthorSerializer, data, request)

    @subscribe.mapping.delete
    def unsubscribe(self, request, id):
        return self.delete_obj(Subscribe,
                               user=request.user,
                               author__id=id)


class IngredientViewSet(ReadOnlyModelViewSet):
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    pagination_class = None
    filterset_class = IngredientFilter
    permission_classes = (AllowAny, IsAuthorOrAdminOrReadOnly)


class TagViewSet(ReadOnlyModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    pagination_class = None


class RecipeViewSet(CreateDeleteMixin, viewsets.ModelViewSet):
    queryset = Recipe.objects.all()
    serializer_class = RecipeCreateSerializer
    filterset_class = RecipeFilter
    filter_backends = (DjangoFilterBackend,)
    permission_classes = (IsAuthorOrAdminOrReadOnly,)

    @action(detail=True,
            methods=['post'],
            permission_classes=(IsAuthenticated,))
    def favorite(self, request, pk):
        data = {'user': request.user.id, 'recipe': pk}
        return self.create_obj(FavoriteSerializer, data, request)

    @favorite.mapping.delete
    def unfavorite(self, request, pk):
        return self.delete_obj(Favorite, user=request.user, recipe=pk)

    @action(detail=True,
            methods=['post'],
            permission_classes=(IsAuthenticated,))
    def shopping_cart(self, request, pk):
        data = {'user': request.user.id, 'recipe': pk}
        return self.create_obj(ShoppingCartSerializer, data, pk)

    @shopping_cart.mapping.delete
    def remove_from_cart(self, request, pk):
        return self.delete_obj(ShoppingCart, user=request.user, recipe=pk)

    @action(detail=False,
            methods=['get'],
            permission_classes=(IsAuthenticated,)
            )
    def download_shopping_cart(self, request):
        shopping_cart_recipes = (ShoppingCart.objects.
                                 filter(user=request.user).
                                 values_list('recipe', flat=True))
        ingredients = (RecipeIngredient.objects
                       .filter(recipe__in=shopping_cart_recipes)
                       .values(name=F('ingredient__name'),
                               unit=F('ingredient__measurement_unit'))
                       .annotate(amount_sum=Sum('amount'))
                       ).order_by('name')
        shopping_cart = '\n'.join([
            f'{ingredient["name"]} - {ingredient["unit"]} '
            f'{ingredient["amount_sum"]}'
            for ingredient in ingredients
        ])
        response = HttpResponse(content_type='text/plain')
        response['Content-Disposition'] = ('attachment; '
                                           'filename="shopping-cart.txt"')
        response.write(shopping_cart)
        return response
