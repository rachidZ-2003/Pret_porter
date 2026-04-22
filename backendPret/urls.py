"""
URL configuration for backendPret project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include

from administration.views import (
    AuthLoginAPIView,
    Verify2FAAPIView,
    RefreshTokenAPIView,
    RegisterAPIView,
    BootstrapRegisterAPIView,
    Activer2FAAPIView,
    Confirmer2FAAPIView,
    Desactiver2FAAPIView,
)

urlpatterns = [
    path('admin/', admin.site.urls),
    # Auth JWT + 2FA
    path('api/auth/login/', AuthLoginAPIView.as_view()),
    path('api/auth/register/', RegisterAPIView.as_view()),
    path('api/auth/bootstrap-register/', BootstrapRegisterAPIView.as_view()),
    path('api/auth/verify-2fa/', Verify2FAAPIView.as_view()),
    path('api/auth/refresh/', RefreshTokenAPIView.as_view()),
    path('api/auth/2fa/activer/', Activer2FAAPIView.as_view()),
    path('api/auth/2fa/confirmer/', Confirmer2FAAPIView.as_view()),
    path('api/auth/2fa/desactiver/', Desactiver2FAAPIView.as_view()),
    path('api/administration/', include('administration.urls')),
    path('api/catalogue/', include('catalogue.urls')),
    path('api/clients/', include('clients.urls')),
    path('api/founisseurs/', include('founisseurs.urls')),
    path('api/promotions/', include('promotions.urls')),
    path('api/ventes/', include('ventes.urls')),
]


from django.conf import settings
from django.conf.urls.static import static

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)