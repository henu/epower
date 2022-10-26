from django.conf import settings

from rest_framework import permissions, response, views, viewsets

from . import models, serializers, utils


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
            cls = utils.import_dot_path(logic_class)
            logics[logic_class] = cls(None).get_settings_fields()

        return response.Response(logics)
