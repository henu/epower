from django.urls import path

from rest_framework.routers import DefaultRouter

import nodes.api_views
import varstorage.api_views


urlpatterns = [
    path('logics/', nodes.api_views.LogicsListView.as_view()),
    path('countries/', nodes.api_views.CountriesListView.as_view()),
    path('timezones/', nodes.api_views.TimezonesListView.as_view()),
]

router = DefaultRouter()
router.register(r'nodes', nodes.api_views.NodeViewSet, basename='nodes')
router.register(r'connections', nodes.api_views.ConnectionViewSet, basename='connections')
router.register(r'variables', varstorage.api_views.VariableViewSet, basename='variables')
urlpatterns += router.urls
