from django.utils import timezone
from django.utils.translation import gettext_lazy, gettext as _

from .. import utils

from . import logic


class Clock(logic.Logic):

    def get_name(self):
        return _('Clock')

    def get_description(self):
        return _('Simple clock that emits signal during a specific time frame.')

    def get_settings_fields(self):
        return {
            'start': {
                'type': 'time',
                'label': gettext_lazy('Start time'),
            },
            'end': {
                'type': 'time',
                'label': gettext_lazy('End time'),
            },
        }

    def get_output_keys(self):
        return {'power'}

    def get_output_values(self):
        # Get and validate settings
        start_time = self.node.settings.get('start')
        end_time = self.node.settings.get('end')
        if not start_time or not end_time:
            return {'power': 0}
        # Check if signal should be emitted
        local_time = timezone.now().astimezone(utils.get_configured_timezone()).strftime('%H:%M')
        if start_time < end_time:
            if start_time <= local_time and end_time > local_time:
                return {'power': 1}
        elif start_time > end_time:
            if start_time <= local_time or end_time > local_time:
                return {'power': 1}
        return {'power': 0}
