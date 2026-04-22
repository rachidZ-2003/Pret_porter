from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    ChangePasswordView,
    MagasinViewSet,
    MeAPIView,
    RoleViewSet,
    UtilisateurViewSet,
    JournalAuditViewSet,
    ParametreViewSet,
)

router = DefaultRouter()
router.register('magasins', MagasinViewSet, basename='magasin')
router.register('roles', RoleViewSet, basename='role')
router.register('utilisateurs', UtilisateurViewSet, basename='utilisateur')
router.register('journaux-audit', JournalAuditViewSet, basename='journal-audit')
router.register('parametres', ParametreViewSet, basename='parametre')


urlpatterns = [
     path('utilisateurs/me/', MeAPIView.as_view(), name='me'), 
     path('auth/change-password/', ChangePasswordView.as_view(), name='change-password'),
    path('', include(router.urls)),
   
]
