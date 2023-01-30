from collections import defaultdict

from django.core.management.base import BaseCommand

import django_lock

from ... import models, prices


class Command(BaseCommand):
    help = 'Runs all periodic tasks at once.'

    def handle(self, *args, **options):

        try:
            with django_lock.lock('run_periodic_tasks', blocking=False, timeout=60 * 60 * 4):

                # Fetch all Nodes to memory. This way, we don't have to fetch them multiple times,
                # and they can do for example some local catching in them. The Logics inside Nodes
                # are automatically cached too, so those can do the local caching too.
                nodes = {node.id: node for node in models.Node.objects.all()}

                # Try to fetch new prices
                new_prices = prices.fetch_prices()

                # If new prices were got, then compare them to the old ones.
                if new_prices:
                    old_prices = prices.get_from_cache()
                    # If prices were changed, then inform all nodes about this. After this, store prices to cache.
                    if old_prices != new_prices:
                        # Iterate all nodes through
                        for node in nodes.values():
                            logic = node.get_logic()
                            logic.handle_updated_prices(new_prices)
                        # Store new prices to cache
                        prices.store_to_cache(new_prices)

        # TODO: If connection is removed, let power go down!
                # Let connections flow through the network.
                # A simple cache is used to detect changes in input values. The cache is not persisent,
                # because it is better to be sure that at least some recalculation happens on every run.
                old_node_inputs = defaultdict(dict)
                # All Nodes are looped several times to keep things easier to
                # code and to make possible to have recurrent connections.
                for i in range(10):
                    # Inputs of nodes. These will be filled in the loop below
                    new_node_inputs = defaultdict(dict)
                    # Now loop all nodes
                    for node in nodes.values():
                        new_outputs = node.get_logic().get_output_values() or {}

                        # Transfer values via Connections
                        for connection in node.outputs.all():
                            value = new_outputs.get(connection.source_key)
                            new_node_inputs[connection.dest_id][connection.dest_key] = value

                    # Now check if some values differ
                    node_ids = set(old_node_inputs.keys()) | set(new_node_inputs.keys())
                    for node_id in node_ids:
                        old_inputs = old_node_inputs.get(node_id, {})
                        new_inputs = new_node_inputs.get(node_id, {})
                        if old_inputs != new_inputs:
                            nodes[node_id].get_logic().handle_inputs_changed(new_inputs)

                    # Update cache
                    old_node_inputs = new_node_inputs

                # Finally apply state to devices
                for node in nodes.values():
                    node.get_logic().apply_state_to_devices()

        except django_lock.Locked:
            pass
