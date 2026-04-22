import base64
import io
from datetime import datetime, timedelta

import qrcode
from django.conf import settings
from rest_framework_simplejwt.backends import TokenBackend
from rest_framework_simplejwt.tokens import RefreshToken


class AuthService:
    @staticmethod
    def _token_backend():
        jwt_settings = getattr(settings, 'SIMPLE_JWT', {})
        algorithm = jwt_settings.get('ALGORITHM', 'HS256')
        signing_key = jwt_settings.get('SIGNING_KEY', settings.SECRET_KEY)
        verifying_key = jwt_settings.get('VERIFYING_KEY', None)
        return TokenBackend(
            algorithm=algorithm,
            signing_key=signing_key,
            verifying_key=verifying_key,
        )

    @staticmethod
    def generer_tokens(utilisateur):
        refresh = RefreshToken.for_user(utilisateur)
        return {
            'access': str(refresh.access_token),
            'refresh': str(refresh),
        }

    @staticmethod
    def generer_token_temporaire_2fa(utilisateur, minutes=10):
        backend = AuthService._token_backend()
        exp = datetime.utcnow() + timedelta(minutes=minutes)
        payload = {
            'user_id': str(utilisateur.id),
            'type': '2fa_temp',
            'exp': exp,
        }
        return backend.encode(payload)

    @staticmethod
    def decoder_token(token):
        backend = AuthService._token_backend()
        try:
            return backend.decode(token, verify=True)
        except Exception:
            return None

    @staticmethod
    def generer_qr_code_data_url(otp_auth_url):
        qr = qrcode.QRCode(box_size=10, border=4)
        qr.add_data(otp_auth_url)
        qr.make(fit=True)
        image = qr.make_image(fill_color='black', back_color='white')
        buffer = io.BytesIO()
        image.save(buffer, format='PNG')
        encoded = base64.b64encode(buffer.getvalue()).decode('utf-8')
        return f'data:image/png;base64,{encoded}'
