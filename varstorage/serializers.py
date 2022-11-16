from rest_framework import serializers

from . import models


class VariableSerializer(serializers.ModelSerializer):

    class Meta:
        model = models.Variable
        fields = (
            'name',
            'value',
        )
