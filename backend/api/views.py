from django.db.models import F, Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from djoser.views import UserViewSet as DjoserViewSet
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ReadOnlyModelViewSet

from .filters import IngredientFilter, RecipeFilter
from .mixins import CreateDeleteMixin
from .permissions import IsAuthorOrAdminOrReadOnly
from .serializers import (IngredientSerializer, RecipeCreateSerializer,
                          SubscribeAuthorSerializer, SubscriptionsSerializer,
                          TagSerializer)
from recipes.models import Ingredient, Recipe, RecipeIngredient, Tag
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
        serializer = SubscriptionsSerializer(page,
                                             many=True,
                                             context={'request': request})
        return self.get_paginated_response(serializer.data)

    @action(detail=True,
            methods=['post'],
            permission_classes=[IsAuthenticated])
    def subscribe(self, request, pk=None):
        author = get_object_or_404(User, id=pk)
        serializer_class = SubscribeAuthorSerializer(
            author,
            data=request.data,
            context={'request': request}
        )
        return self.create(request,
                           serializer_class,
                           related_field=Subscribe.objects,
                           obj=author)

    @subscribe.mapping.delete
    def unsubscribe(self, request, pk=None):
        author = get_object_or_404(User, id=pk)
        serializer_class = SubscribeAuthorSerializer(
            author,
            data=request.data,
            context={'request': request}
        )
        return self.delete(request,
                           serializer_class,
                           related_field=Subscribe.objects,
                           obj=author)


class IngredientViewSet(ReadOnlyModelViewSet):
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    pagination_class = None
    filter_backends = (IngredientFilter,)
    search_fields = ('^name',)  # Работает только так :(
    permission_classes = (AllowAny, IsAuthorOrAdminOrReadOnly)


class TagViewSet(ReadOnlyModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    pagination_class = None


class RecipeViewSet(CreateDeleteMixin, viewsets.ModelViewSet):
    queryset = Recipe.objects.all()
    serializer_class = RecipeCreateSerializer
    filter_backends = (filters.SearchFilter,)
    permission_classes = (IsAuthorOrAdminOrReadOnly,)
    filterset_class = RecipeFilter

    @action(detail=True,
            methods=['post'],
            permission_classes=(IsAuthenticated,))
    def favorite(self, request, **kwargs):
        recipe = get_object_or_404(Recipe, id=kwargs['pk'])
        serializer = self.get_serializer(
            data=request.data,
            context={'request': request, 'recipe': recipe}
        )
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @favorite.mapping.delete
    def unfavorite(self, request, **kwargs):
        recipe = get_object_or_404(Recipe, id=kwargs['pk'])
        serializer = self.get_serializer(
            data=request.data,
            context={'request': request, 'recipe': recipe}
        )
        serializer.is_valid(raise_exception=True)
        self.perform_destroy(serializer)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True,
            methods=['post'],
            permission_classes=(IsAuthenticated,))
    def shopping_cart(self, request, pk=None):
        recipe = get_object_or_404(Recipe, id=pk)
        serializer = self.get_serializer(
            data=request.data,
            context={'request': request, 'recipe': recipe}
        )
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @shopping_cart.mapping.delete
    def remove_from_cart(self, request, pk=None):
        recipe = get_object_or_404(Recipe, id=pk)
        serializer = self.get_serializer(
            data=request.data,
            context={'request': request, 'recipe': recipe}
        )
        serializer.is_valid(raise_exception=True)
        self.perform_destroy(serializer)
        return Response(status=status.HTTP_204_NO_CONTENT)

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
