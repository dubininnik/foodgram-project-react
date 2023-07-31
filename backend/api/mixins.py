from rest_framework import status
from rest_framework.response import Response


class CreateDeleteMixin:
    def create(self, request, serializer, related_obj, *args, **kwargs):
        if serializer.is_valid():
            obj = serializer.save()
            _, created = related_obj.get_or_create(user=request.user, obj=obj)
            if created:
                return Response(serializer.data,
                                status=status.HTTP_201_CREATED)
            return Response({'errors': 'Объект уже в избранном.'},
                            status=status.HTTP_400_BAD_REQUEST)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, serializer, related_obj, *args, **kwargs):
        if serializer.is_valid():
            obj = serializer.save()
            related_obj.filter(user=request.user, obj=obj).delete()
            return Response({'detail': 'Объект успешно удалён.'},
                            status=status.HTTP_204_NO_CONTENT)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
