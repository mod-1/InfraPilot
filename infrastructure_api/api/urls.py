from django.urls import path
from rest_framework import routers
from . import views

router = routers.DefaultRouter()
# regester a /compute endpoint
router.register(r'compute', views.ComputeViewSet, basename='compute')
router.register(r'store', views.StoreViewSet, basename='store')
router.register(r'cluster', views.ClusterViewSet, basename='cluster')
router.register(r'custom', views.CustomViewSet, basename='custom')
urlpatterns = router.urls