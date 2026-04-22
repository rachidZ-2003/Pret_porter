from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import PromotionViewSet

router = DefaultRouter()
router.register('promotions', PromotionViewSet, basename='promotion')

urlpatterns = [
    path('', include(router.urls)),
]
