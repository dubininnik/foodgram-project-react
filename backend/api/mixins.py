from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response


class CreateDeleteMixin:
    def create_obj(self, serializer_class, data, request):
        serializer = serializer_class(data=data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(status=status.HTTP_201_CREATED)

    def delete_obj(self, model, **kwargs):
        get_object_or_404(model, **kwargs).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
