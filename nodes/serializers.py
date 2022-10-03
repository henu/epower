from django.conf import settings
from django.utils.translation import gettext as _

from rest_framework import serializers

from . import models, utils


class NodeSerializer(serializers.ModelSerializer):

    state = serializers.SerializerMethodField()
    inputs = serializers.SerializerMethodField()
    outputs = serializers.SerializerMethodField()

    class Meta:
        model = models.Node
        fields = (
            'id',
            'name',
            'logic_class',
            'settings',
            'pos_x',
            'pos_y',
            'state',
            'inputs',
            'outputs',
        )

    def get_state(self, obj):
        return obj.get_state()

    def get_inputs(self, obj):
        logic = obj.get_logic()
        return sorted(logic.get_input_keys())

    def get_outputs(self, obj):
        logic = obj.get_logic()
        return sorted(logic.get_output_keys())

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


class ConnectionSerializer(serializers.ModelSerializer):

    class Meta:
        model = models.Connection
        fields = (
            'id',
            'source',
            'source_key',
            'dest',
            'dest_key',
        )

    def get_state(self, obj):
        return obj.get_state()

    def create(self, validated_data):
        # Validate source and destination keys exist
        if not self._node_key_exists(validated_data.get('source'), validated_data.get('source_key'), True):
            raise serializers.ValidationError({'source_key': _('Invalid source key!')})
        if not self._node_key_exists(validated_data.get('dest'), validated_data.get('dest_key'), False):
            raise serializers.ValidationError({'dest_key': _('Invalid destination key!')})

        return super().create(validated_data)

    def update(self, instance, validated_data):
        # Validate source and destination keys exist
        if not self._node_key_exists(validated_data.get('source'), validated_data.get('source_key'), True):
            raise serializers.ValidationError({'source_key': _('Invalid source key!')})
        if not self._node_key_exists(validated_data.get('dest'), validated_data.get('dest_key'), False):
            raise serializers.ValidationError({'dest_key': _('Invalid destination key!')})

        return super().update(instance, validated_data)

    def _node_key_exists(self, node, node_key, is_output):
        if not node:
            # If node ID was invalid, then it is of course an error, but it
            # is checked elsewhere, so it's not a concern of this function.
            return True
        if is_output:
            return node_key in node.get_logic().get_output_keys()
        return node_key in node.get_logic().get_input_keys()
