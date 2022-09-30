from django.conf import settings
from django.utils.translation import gettext as _

from rest_framework import serializers

from . import models, utils


class NodeSerializer(serializers.ModelSerializer):

    state = serializers.SerializerMethodField()

    class Meta:
        model = models.Node
        fields = (
            'id',
            'name',
            'logic_class',
            'settings',
            'state',
        )

    def get_state(self, obj):
        return obj.get_state()

    def create(self, validated_data):
        # Validate logic class
        logic_class = validated_data.get('logic_class')
        if logic_class not in settings.NODE_LOGIC_CLASSES:
            raise serializers.ValidationError({'logic_class': _('Invalid logic class!')})

        logic_cls = utils.import_dot_path(logic_class)
        logic = logic_cls(None)

        # Validate settings
        node_settings = validated_data.get('settings')
        node_settings_error = logic.get_settings_error(node_settings)
        if node_settings_error:
            raise serializers.ValidationError({'settings': node_settings_error})

        return super().create(validated_data)

    def update(self, instance, validated_data):
        # Logic class may not be changed
        if 'logic_class' in validated_data:
            raise serializers.ValidationError({'logic_class': _('Logic class may not be changed!')})

        logic = instance.get_logic()

        # Validate settings
        node_settings = validated_data.get('settings')
        if node_settings:
            node_settings_error = logic.get_settings_error(node_settings)
            if node_settings_error:
                raise serializers.ValidationError({'settings': node_settings_error})

        return super().update(instance, validated_data)
