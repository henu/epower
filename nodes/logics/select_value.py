from django.utils.translation import gettext as _

from . import logic


class SelectValue(logic.Logic):

    def get_name(self):
        return _('Select value')

    def get_description(self):
        return _('Outputs one of two values, based on input.')

    def get_settings_fields(self):
        return {
            'value_on': {
                'type': 'integer',
                'label': _('Output when input is on'),
            },
            'value_off': {
                'type': 'integer',
                'label': _('Output when input is off'),
            },
        }

    def get_input_keys(self):
        return {'input'}

    def get_output_keys(self):
        return {'output'}

    def get_output_values(self):
        if self.node.get_state().get('input'):
            return {
                'output': self.node.settings.get('value_on') or 0
            }
        return {
            'output': self.node.settings.get('value_off') or 0
        }

    def handle_inputs_changed(self, inputs):
        self.node.set_state({'input': inputs.get('input')})
