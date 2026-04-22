from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    CategorieViewSet,
    MarqueViewSet,
    CollectionViewSet,
    ArticleViewSet,
    DeclinaisonViewSet,
    MouvementStockViewSet,
    InventaireViewSet,
    LigneInventaireViewSet,
)

router = DefaultRouter()
router.register('categories', CategorieViewSet, basename='categorie')
router.register('marques', MarqueViewSet, basename='marque')
router.register('collections', CollectionViewSet, basename='collection')
router.register('articles', ArticleViewSet, basename='article')
router.register('declinaisons', DeclinaisonViewSet, basename='declinaison')
router.register('mouvements-stock', MouvementStockViewSet, basename='mouvementstock')
router.register('inventaires', InventaireViewSet, basename='inventaire')
router.register('lignes-inventaire', LigneInventaireViewSet, basename='ligneinventaire')

urlpatterns = [
    path('', include(router.urls)),
]
