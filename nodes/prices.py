import dateutil
import decimal
import entsoe
import json
import pandas
import xml.dom.minidom

from django.core.cache import cache
from django.utils import timezone

from varstorage.models import Variable


def get_from_cache():
    prices = cache.get('prices')
    if not prices:
        return None
    prices = json.loads(prices)
    return _fix_prices(prices)


def store_to_cache(prices):
    cache.set('prices', json.dumps(_unfix_prices(prices)), 60 * 60 * 48)
    cache.set('prices_fetched_at', timezone.now().isoformat(), 60 * 60 * 48)


def fetch_prices():
    # If prices have been fetched recently, then don't return anything
    if cache.get('prices'):
        prices_fetched_at = cache.get('prices_fetched_at')
        if prices_fetched_at:
            prices_fetched_at = dateutil.parser.parse(prices_fetched_at)
            if prices_fetched_at > timezone.now() - timezone.timedelta(hours=1):
                return None

    # Read settings. If something is missing or invalid, then give up immediately
    countrycode = Variable.objects.get_value('countrycode')
    entsoe_api_key = Variable.objects.get_value('entsoe_api_key')
    if not countrycode or not entsoe_api_key:
        return None
    if not isinstance(countrycode, str) or not isinstance(entsoe_api_key, str):
        return None
    if len(countrycode) != 2:
        return None

    # Fetch fresh prices
    client = entsoe.EntsoeRawClient(api_key=entsoe_api_key)

    # Decide time range. Go a little bit to the past and a little
    # more to the future, so we are sure to get all the needed data.
    now = timezone.now()
    start = pandas.Timestamp((now - timezone.timedelta(days=1)).strftime('%Y%m%d'))
    end = pandas.Timestamp((now + timezone.timedelta(days=2)).strftime('%Y%m%d'))

    # Fetch the data
    xml_data = client.query_day_ahead_prices(countrycode.upper(), start, end)

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

    return _fix_prices(prices)


def _fix_prices(prices_raw):
    prices_fixed = []
    for price in prices_raw:
        prices_fixed.append({
            'start': dateutil.parser.parse(price['start']),
            'end': dateutil.parser.parse(price['end']),
            'price': decimal.Decimal(price['price']),
        })
    return prices_fixed


def _unfix_prices(prices):
    prices_raw = []
    for price in prices:
        prices_raw.append({
            'start': price['start'].isoformat(),
            'end': price['end'].isoformat(),
            'price': str(price['price']),
        })
    return prices_raw
