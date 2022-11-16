from django.utils.translation import gettext_lazy


COUNTRIES = {
    'FI': {
        'name': gettext_lazy('Finland'),
        'timezones': 'Europe/Helsinki',
        'price_source': {
            'type': 'entsoe',
        }
    }
}
