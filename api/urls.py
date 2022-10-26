from django.urls import path

from rest_framework.routers import DefaultRouter

import nodes.api_views


urlpatterns = [
    path('logics/', nodes.api_views.LogicsListView.as_view()),
]

router = DefaultRouter()
router.register(r'nodes', nodes.api_views.NodeViewSet, basename='nodes')
router.register(r'connections', nodes.api_views.ConnectionViewSet, basename='connections')
urlpatterns += router.urls
