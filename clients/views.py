from rest_framework import viewsets

from clients.models import Client, Avoir
from clients.serializers import ClientSerializer, AvoirSerializer


class ClientViewSet(viewsets.ModelViewSet):
    queryset = Client.objects.all()
    serializer_class = ClientSerializer


class AvoirViewSet(viewsets.ModelViewSet):
    queryset = Avoir.objects.all()
    serializer_class = AvoirSerializer
