from django.db.models import F, Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from djoser.views import UserViewSet as DjoserViewSet
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .filters import IngredientFilter, RecipeFilter
from .mixins import ListRetrieveViewSet
from .pagination import CustomPaginator
from .permissions import IsAuthorOrAdminOrReadOnly
from .serializers import (IngredientSerializer, RecipeCreateSerializer,
                          RecipeReadSerializer, RecipeSerializer,
                          SubscribeAuthorSerializer,
                          SubscriptionsSerializer, TagSerializer)
from recipes.models import (Favorite, Ingredient, Recipe, RecipeIngredient,
                            ShoppingCart, Tag)
from users.models import Subscribe, User


class UserViewSet(DjoserViewSet):
    queryset = User.objects.all()
    permission_classes = (AllowAny, IsAuthorOrAdminOrReadOnly)
    pagination_class = CustomPaginator

    @action(detail=False,
            methods=['get'],
            permission_classes=[IsAuthenticated])
    def me(self, request):
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)

    @action(detail=False,
            methods=['post'],
            permission_classes=[IsAuthenticated])
    def set_password(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response({'detail': 'Пароль успешно изменён.'})

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
            methods=['post', 'delete'],
            permission_classes=[IsAuthenticated])
    def subscribe(self, request, pk=None):
        author = get_object_or_404(User, id=pk)
        if request.method == 'POST':
            serializer = SubscribeAuthorSerializer(author,
                                                   data=request.data,
                                                   context={'request': request}
                                                   )
            serializer.is_valid(raise_exception=True)
            _, created = Subscribe.objects.get_or_create(user=request.user,
                                                         author=author)
            if created:
                return Response(serializer.data,
                                status=status.HTTP_201_CREATED)
            return Response('Подписка уже существует.',
                            status=status.HTTP_200_OK)
        get_object_or_404(Subscribe, user=request.user, author=author).delete()
        return self.delete(request, pk)

    def delete(self, request, pk=None):
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
    search_fields = ('^name',)
    permission_classes = (AllowAny, IsAuthorOrAdminOrReadOnly)


class TagViewSet(ListRetrieveViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    pagination_class = None


class RecipeViewSet(viewsets.ModelViewSet):
    queryset = Recipe.objects.all()
    pagination_class = CustomPaginator
    filter_backends = (filters.SearchFilter,)
    permission_classes = (IsAuthorOrAdminOrReadOnly,)
    filterset_class = RecipeFilter

    def get_serializer_class(self):
        if self.action:
            return RecipeReadSerializer
        return RecipeCreateSerializer

    def toggle_favorite_and_cart(
            self,
            request,
            recipe,
            serializer_class,
            related_field
    ):
        if request.method == 'POST':
            if not related_field.filter(
                    user=request.user, recipe=recipe).exists():
                related_field.create(user=request.user, recipe=recipe)
                serializer = serializer_class(
                    recipe, context={'request': request})
                return Response(serializer.data,
                                status=status.HTTP_201_CREATED)
            return Response(
                {'errors': 'Рецепт уже в избранном.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        related_field.filter(user=request.user, recipe=recipe).delete()
        return Response(
            {'detail': 'Рецепт успешно удален.'},
            status=status.HTTP_204_NO_CONTENT
        )

    @action(detail=True,
            methods=['post', 'delete'],
            permission_classes=(IsAuthenticated,)
            )
    def favorite(self, request, **kwargs):
        recipe = get_object_or_404(Recipe, id=kwargs['pk'])
        return self.toggle_favorite_and_cart(
            request,
            recipe,
            RecipeSerializer,
            Favorite.objects
        )

    @action(detail=True,
            methods=['post', 'delete'],
            permission_classes=(IsAuthenticated,)
            )
    def shopping_cart(self, request, pk=None):
        recipe = get_object_or_404(Recipe, id=pk)
        return self.toggle_favorite_and_cart(
            request,
            recipe,
            RecipeSerializer,
            ShoppingCart.objects
        )

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
