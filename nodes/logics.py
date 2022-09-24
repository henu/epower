import dateutil
import decimal

from django.utils import timezone

from PyP100 import PyP100


class Logic:

    def __init__(self, node):
        self.node = node

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


class SimpleCheapestHours(Logic):

    DEFAULT_ON_HOURS = 4
    DEFAULT_MIN_OFF_HOURS = 12

    def get_output_keys(self):
        return {'default'}

    def get_output_values(self):
        # Check all hours. If any of them is now, then return active signal
        # Return active signal, if any of the hours is now
        for start, end in self.node.get_state().get('hours', []):
            start = dateutil.parser.parse(start)
            end = dateutil.parser.parse(end)
            if start <= timezone.now() <= end:
                return {'default': 1}
        return {'default': 0}

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


class TapoP100(Logic):

    def get_input_keys(self):
        return {'default'}

    def handle_inputs_changed(self, inputs):
        self.node.set_state({'power': bool(inputs.get('default'))})

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
