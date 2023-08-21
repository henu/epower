from django.utils.translation import gettext_lazy, gettext as _

from . import logic


class And(logic.Logic):

    def get_name(self):
        return _('AND port')

    def get_description(self):
        return _('If all inputs are considered true, then returns last of them. Otherwise returns first input that is considered as false.')

    def get_input_keys(self):
        return {'input1', 'input2'}

    def get_output_keys(self):
        return {'output'}

    def get_output_values(self):

        return {
            'output': self.node.get_state().get('output'),
        }

    def handle_inputs_changed(self, inputs):
        self.node.set_state({'output': inputs.get('input1') and inputs.get('input2')})
