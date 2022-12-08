import aiohttp
import asyncio
import pymelcloud

from django.utils.translation import gettext_lazy, gettext as _

from . import logic, validators


# TODO: It would be great if this could combine API calls of all heat pumps.
# Now it makes full calls all the time when single pump is read or written.
class MelCloud(logic.Logic):

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

    async def _get_device_state(self):

        async with aiohttp.ClientSession() as session:
            token = await pymelcloud.login(
                self.node.settings.get('username'),
                self.node.settings.get('password'),
                session=session,
            )

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
            token = await pymelcloud.login(
                self.node.settings.get('username'),
                self.node.settings.get('password'),
                session=session,
            )

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
