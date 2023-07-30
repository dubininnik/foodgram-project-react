from rest_framework import status
from rest_framework.response import Response


class CreateDeleteMixin:
    def create(self, request, serializer_class, *args, **kwargs):
        serializer = serializer_class(data=request.data)
        if serializer.is_valid():
            obj = serializer.save()
            if not self.related_field.filter(user=request.user,
                                             obj=obj).exists():
                self.related_field.create(user=request.user, obj=obj)
                return Response(serializer.data,
                                status=status.HTTP_201_CREATED)
            return Response({'errors': 'Объект уже в избранном.'},
                            status=status.HTTP_400_BAD_REQUEST)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, serializer_class, *args, **kwargs):
        serializer = serializer_class(data=request.data)
        if serializer.is_valid():
            obj = serializer.save()
            self.related_field.filter(user=request.user, obj=obj).delete()
            return Response({'detail': 'Объект успешно удалён.'},
                            status=status.HTTP_204_NO_CONTENT)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
