from django.urls import path
from rest_framework import routers
from . import views

router = routers.DefaultRouter()

# regester a /compute endpoint
router.register(r'compute', views.ComputeViewSet, basename='compute')
router.register(r'store', views.StoreViewSet, basename='store')
router.register(r'ecs', views.EcsViewSet, basename='ecs')

urlpatterns = router.urls