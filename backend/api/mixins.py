from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response

from recipes.models import Recipe


class CreateDeleteMixin:
    def create_obj(self,
                   serializer_class,
                   serializer_return,
                   model,
                   request,
                   pk):
        if model == Recipe:
            data = {'user': request.user.id, 'recipe': pk}
        else:
            data = {'user': request.user.id, 'author': pk}
        serializer = serializer_class(data=data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        object = get_object_or_404(model, pk=pk)
        serializer_data = serializer_return(
            object,
            context={'request': request}
        ).data
        return Response(
            data=serializer_data,
            status=status.HTTP_201_CREATED
        )

    def delete_obj(self, model, **kwargs):
        get_object_or_404(model, **kwargs).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
