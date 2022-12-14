import json

from django.conf import settings
from django.core.cache import cache
from django.db import models

from . import utils


class Node(models.Model):

    name = models.CharField(max_length=200)

    logic_class = models.CharField(max_length=200)

    settings = models.JSONField()

    # These are used only for graphical representation
    pos_x = models.FloatField(default=0)
    pos_y = models.FloatField(default=0)

    def get_state(self):
        return json.loads(cache.get(self._state_cache_key()) or '{}')

    def set_state(self, state):
        return cache.set(self._state_cache_key(), json.dumps(state), 60 * 60 * 24 * 365)

    def get_logic(self):

        # To prevent re-creating this object every time, use simple local caching
        if not hasattr(self, '_cached_logic'):

            # Some extra security, make sure logic class is allowed in settings
            if self.logic_class not in settings.NODE_LOGIC_CLASSES:
                raise Exception('Invalid logic_class!')

            cls = utils.import_dot_path(self.logic_class)

            # Create a new instance from the class
            self._cached_logic = cls(self)

        return self._cached_logic

    def _state_cache_key(self):
        return f'node_state_{self.id}'

    def __str__(self):
        return f'{self.name} ({self.logic_class})'


class Connection(models.Model):

    source = models.ForeignKey(Node, related_name='outputs', on_delete=models.CASCADE)
    source_key = models.CharField(max_length=50)

    dest = models.ForeignKey(Node, related_name='inputs', on_delete=models.CASCADE)
    dest_key = models.CharField(max_length=50)

    def __str__(self):
        return f'{self.source} ({self.source_key}) -> {self.dest} ({self.dest_key})'

    class Meta:
        unique_together = (
            ('dest', 'dest_key'),
        )
