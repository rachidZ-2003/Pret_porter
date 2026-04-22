from rest_framework import viewsets, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
from django.utils import timezone

from administration.models import Magasin, Role, Utilisateur, JournalAudit, Parametre
from administration.serializers import (
    ChangerMotDePasseSerializer,
    MagasinSerializer,
    RoleSerializer,
    UtilisateurLectureSerializer,
    UtilisateurCreationSerializer,
    UtilisateurMiseAJourSerializer,
    AuthSerializer,
    Verify2FASerializer,
    Activer2FASerializer,
    Confirmer2FASerializer,
    Desactiver2FASerializer,
    JournalAuditSerializer,
    ParametreSerializer,
)
from administration.services import AuthService


class MagasinViewSet(viewsets.ModelViewSet):
    queryset = Magasin.objects.all()
    serializer_class = MagasinSerializer


class RoleViewSet(viewsets.ModelViewSet):
    queryset = Role.objects.all()
    serializer_class = RoleSerializer


class UtilisateurViewSet(viewsets.ModelViewSet):
    queryset = Utilisateur.objects.all()

    def get_serializer_class(self):
        if self.action == 'create':
            return UtilisateurCreationSerializer
        if self.action in ['update', 'partial_update']:
            return UtilisateurMiseAJourSerializer
        return UtilisateurLectureSerializer

class JournalAuditViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = JournalAudit.objects.all()
    serializer_class = JournalAuditSerializer


class ParametreViewSet(viewsets.ModelViewSet):
    queryset = Parametre.objects.all()
    serializer_class = ParametreSerializer


class AuthLoginAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = AuthSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        utilisateur = serializer.validated_data['utilisateur']

        if utilisateur.deux_facteurs_actif:
            token_temporaire = AuthService.generer_token_temporaire_2fa(utilisateur)
            return Response(
                {
                    'etape': '2fa_requis',
                    'token_temporaire': token_temporaire,
                    'methode': utilisateur.deux_facteurs_methode,
                },
                status=status.HTTP_200_OK,
            )

        tokens = AuthService.generer_tokens(utilisateur)
        utilisateur.derniere_connexion = timezone.now()
        utilisateur.save(update_fields=['derniere_connexion'])

        return Response(
            {
                'access': tokens['access'],
                'refresh': tokens['refresh'],
                'user': UtilisateurLectureSerializer(utilisateur).data,
            },
            status=status.HTTP_200_OK,
        )


class Verify2FAAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = Verify2FASerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        utilisateur = serializer.validated_data['utilisateur']

        tokens = AuthService.generer_tokens(utilisateur)
        utilisateur.derniere_connexion = timezone.now()
        utilisateur.save(update_fields=['derniere_connexion'])

        return Response(
            {
                'access': tokens['access'],
                'refresh': tokens['refresh'],
                'user': UtilisateurLectureSerializer(utilisateur).data,
            },
            status=status.HTTP_200_OK,
        )


class RefreshTokenAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        refresh_token = request.data.get('refresh')
        if not refresh_token:
            return Response(
                {'refresh': 'Ce champ est requis.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            refresh = RefreshToken(refresh_token)
        except TokenError:
            return Response(
                {'refresh': 'Jeton de rafraîchissement invalide ou expiré.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        utilisateur_id = refresh.get('user_id')
        if not utilisateur_id:
            return Response(
                {'detail': 'Jeton invalide.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            utilisateur = Utilisateur.objects.get(id=utilisateur_id, actif=True)
        except Utilisateur.DoesNotExist:
            return Response(
                {'detail': 'Utilisateur introuvable.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response({'access': str(refresh.access_token)})

class MeAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UtilisateurLectureSerializer(request.user)
        return Response(serializer.data)
    

class RegisterAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = UtilisateurCreationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        utilisateur = serializer.save()
        return Response(
            UtilisateurLectureSerializer(utilisateur).data,
            status=status.HTTP_201_CREATED,
        )


class BootstrapRegisterAPIView(APIView):
    """
    Endpoint temporaire pour créer le premier utilisateur.
    À supprimer en production.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = UtilisateurCreationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        utilisateur = serializer.save()
        return Response(
            UtilisateurLectureSerializer(utilisateur).data,
            status=status.HTTP_201_CREATED,
        )


class Activer2FAAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = Activer2FASerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        utilisateur = request.user

        if utilisateur.deux_facteurs_actif:
            return Response(
                {'detail': 'La double authentification est déjà activée.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        methode = serializer.validated_data['methode']
        if methode != 'totp':
            return Response(
                {'methode': 'La seule méthode actuellement prise en charge est totp.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        utilisateur.generate_2fa_secret(methode=methode)
        otp_auth_url = utilisateur.get_otpauth_url()
        qr_code_data_url = AuthService.generer_qr_code_data_url(otp_auth_url)

        return Response(
            {
                'secret': utilisateur.deux_facteurs_secret,
                'otp_auth_url': otp_auth_url,
                'qr_code_data_url': qr_code_data_url,
                'methode': methode,
            },
            status=status.HTTP_200_OK,
        )


class Confirmer2FAAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = Confirmer2FASerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        utilisateur = request.user

        codes_secours = utilisateur.confirmer_deux_facteurs(serializer.validated_data['code'])
        if codes_secours is None:
            return Response(
                {'code': 'Le code OTP est invalide ou expiré.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {
                'detail': '2FA activé avec succès.',
                'codes_secours': codes_secours,
            },
            status=status.HTTP_200_OK,
        )


class Desactiver2FAAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = Desactiver2FASerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        utilisateur = request.user

        utilisateur.deux_facteurs_actif = False
        utilisateur.deux_facteurs_secret = ''
        utilisateur.codes_secours = []
        utilisateur.save(update_fields=['deux_facteurs_actif', 'deux_facteurs_secret', 'codes_secours'])

        return Response(
            {'detail': '2FA désactivé avec succès.'},
            status=status.HTTP_200_OK,
        )
    


class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChangerMotDePasseSerializer(
            data=request.data,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        # Récupérer l'utilisateur et changer le mot de passe
        user = request.user
        user.set_password(serializer.validated_data['nouveau_mot_de_passe'])
        user.save()
        return Response({'detail': 'Mot de passe modifié avec succès.'})
