import dateutil.parser
import decimal

from django.utils import timezone
from django.utils.translation import gettext_lazy, gettext as _

from . import logic


# TODO: There is a problem, that if you put certain difficult min on/off times, it will not be able
# to calculate the ranges very far, and the ranges might end before the time reaches their end
class PriceBasedOnOff(logic.Logic):

    def get_name(self):
        return _('Price based on/off')

    def get_description(self):
        return _('You set the minimum and maximum on and off hours. This logic will '
            'start and stop emitting signal depending the electricity price.')

    def get_settings_fields(self):
        return {
            'min_on_hours': {
                'type': 'integer',
                'label': gettext_lazy('"On" state minimum length (h)'),
                'min': 1,
                'max': 23
            },
            'max_on_hours': {
                'type': 'integer',
                'label': gettext_lazy('"On" state maximum length (h)'),
                'min': 1,
                'max': 23
            },
            'min_off_hours': {
                'type': 'integer',
                'label': gettext_lazy('"Off" state minimum length (h)'),
                'min': 1,
                'max': 23
            },
            'max_off_hours': {
                'type': 'integer',
                'label': gettext_lazy('"Off" state maximum length (h)'),
                'min': 1,
                'max': 23
            },
        }

    def get_output_keys(self):
        return {'power'}

    def get_output_values(self):
        # If there are no ranges at all, then return True
        ranges = self.node.get_state().get('ranges', [])
        if not ranges:
            return {'power': True}

        # Try to find the current range
        for start, end, state in ranges:
            start = dateutil.parser.parse(start)
            end = dateutil.parser.parse(end)
            if start <= timezone.now() <= end:
                return {'power': state}

        # If range was not found, then return opposite what the latest range said
        return {'power': not ranges[-1][2]}

    def handle_updated_prices(self, prices):

        # Get and validate options
        min_on_hours = self.node.settings.get('min_on_hours')
        max_on_hours = self.node.settings.get('max_on_hours')
        min_off_hours = self.node.settings.get('min_off_hours')
        max_off_hours = self.node.settings.get('max_off_hours')
        if not min_on_hours or not max_on_hours or not min_off_hours or not max_off_hours:
            return

        # Get current ranges and remove those that are one week to the
        # past. The period of one week is left for debugging purposes.
        ranges = [
            (dateutil.parser.parse(start), dateutil.parser.parse(end), state)
            for start, end, state in self.node.get_state().get('ranges', [])
            if dateutil.parser.parse(end) >= timezone.now() - timezone.timedelta(days=7)
        ]

        # Decide the starting point and what is the initial state of the output
        now_hour = timezone.now().replace(minute=0, second=0, microsecond=0)
        initial_state = True
        if ranges:
            now_hour = max(now_hour, ranges[-1][1])
            initial_state = not ranges[-1][2]

        # Gather the prices starting from "now_hour"
        future_prices = [price for price in prices if price['end'] > now_hour]

        # Start iterating different combinations through, and keep track of the cheapest one
        cheapest_comb = {
            'ranges': None,
            'price': None,
        }
        self._iterate_all_combinations(
            cheapest_comb,
            future_prices,
            [],
            decimal.Decimal(0),
            initial_state,
            min_on_hours,
            max_on_hours,
            min_off_hours,
            max_off_hours,
        )
        if cheapest_comb['ranges']:
            ranges += cheapest_comb['ranges']

        # Store ranges to state
        state = self.node.get_state()
        state['ranges'] = [(start.isoformat(), end.isoformat(), range_state) for start, end, range_state in ranges]
        self.node.set_state(state)

    def get_settings_errors(self, settings):
        settings_error = {}

        if 'min_on_hours' not in settings:
            if not self.node:
                settings_error['min_on_hours'] = [_('This field is required!')]
            min_on_hours = self.node.settings.get('min_on_hours', SimpleCheapestHours.DEFAULT_ON_HOURS)
        else:
            min_on_hours = settings['min_on_hours']
            if not isinstance(min_on_hours, int):
                settings_error['min_on_hours'] = [_('Invalid type!')]
            elif min_on_hours < 1:
                settings_error['min_on_hours'] = [_('Must be at least one!')]
            elif min_on_hours > 23:
                settings_error['min_on_hours'] = [_('Must be smaller than 24!')]

        if 'max_on_hours' not in settings:
            if not self.node:
                settings_error['max_on_hours'] = [_('This field is required!')]
            max_on_hours = self.node.settings.get('max_on_hours', SimpleCheapestHours.DEFAULT_ON_HOURS)
        else:
            max_on_hours = settings['max_on_hours']
            if not isinstance(max_on_hours, int):
                settings_error['max_on_hours'] = [_('Invalid type!')]
            elif max_on_hours < 1:
                settings_error['max_on_hours'] = [_('Must be at least one!')]
            elif max_on_hours > 23:
                settings_error['max_on_hours'] = [_('Must be smaller than 24!')]
        if min_on_hours > max_on_hours:
            settings_error['max_on_hours'] = [_('Minimum limit cannot be greater than maximum limit!')]

        if 'min_off_hours' not in settings:
            if not self.node:
                settings_error['min_off_hours'] = [_('This field is required!')]
            min_off_hours = self.node.settings.get('min_off_hours', SimpleCheapestHours.DEFAULT_ON_HOURS)
        else:
            min_off_hours = settings['min_off_hours']
            if not isinstance(min_off_hours, int):
                settings_error['min_off_hours'] = [_('Invalid type!')]
            elif min_off_hours < 1:
                settings_error['min_off_hours'] = [_('Must be at least one!')]
            elif min_off_hours > 23:
                settings_error['min_off_hours'] = [_('Must be smaller than 24!')]

        if 'max_off_hours' not in settings:
            if not self.node:
                settings_error['max_off_hours'] = [_('This field is required!')]
            max_off_hours = self.node.settings.get('max_off_hours', SimpleCheapestHours.DEFAULT_ON_HOURS)
        else:
            max_off_hours = settings['max_off_hours']
            if not isinstance(max_off_hours, int):
                settings_error['max_off_hours'] = [_('Invalid type!')]
            elif max_off_hours < 1:
                settings_error['max_off_hours'] = [_('Must be at least one!')]
            elif max_off_hours > 23:
                settings_error['max_off_hours'] = [_('Must be smaller than 24!')]
        if min_off_hours > max_off_hours:
            settings_error['max_off_hours'] = [_('Minimum limit cannot be greater than maximum limit!')]

        return settings_error

    def _iterate_all_combinations(self, cheapest_comb, prices, ranges_now, price_now, next_state,
            min_on, max_on, min_off, max_off):

        if next_state:
            range_min = min_on
            range_max = max_on
        else:
            range_min = min_off
            range_max = max_off

        # If the last state fitted perfectly, or if this change will not fit at
        # all, then calculate price and check if it's the new cheapest one.
        if not prices or len(prices) < range_min:
            # If there are no ranges currently, then it means the old ranges already fill the hours. So give up.
            if not ranges_now:
                return

            hours = round((ranges_now[-1][1] - ranges_now[0][0]).total_seconds() / 3600)
            # If this range doesn't fit here, then add it partially, but only use this partial range in price calculation
            if len(prices) < range_min:
                hours += len(prices)
                if next_state:
                    price_now += sum([price['price'] for price in prices])

            # Now calculate and compare final prices
            price_per_hour = price_now / hours
            if cheapest_comb['price'] is None or price_per_hour < cheapest_comb['price']:
                cheapest_comb['price'] = price_per_hour
                cheapest_comb['ranges'] = ranges_now
            return

        for new_range_len in range(range_min, range_max + 1):
            # If the next range doesn't fit, then give up totally
            if len(prices) < new_range_len:
                return

            # Calculate new price.
            new_price = price_now
            if next_state:
                new_price += sum([price['price'] for price in prices[0:new_range_len]])

            # Since the prices are now used, they can be ditched
            new_prices = prices[new_range_len:]

            # Add new ranges
            new_ranges = ranges_now + [(prices[0]['start'], prices[new_range_len - 1]['end'], next_state)]

            self._iterate_all_combinations(
                cheapest_comb,
                new_prices,
                new_ranges,
                new_price,
                not next_state,
                min_on,
                max_on,
                min_off,
                max_off,
            )
