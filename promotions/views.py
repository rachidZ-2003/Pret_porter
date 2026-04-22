from rest_framework import viewsets

from promotions.models import Promotion
from promotions.serializers import PromotionSerializer


class PromotionViewSet(viewsets.ModelViewSet):
    queryset = Promotion.objects.all()
    serializer_class = PromotionSerializer
