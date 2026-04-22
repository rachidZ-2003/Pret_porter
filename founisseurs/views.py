from rest_framework import viewsets

from founisseurs.models import Fournisseur, CommandeFournisseur, LigneCommande
from founisseurs.serializers import (
    FournisseurSerializer,
    LigneCommandeSerializer,
    LigneCommandeCreateSerializer,
    CommandeFournisseurSerializer,
    CommandeFournisseurCreateSerializer,
)


class FournisseurViewSet(viewsets.ModelViewSet):
    queryset = Fournisseur.objects.all()
    serializer_class = FournisseurSerializer


class LigneCommandeViewSet(viewsets.ModelViewSet):
    queryset = LigneCommande.objects.all()

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return LigneCommandeCreateSerializer
        return LigneCommandeSerializer


class CommandeFournisseurViewSet(viewsets.ModelViewSet):
    queryset = CommandeFournisseur.objects.all()

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return CommandeFournisseurCreateSerializer
        return CommandeFournisseurSerializer
