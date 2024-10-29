from django.urls import path
from rest_framework import routers
from . import views

router = routers.DefaultRouter()
# Add your viewsets here
# router.register(r'items', views.ItemViewSet)

urlpatterns = router.urls