from django.contrib import admin

from . import models


class UserInline(admin.StackedInline):
    model = models.User
    can_delete = False
    verbose_name_plural = 'Пользователи'


@admin.register(models.User)
class UserAdmin(admin.ModelAdmin):

    def save_model(self, request, obj, form, change):
        obj.set_password(obj.password)
        obj.save()

    inlines = (UserInline,)

    list_display = (
        'pk',
        'is_active',
        'username',
        'password',
        'email',
        'first_name',
        'last_name',
    )
    list_editable = (
        'is_active',
        'password',
    )
    list_filter = (
        'username',
        'email',
    )
    search_fields = (
        'username',
        'email',
    )


@admin.register(models.Subscribe)
class SubscribeAdmin(admin.ModelAdmin):
    list_display = (
        'pk',
        'user',
        'author',
    )
    list_editable = (
        'user',
        'author',
    )
