from django.utils.translation import gettext_lazy, gettext as _

import logging
from PyP100 import PyP100
import requests.exceptions

from . import logic, validators


logger = logging.getLogger(__name__)


class TapoP100(logic.Logic):

    def get_name(self):
        return _('Tapo P100')

    def get_description(self):
        return _('Controls Tapo smart plugs')

    def get_settings_fields(self):
        return {
            'ip': {
                'type': 'string',
                'label': gettext_lazy('IP address'),
            },
            'username': {
                'type': 'string',
                'label': gettext_lazy('Username (e-mail)'),
            },
            'password': {
                'type': 'password',
                'label': gettext_lazy('Password'),
            },
        }

    def get_input_keys(self):
        return {'power'}

    def handle_inputs_changed(self, inputs):
        self.node.set_state({'power': inputs.get('power')})

    def apply_state_to_devices(self):
        # Get and parse state
        power = self.node.get_state().get('power')
        # None means, do nothing
        if power is None:
            return
        # Convert to boolean
        power = bool(power)

        # Get settings
        ip = self.node.settings.get('ip')
        username = self.node.settings.get('username')
        password = self.node.settings.get('password')
        try:
            # Establish connection
            p100 = PyP100.P100(ip, username, password)
            p100.handshake()
            p100.login()
            # Update state
            if power:
                p100.turnOn()
            else:
                p100.turnOff()
        except requests.exceptions.ConnectTimeout:
            logger.error('Unable to connect to Tapo smartplug at {}'.format(ip))

    def get_settings_errors(self, settings, instance=None):
        settings_error = {}

        ip = settings.get('ip')

        if not ip:
            if not self.node:
                settings_error['ip'] = [_('This field is required!')]
        else:
            if not isinstance(ip, str):
                settings_error['ip'] = [_('Invalid type!')]
            elif not validators.IP_VALIDATION_RE.match(ip):
                settings_error['ip'] = [_('Not a valid IP address!')]

        username = settings.get('username')
        if not username:
            if not self.node:
                settings_error['username'] = [_('This field is required!')]
        else:
            if not isinstance(username, str):
                settings_error['username'] = [_('Invalid type!')]
            elif not validators.EMAIL_VALIDATION_RE.match(username):
                settings_error['username'] = [_('Not a valid e-mail!')]

        password = settings.get('password')
        if not password:
            if not self.node:
                settings_error['password'] = [_('This field is required!')]
        else:
            if not isinstance(password, str):
                settings_error['password'] = [_('Invalid type!')]

        return settings_error
