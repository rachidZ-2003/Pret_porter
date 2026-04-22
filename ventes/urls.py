from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    CaisseViewSet,
    SessionCaisseViewSet,
    VenteViewSet,
    LigneVenteViewSet,
    PaiementViewSet,
    RetourViewSet,
    LigneRetourViewSet,
)

router = DefaultRouter()
router.register('caisses', CaisseViewSet, basename='caisse')
router.register('sessions-caisse', SessionCaisseViewSet, basename='sessioncaisse')
router.register('ventes', VenteViewSet, basename='vente')
router.register('lignes-vente', LigneVenteViewSet, basename='linevente')
router.register('paiements', PaiementViewSet, basename='paiement')
router.register('retours', RetourViewSet, basename='retour')
router.register('lignes-retour', LigneRetourViewSet, basename='ligneretour')

urlpatterns = [
    path('', include(router.urls)),
]
