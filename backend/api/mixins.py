from rest_framework import mixins, status, viewsets
from rest_framework.response import Response

from .serializers import RecipeSerializer


class ListRetrieveViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet
):
    pass


class FavoriteAndCartMixin:
    related_field = None
    serializer_class = RecipeSerializer

    def create_favorite_and_cart(self, request, recipe):
        if not self.related_field.filter(
                user=request.user, recipe=recipe).exists():
            self.related_field.create(user=request.user, recipe=recipe)
            serializer = self.serializer_class(
                recipe, context={'request': request})
            return Response(serializer.data,
                            status=status.HTTP_201_CREATED)
        return Response(
            {'errors': 'Рецепт уже в избранном.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    def delete_favorite_and_cart(self, request, recipe):
        self.related_field.filter(user=request.user, recipe=recipe).delete()
        return Response(
            {'detail': 'Рецепт успешно удален.'},
            status=status.HTTP_204_NO_CONTENT
        )


class FavoriteMixin(FavoriteAndCartMixin):
    related_field = 'favorite_recipe'


class ShoppingCartMixin(FavoriteAndCartMixin):
    related_field = 'shopping_recipe'
