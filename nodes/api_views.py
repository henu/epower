from babel.dates import get_timezone_location
import pytz

from django.conf import settings
from django.utils import translation

from rest_framework import permissions, response, views, viewsets

from . import constants, models, serializers, utils


class NodeViewSet(viewsets.ModelViewSet):
    queryset = models.Node.objects.all().order_by('name')
    serializer_class = serializers.NodeSerializer
    permission_classes = [permissions.IsAuthenticated]


class ConnectionViewSet(viewsets.ModelViewSet):
    queryset = models.Connection.objects.all().order_by('id')
    serializer_class = serializers.ConnectionSerializer
    permission_classes = [permissions.IsAuthenticated]


class LogicsListView(views.APIView):

    def get(self, request):
        logics = {}

        for logic_class in settings.NODE_LOGIC_CLASSES:
            logic = utils.import_dot_path(logic_class)(None)
            logics[logic_class] = {
                'name': logic.get_name(),
                'description': logic.get_description(),
                'settings_fields': logic.get_settings_fields(),
            }

        return response.Response(logics)


class CountriesListView(views.APIView):

    def get(self, request):
        return response.Response(constants.COUNTRIES)


class TimezonesListView(views.APIView):

    def get(self, request):

        timezones = []

        for tz in sorted(pytz.common_timezones_set):
            locale = (translation.get_language() or 'en').split('-')[0]
            timezones.append([
                tz,
                '{} ({})'.format(tz, get_timezone_location(tz, locale=locale))
            ]);

        return response.Response(timezones)
