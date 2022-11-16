from rest_framework import permissions, viewsets

from . import models, serializers


class VariableViewSet(viewsets.ModelViewSet):
    queryset = models.Variable.objects.all().order_by('name')
    serializer_class = serializers.VariableSerializer
    permission_classes = [permissions.IsAuthenticated]
