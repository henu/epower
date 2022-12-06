import aiohttp
import asyncio
import dateutil
import decimal
import re
import pymelcloud
import pytz

from django.conf import settings
from django.utils import timezone
from django.utils.translation import gettext_lazy, gettext as _

from PyP100 import PyP100

from . import utils


IP_VALIDATION_RE = re.compile('^[0-9]{1,3}\\.[0-9]{1,3}\\.[0-9]{1,3}\\.[0-9]{1,3}$')


class Logic:

    def __init__(self, node):
        self.node = node

    def get_name(self):
        raise NotImplementedError()

    def get_description(self):
        raise NotImplementedError()

    def get_settings_fields(self):
        return {}

    def get_input_keys(self):
        return set()

    def get_output_keys(self):
        return set()

    def get_output_values(self):
        return {}

    def handle_inputs_changed(self, inputs):
        pass

    def handle_updated_prices(self, prices):
        pass

    def apply_state_to_devices(self):
        pass

    def get_settings_errors(self, settings):
        return {}


class SimpleCheapestHours(Logic):

    DEFAULT_ON_HOURS = 4
    DEFAULT_MIN_OFF_HOURS = 12

    def get_name(self):
        return _('Simple cheapest hours')

    def get_description(self):
        return _('Emits signal during the cheapest hours of the day.')

    def get_settings_fields(self):
        return {
            'on_hours': {
                'type': 'integer',
                'label': gettext_lazy('"On" state length (h)'),
                'min': 1,
                'max': 23
            },
            'min_off_hours': {
                'type': 'integer',
                'label': gettext_lazy('Minimum time in "off" state (h)'),
                'min': 0,
                'max': 23
            },
        }

    def get_output_keys(self):
        return {'power'}

    def get_output_values(self):
        # Check all hours. If any of them is now, then return active signal
        # Return active signal, if any of the hours is now
        for start, end in self.node.get_state().get('hours', []):
            start = dateutil.parser.parse(start)
            end = dateutil.parser.parse(end)
            if start <= timezone.now() <= end:
                return {'power': 1}
        return {'power': 0}

    def handle_updated_prices(self, prices):

        # Get options for this node
        on_hours = self.node.settings.get('on_hours', SimpleCheapestHours.DEFAULT_ON_HOURS)
        on_hours_td = timezone.timedelta(hours=on_hours)
        min_off_hours_td = timezone.timedelta(hours=self.node.settings.get('min_off_hours', SimpleCheapestHours.DEFAULT_MIN_OFF_HOURS))

        # Get current hours and remove those that are one week to the
        # past. The period of one week is left for debugging purposes.
        hours = [
            (dateutil.parser.parse(start), dateutil.parser.parse(end))
            for start, end in self.node.get_state().get('hours', [])
            if dateutil.parser.parse(end) >= timezone.now() - timezone.timedelta(days=7)
        ]

        # If there are already on-hours during the last 24 hours, then don't add more on-hours
        range_24h_start = prices[-24]['start']
        for start, end in hours:
            if end > range_24h_start:
                return

        # Now try to find a good on time for the newest 24 hour range
        prices = prices[-23 - on_hours:]
        best_on_time_price_ofs = None
        best_on_time_total_price = None
        for price_ofs in range(len(prices)):
            # Skip those hours that start in the past
            if prices[price_ofs]['start'] < timezone.now():
                continue
            # Give up if there is not enough hours to fit the on_hours range
            if len(prices) - price_ofs < on_hours:
                break
            # Skip if this time is too close to already existing on_hour range
            price_start = prices[price_ofs]['start']
            price_end = price_start + on_hours_td
            too_close = False
            for hour_start, hour_end in hours:
                if price_start < hour_end + min_off_hours_td and price_end > hour_start - min_off_hours_td:
                    too_close = True
                    break
            if too_close:
                continue
            # Check if this would be a better candidate
            total_price = decimal.Decimal(0)
            for hour_i in range(on_hours):
                total_price += prices[price_ofs + hour_i]['price']
            if best_on_time_total_price is None or best_on_time_total_price > total_price:
                best_on_time_price_ofs = price_ofs
                best_on_time_total_price = total_price
        # If good price was found
        if best_on_time_total_price is not None:
            best_on_time_price_start = prices[best_on_time_price_ofs]['start']
            hours.append((best_on_time_price_start, best_on_time_price_start + on_hours_td))

        # Store new state of node
        self.node.set_state({'hours': [(start.isoformat(), end.isoformat()) for start, end in hours]})

    def get_settings_errors(self, settings):
        settings_error = {}

        if 'on_hours' not in settings:
            if not self.node:
                settings_error['on_hours'] = [_('This field is required!')]
            on_hours = self.node.settings.get('on_hours', SimpleCheapestHours.DEFAULT_ON_HOURS)
        else:
            on_hours = settings['on_hours']
            if not isinstance(on_hours, int):
                settings_error['on_hours'] = [_('Invalid type!')]
            elif on_hours < 1:
                settings_error['on_hours'] = [_('Must be at least one!')]
            elif on_hours > 23:
                settings_error['on_hours'] = [_('Must be smaller than 24!')]

        if 'min_off_hours' not in settings:
            if not self.node:
                settings_error['min_off_hours'] = [_('This field is required!')]
        else:
            min_off_hours = settings['min_off_hours']
            if not isinstance(min_off_hours, int):
                settings_error['min_off_hours'] = [_('Invalid type!')]
            elif min_off_hours < 0:
                settings_error['min_off_hours'] = [_('Cannot be negative!')]
            elif min_off_hours > 23 - min(23, on_hours):
                settings_error['min_off_hours'] = [_('Must be smaller than {}!'.format(24 - min(23, on_hours)))]

        return settings_error


