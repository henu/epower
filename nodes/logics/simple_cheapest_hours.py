import dateutil
import decimal

from django.utils import timezone
from django.utils.translation import gettext_lazy, gettext as _

from . import logic


class SimpleCheapestHours(logic.Logic):

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
        min_off_hours_td = timezone.timedelta(
            hours=self.node.settings.get('min_off_hours', SimpleCheapestHours.DEFAULT_MIN_OFF_HOURS),
        )

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
