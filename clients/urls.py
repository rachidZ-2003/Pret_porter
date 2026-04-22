from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import ClientViewSet, AvoirViewSet

router = DefaultRouter()
router.register('clients', ClientViewSet, basename='client')
router.register('avoirs', AvoirViewSet, basename='avoir')

urlpatterns = [
    path('', include(router.urls)),
]