class TapoP100(Logic):

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
        self.node.set_state({'power': bool(inputs.get('power'))})

    def apply_state_to_devices(self):
        # Get settings
        ip = self.node.settings.get('ip')
        username = self.node.settings.get('username')
        password = self.node.settings.get('password')
        # Establish connection
        p100 = PyP100.P100(ip, username, password)
        p100.handshake()
        p100.login()
        # Update state
        if self.node.get_state().get('power'):
            p100.turnOn()
        else:
            p100.turnOff()

    def get_settings_errors(self, settings, instance=None):
        settings_error = {}

        ip = settings.get('ip')

        if not ip:
            if not self.node:
                settings_error['ip'] = [_('This field is required!')]
        else:
            if not isinstance(ip, str):
                settings_error['ip'] = [_('Invalid type!')]
            elif not IP_VALIDATION_RE.match(ip):
                settings_error['ip'] = [_('Not a valid IP address!')]

        username = settings.get('username')
        if not username:
            if not self.node:
                settings_error['username'] = [_('This field is required!')]
        else:
            if not isinstance(username, str):
                settings_error['username'] = [_('Invalid type!')]

        password = settings.get('password')
        if not password:
            if not self.node:
                settings_error['password'] = [_('This field is required!')]
        else:
            if not isinstance(password, str):
                settings_error['password'] = [_('Invalid type!')]

        return settings_error


class Clock(Logic):

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


# TODO: It would be great if this could combine API calls of all heat pumps. Now it makes full calls all the time when single pump is read or written.
class MelCloud(Logic):

    def get_name(self):
        return _('Mitsubishi air-to-air heat pump')

    def get_description(self):
        return _('Controls Mitsubishi air-to-air heat pumps. Also gets room and target temperatures from them.')

    def get_settings_fields(self):
        return {
            'name': {
                'type': 'string',
                'label': gettext_lazy('Device name'),
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

    def get_output_keys(self):
        return {'room temperature', 'target temperature'}

    def get_output_values(self):

        # Use local caching
        if not hasattr(self, '_cached_room_temp') or not hasattr(self, '_cached_target_temp'):
            loop = asyncio.get_event_loop()
            device_state = loop.run_until_complete(self._get_device_state())
            self._cached_room_temp = device_state['room_temp']
            self._cached_target_temp = device_state['target_temp']

        return {
            'room temperature': self._cached_room_temp,
            'target temperature': self._cached_target_temp,
        }

    def handle_inputs_changed(self, inputs):
        self.node.set_state({'power': bool(inputs.get('power'))})

    def apply_state_to_devices(self):
        # Get state
        power = self.node.get_state().get('power')
        # Validate state
        if power not in [True, False]:
            return
        # Do the magic
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self._set_power(power))

    def get_settings_errors(self, settings, instance=None):
        settings_error = {}

        name = settings.get('name')

        if not name:
            if not self.node:
                settings_error['name'] = [_('This field is required!')]

        username = settings.get('username')
        if not username:
            if not self.node:
                settings_error['username'] = [_('This field is required!')]
        else:
            if not isinstance(username, str):
                settings_error['username'] = [_('Invalid type!')]

        password = settings.get('password')
        if not password:
            if not self.node:
                settings_error['password'] = [_('This field is required!')]
        else:
            if not isinstance(password, str):
                settings_error['password'] = [_('Invalid type!')]

        return settings_error

    async def _get_device_state(self):

        async with aiohttp.ClientSession() as session:
            token = await pymelcloud.login(self.node.settings.get('username'), self.node.settings.get('password'), session=session)

            room_temp = None
            target_temp = None

            # Iterate all devices and try to find the one with correct name
            devices = await pymelcloud.get_devices(token, session=session)
            for device in devices[pymelcloud.DEVICE_TYPE_ATA]:
                if device.name.lower() == (self.node.settings.get('name') or '').lower():
                    room_temp = device.get_device_prop('RoomTemperature')
                    target_temp = device.get_device_prop('SetTemperature')

            await session.close()

            return {
                'room_temp': room_temp,
                'target_temp': target_temp,
            }

    async def _set_power(self, power):

        async with aiohttp.ClientSession() as session:
            token = await pymelcloud.login(self.node.settings.get('username'), self.node.settings.get('password'), session=session)

            # Update first device with matching name
            devices = await pymelcloud.get_devices(token, session=session)
            for device in devices[pymelcloud.DEVICE_TYPE_ATA]:
                if device.name.lower() == (self.node.settings.get('name') or '').lower():

                    # Only update if power state differs
                    if power != device.get_device_prop('Power'):
                        await device.update()
                        await device.set({pymelcloud.device.PROPERTY_POWER: power})

                    break

            await session.close()
