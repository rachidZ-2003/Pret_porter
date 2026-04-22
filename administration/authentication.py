from rest_framework.authentication import BaseAuthentication, get_authorization_header
from rest_framework import exceptions
from rest_framework_simplejwt.backends import TokenBackend
from django.conf import settings

from administration.models import Utilisateur


class UtilisateurJWTAuthentication(BaseAuthentication):
    def _get_backend(self):
        jwt_settings = getattr(settings, 'SIMPLE_JWT', {})
        algorithm = jwt_settings.get('ALGORITHM', 'HS256')
        signing_key = jwt_settings.get('SIGNING_KEY', settings.SECRET_KEY)
        verifying_key = jwt_settings.get('VERIFYING_KEY', None)
        return TokenBackend(
            algorithm=algorithm,
            signing_key=signing_key,
            verifying_key=verifying_key,
        )

    def authenticate(self, request):
        header = get_authorization_header(request).split()
        if not header or header[0].lower() != b'bearer':
            return None

        if len(header) != 2:
            raise exceptions.AuthenticationFailed('Entête Authorization invalide.')

        token = header[1].decode('utf-8')
        backend = self._get_backend()

        try:
            validated = backend.decode(token, verify=True)
        except Exception:
            raise exceptions.AuthenticationFailed('Jeton invalide ou expiré.')

        token_type = validated.get('token_type') or validated.get('type')
        if token_type != 'access':
            raise exceptions.AuthenticationFailed('Jeton non autorisé pour cette opération.')

        user_id = validated.get('user_id')
        if not user_id:
            raise exceptions.AuthenticationFailed('Jeton sans utilisateur.')

        try:
            utilisateur = Utilisateur.objects.get(id=user_id, actif=True)
        except Utilisateur.DoesNotExist:
            raise exceptions.AuthenticationFailed('Utilisateur introuvable.')

        request.utilisateur = utilisateur
        return (utilisateur, token)
