from django.core.management.base import BaseCommand

from ... import prices


class Command(BaseCommand):
    help = 'Runs all periodic tasks at once.'

    def handle(self, *args, **options):

        # Try to fetch new prices
        new_prices = prices.fetch_prices()

        # If new prices were got, then compare them to the old ones.
        if new_prices:
            old_prices = prices.get_from_cache()
            # If prices were changed, then store prices to cache.
            if old_prices != new_prices:
                # Store new prices to cache
                prices.store_to_cache(new_prices)
