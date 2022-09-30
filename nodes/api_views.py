from rest_framework import permissions, viewsets

from . import models, serializers


class NodeViewSet(viewsets.ModelViewSet):
    queryset = models.Node.objects.all().order_by('name')
    serializer_class = serializers.NodeSerializer
    permission_classes = [permissions.IsAuthenticated]


class ConnectionViewSet(viewsets.ModelViewSet):
    queryset = models.Connection.objects.all().order_by('id')
    serializer_class = serializers.ConnectionSerializer
    permission_classes = [permissions.IsAuthenticated]
