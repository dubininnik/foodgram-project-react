from django.db.models import F, Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from djoser.views import UserViewSet as DjoserViewSet
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .filters import IngredientFilter, RecipeFilter
from .mixins import FavoriteMixin, ListRetrieveViewSet, ShoppingCartMixin
from .pagination import CustomPaginator
from .permissions import IsAuthorOrAdminOrReadOnly
from .serializers import (IngredientSerializer, RecipeCreateSerializer,
                          SubscribeAuthorSerializer, SubscriptionsSerializer,
                          TagSerializer)
from recipes.models import Ingredient, Recipe, RecipeIngredient, Tag
from users.models import Subscribe, User


class UserViewSet(DjoserViewSet, FavoriteMixin):
    queryset = User.objects.all()
    permission_classes = (AllowAny, IsAuthorOrAdminOrReadOnly)

    @action(detail=True,
            methods=['post'],
            permission_classes=[IsAuthenticated])
    def favorite(self, request, **kwargs):
        recipe = get_object_or_404(Recipe, id=kwargs['pk'])
        return self.create_favorite_and_cart(request, recipe)

    @action(detail=True,
            methods=['delete'],
            permission_classes=[IsAuthenticated])
    def unfavorite(self, request, **kwargs):
        recipe = get_object_or_404(Recipe, id=kwargs['pk'])
        return self.delete_favorite_and_cart(request, recipe)

    @action(detail=False,
            methods=['get'],
            permission_classes=[IsAuthenticated])
    def subscriptions(self, request):
        queryset = User.objects.filter(subscribing__user=request.user)
        page = self.paginate_queryset(queryset)
        serializer = SubscriptionsSerializer(page,
                                             many=True,
                                             context={'request': request})
        return self.get_paginated_response(serializer.data)

    @action(detail=True,
            methods=['post'],
            permission_classes=[IsAuthenticated])
    def subscribe(self, request, pk=None):
        author = get_object_or_404(User, id=pk)
        serializer = SubscribeAuthorSerializer(author,
                                               data=request.data,
                                               context={'request': request}
                                               )
        serializer.is_valid(raise_exception=True)
        serializer.save(user=request.user, author=author)
        return Response(serializer.data,
                        status=status.HTTP_201_CREATED)

    @action(detail=True,
            methods=['delete'],
            permission_classes=[IsAuthenticated])
    def unsubscribe(self, request, pk=None):
        author = get_object_or_404(User, id=pk)
        subscription = get_object_or_404(Subscribe,
                                         user=request.user,
                                         author=author)
        subscription.delete()
        return Response({'detail': 'Подписка успешно удалена.'})


class IngredientViewSet(ListRetrieveViewSet):
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    pagination_class = None
    filter_backends = (IngredientFilter,)
    permission_classes = (AllowAny, IsAuthorOrAdminOrReadOnly)


class TagViewSet(ListRetrieveViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    pagination_class = None


class RecipeViewSet(viewsets.ModelViewSet, FavoriteMixin, ShoppingCartMixin):
    queryset = Recipe.objects.all()
    serializer_class = RecipeCreateSerializer
    pagination_class = CustomPaginator
    filter_backends = (filters.SearchFilter,)
    permission_classes = (IsAuthorOrAdminOrReadOnly,)
    filterset_class = RecipeFilter

    @action(detail=True,
            methods=['post'],
            permission_classes=(IsAuthenticated,))
    def favorite(self, request, **kwargs):
        recipe = get_object_or_404(Recipe, id=kwargs['pk'])
        return self.create_favorite_and_cart(request, recipe)

    @action(detail=True,
            methods=['delete'],
            permission_classes=(IsAuthenticated,))
    def unfavorite(self, request, **kwargs):
        recipe = get_object_or_404(Recipe, id=kwargs['pk'])
        return self.delete_favorite_and_cart(request, recipe)

    @action(detail=True,
            methods=['post'],
            permission_classes=(IsAuthenticated,))
    def shopping_cart(self, request, pk=None):
        recipe = get_object_or_404(Recipe, id=pk)
        return self.create_favorite_and_cart(request, recipe)

    @action(detail=True,
            methods=['delete'],
            permission_classes=(IsAuthenticated,))
    def remove_from_cart(self, request, pk=None):
        recipe = get_object_or_404(Recipe, id=pk)
        return self.delete_favorite_and_cart(request, recipe)

    @action(detail=False,
            methods=['get'],
            permission_classes=(IsAuthenticated,)
            )
    def download_shopping_cart(self, request):
        ingredients = (
            RecipeIngredient.objects
            .filter(recipe__shopping_recipe__user=request.user)
            .values(name=F('ingredient__name'),
                    amount_sum=Sum('amount'),
                    unit=F('ingredient__measurement_unit'))
        )
        shopping_cart = []
        for ingredient in ingredients:
            shopping_cart.append(
                f'{ingredient["name"]} - {ingredient["unit"]} '
                f'{ingredient["amount_sum"]}'
            )
        shopping_cart = '\n'.join(shopping_cart)
        response = HttpResponse(shopping_cart, 'Content-Type: text/plain')
        response['Content-Disposition'] = 'attachment; filename="wishlist.txt"'
        return response
