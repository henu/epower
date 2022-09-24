from django.contrib import admin

from . import models


@admin.register(models.Node)
class NodeAdmin(admin.ModelAdmin):

    readonly_fields = (
        'get_state',
    )


@admin.register(models.Connection)
class ConnectionAdmin(admin.ModelAdmin):
    pass
