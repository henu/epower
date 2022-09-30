from rest_framework.routers import DefaultRouter

import nodes.api_views


router = DefaultRouter()
router.register(r'nodes', nodes.api_views.NodeViewSet, basename='node')
urlpatterns = router.urls
