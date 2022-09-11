import json
import pandas

from django.conf import settings
from django.core.cache import cache
from django.utils import timezone

import dateutil
import decimal
import entsoe
import xml.dom.minidom


def get_latest_prices():

    # First check if prices can be found from cache
    prices = None
    prices_fetched_at = cache.get('prices_fetched_at')
    if prices_fetched_at:
        prices_fetched_at = dateutil.parser.parse(prices_fetched_at)
        # Prices are considered fresh, if they are fetched a maximum of one hour ago
        if prices_fetched_at > timezone.now() - timezone.timedelta(hours=1):
            prices = cache.get('prices')
            if prices:
                prices = json.loads(prices)

    # If prices were not in the cache, then fetch them now
    if not prices:
        client = entsoe.EntsoeRawClient(api_key=settings.ENTSOE_API_KEY)

        # Decide times. Go a little bit to the past and a little bit
        # more to the future, so we are sure to get all the needed data.
        now = timezone.now()
        start = pandas.Timestamp((now - timezone.timedelta(days=1)).strftime('%Y%m%d'))
        end = pandas.Timestamp((now + timezone.timedelta(days=2)).strftime('%Y%m%d'))

        # Fetch the data
        xml_data = client.query_day_ahead_prices(settings.COUNTRYCODE, start, end)

        # Parse XML to dict
        xml_dom = xml.dom.minidom.parseString(xml_data)
        prices = []
        for period in xml_dom.getElementsByTagName('Period'):
            period_start = dateutil.parser.parse(period.getElementsByTagName('start')[0].firstChild.wholeText)

            period_resolution = period.getElementsByTagName('resolution')[0].firstChild.wholeText
            if period_resolution != 'PT60M':
                raise Exception(f'Unsupported period resolution {period_resolution}')

            for hour, point in enumerate(period.getElementsByTagName('Point')):
                point_start = (period_start + timezone.timedelta(hours=hour)).isoformat()
                point_end = (period_start + timezone.timedelta(hours=hour + 1)).isoformat()
                point_price = point.getElementsByTagName('price.amount')[0].firstChild.wholeText
                prices.append({
                    'start': point_start,
                    'end': point_end,
                    'price': point_price,
                })

        # Keep only latest 48 hours
        prices = sorted(prices, key=lambda price: price['start'])[-48:]

        # Store fresh prices to the cache
        cache.set('prices', json.dumps(prices), 60 * 60 * 48)
        cache.set('prices_fetched_at', timezone.now().isoformat(), 60 * 60 * 48)

    # Return the prices, but convert dates to datetime objects and price to Decimal object
    prices_fixed = []
    for price in prices:
        prices_fixed.append({
            'start': dateutil.parser.parse(price['start']),
            'end': dateutil.parser.parse(price['end']),
            'price': decimal.Decimal(price['price']),
        })
    return prices_fixed
