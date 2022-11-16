from django.contrib import admin

from . import models


@admin.register(models.Variable)
class VariableAdmin(admin.ModelAdmin):
    pass
