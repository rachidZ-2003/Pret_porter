from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    FournisseurViewSet,
    LigneCommandeViewSet,
    CommandeFournisseurViewSet,
)

router = DefaultRouter()
router.register('fournisseurs', FournisseurViewSet, basename='fournisseur')
router.register('lignes-commande', LigneCommandeViewSet, basename='lignecommande')
router.register('commandes-fournisseur', CommandeFournisseurViewSet, basename='commandefournisseur')

urlpatterns = [
    path('', include(router.urls)),
]
