"""
=============================================================================
SERIALIZERS — APP : administration
=============================================================================
Couvre :
  - MagasinSerializer
  - RoleSerializer
  - UtilisateurSerializer (lecture, création, mise à jour)
  - AuthSerializer          → connexion étape 1 (email + mot de passe)
  - Verify2FASerializer     → connexion étape 2 (code OTP)
  - Activer2FASerializer    → activation du 2FA par l'utilisateur
  - Confirmer2FASerializer  → confirmation après scan QR code
  - ChangerMotDePasseSerializer
  - ChangerPINSerializer
  - JournalAuditSerializer  (lecture seule)
  - ParametreSerializer

Règles appliquées :
  - Les champs sensibles (mot_de_passe, code_pin, deux_facteurs_secret,
    codes_secours) ne sont JAMAIS retournés dans les réponses API.
  - write_only=True  sur tous les champs secrets en entrée.
  - read_only=True   sur tous les champs calculés ou auto-générés.
=============================================================================
"""

from rest_framework import serializers
from django.contrib.auth.hashers import make_password, check_password
from django.utils import timezone
from administration.models import (
    Magasin, Role, Utilisateur, JournalAudit, Parametre
)


# =============================================================================
# MAGASIN
# =============================================================================

class MagasinSerializer(serializers.ModelSerializer):
    """
    Sérialise les informations d'une boutique.
    Utilisé dans le contexte global Next.js pour afficher le nom,
    la devise et le logo sur tous les écrans.
    """

    class Meta:
        model = Magasin
        fields = [
            'id', 'nom', 'adresse', 'telephone', 'email',
            'logo', 'devise', 'taux_tva_defaut', 'actif',
        ]
        read_only_fields = ['id']


class MagasinResumeSerializer(serializers.ModelSerializer):
    """
    Version allégée pour les listes déroulantes et le contexte JWT.
    On évite de renvoyer l'adresse complète dans chaque token.
    """

    class Meta:
        model = Magasin
        fields = ['id', 'nom', 'devise']
        read_only_fields = ['id', 'nom', 'devise']


# =============================================================================
# ROLE
# =============================================================================

class RoleSerializer(serializers.ModelSerializer):
    """
    Sérialise un rôle avec son dictionnaire de permissions JSON.
    Accessible uniquement aux administrateurs.
    """

    class Meta:
        model = Role
        fields = ['id', 'libelle', 'description', 'permissions']
        read_only_fields = ['id']


class RoleResumeSerializer(serializers.ModelSerializer):
    """
    Version allégée sans le JSON des permissions.
    Utilisée dans UtilisateurSerializer pour éviter la fuite de permissions.
    """

    class Meta:
        model = Role
        fields = ['id', 'libelle']
        read_only_fields = ['id', 'libelle']


# =============================================================================
# UTILISATEUR
# =============================================================================
class UtilisateurLectureSerializer(serializers.ModelSerializer):
    role = RoleResumeSerializer(read_only=True)
    magasin = MagasinResumeSerializer(read_only=True)

    class Meta:
        model = Utilisateur
        fields = [
            'id', 'nom', 'prenom', 'email',
            'role', 'magasin', 'actif',
            'deux_facteurs_actif', 'deux_facteurs_methode',
            'derniere_connexion', 'date_creation',
        ]
        read_only_fields = fields
class UtilisateurCreationSerializer(serializers.ModelSerializer):
    mot_de_passe = serializers.CharField(
        write_only=True,
        min_length=8
    )

    role_id = serializers.PrimaryKeyRelatedField(
        queryset=Role.objects.all(),
        source='role',
        required=False,
        allow_null=True
    )

    magasin_id = serializers.PrimaryKeyRelatedField(
        queryset=Magasin.objects.all(),
        source='magasin',
        required=False,
        allow_null=True
    )

    class Meta:
        model = Utilisateur
        fields = [
            'nom', 'prenom', 'email',
            'mot_de_passe', 'role_id', 'magasin_id', 'actif',
        ]

    def create(self, validated_data):
        password = validated_data.pop("mot_de_passe")

        user = Utilisateur(**validated_data)
        user.set_password(password)   # 🔥 IMPORTANT
        user.save()
        return user
class UtilisateurMiseAJourSerializer(serializers.ModelSerializer):

    role_id = serializers.PrimaryKeyRelatedField(
        queryset=Role.objects.all(),
        source='role',
        required=False,
        allow_null=True
    )

    magasin_id = serializers.PrimaryKeyRelatedField(
        queryset=Magasin.objects.all(),
        source='magasin',
        required=False,
        allow_null=True
    )

    class Meta:
        model = Utilisateur
        fields = [
            'nom', 'prenom', 'email',
            'role_id', 'magasin_id', 'actif'
        ]

    def validate_email(self, value):
        if self.instance and self.instance.email == value:
            return value

        if Utilisateur.objects.filter(email=value).exists():
            raise serializers.ValidationError("Cet email est déjà utilisé.")
        return value

# =============================================================================
# AUTHENTIFICATION — ÉTAPE 1 : email + mot de passe
# =============================================================================
class AuthSerializer(serializers.Serializer):
    """
    Étape 1 : login email + mot de passe
    """

    email = serializers.EmailField()
    mot_de_passe = serializers.CharField(write_only=True)

    def validate(self, data):
        email = data.get("email")
        mot_de_passe = data.get("mot_de_passe")

        try:
            utilisateur = Utilisateur.objects.select_related(
                "role", "magasin"
            ).get(email=email, actif=True)
        except Utilisateur.DoesNotExist:
            raise serializers.ValidationError("Email ou mot de passe incorrect.")

        # ✅ UTILISATION CORRECTE DU MODELE
        if not utilisateur.check_password(mot_de_passe):
            raise serializers.ValidationError("Email ou mot de passe incorrect.")

        data["utilisateur"] = utilisateur
        return data

# =============================================================================
# AUTHENTIFICATION — ÉTAPE 2 : vérification du code OTP (2FA)
# =============================================================================

class Verify2FASerializer(serializers.Serializer):
    """
    Étape 2 de la connexion quand le 2FA est activé.

    Le frontend envoie :
      - token_temporaire : reçu à l'étape 1
      - code            : code OTP à 6 chiffres (ou code de secours)

    Retourne access_token + refresh_token si le code est valide.
    """

    token_temporaire = serializers.CharField(
        write_only=True,
        help_text="Token temporaire reçu lors de l'étape 1 de connexion."
    )

    code = serializers.CharField(
        max_length=20,
        write_only=True,
        help_text="Code OTP à 6 chiffres depuis l'application 2FA, ou code de secours."
    )

    def validate(self, data):
        from administration.services import AuthService

        # Décoder le token temporaire
        payload = AuthService.decoder_token(data['token_temporaire'])

        if not payload:
            raise serializers.ValidationError(
                "Token temporaire invalide ou expiré. Recommencez la connexion."
            )

        if payload.get('type') != '2fa_temp':
            raise serializers.ValidationError(
                "Ce token n'est pas un token 2FA temporaire."
            )

        # Récupérer l'utilisateur
        try:
            utilisateur = Utilisateur.objects.select_related(
                'role', 'magasin'
            ).get(id=payload['user_id'], actif=True)
        except Utilisateur.DoesNotExist:
            raise serializers.ValidationError("Utilisateur introuvable.")

        # Vérifier le code OTP ou le code de secours
        code = data['code']
        code_valide = utilisateur.verifier_code_totp(code)

        if not code_valide:
            # Essayer avec les codes de secours
            code_valide = utilisateur.utiliser_code_secours(code)

        if not code_valide:
            raise serializers.ValidationError(
                "Code OTP invalide ou expiré."
            )

        data['utilisateur'] = utilisateur
        return data


# =============================================================================
# ACTIVATION DU 2FA — ÉTAPE 1 : demande d'activation
# =============================================================================

class Activer2FASerializer(serializers.Serializer):
    """
    Déclenche l'activation du 2FA pour l'utilisateur connecté.

    Ne requiert aucun champ en entrée — l'utilisateur est identifié
    via request.utilisateur dans la vue.

    Retourne :
      - qr_code_url : URL à encoder en QR code pour Google Authenticator
      - secret      : clé base32 (pour saisie manuelle si scan impossible)
      - methode     : méthode choisie
    """

    methode = serializers.ChoiceField(
        choices=[('totp', 'Application'), ('sms', 'SMS'), ('email', 'Email')],
        default='totp',
        help_text="Méthode de double authentification souhaitée."
    )


# =============================================================================
# ACTIVATION DU 2FA — ÉTAPE 2 : confirmation par code OTP
# =============================================================================

class Confirmer2FASerializer(serializers.Serializer):
    """
    Confirme l'activation du 2FA après que l'utilisateur a scanné le QR code.

    Le frontend envoie le premier code OTP généré par l'application.
    Si valide, le 2FA est officiellement activé et les codes de secours
    sont générés et retournés UNE SEULE FOIS.

    ⚠️ Les codes de secours retournés ici ne peuvent plus être récupérés.
       Le frontend doit les afficher et demander à l'utilisateur de les noter.
    """

    code = serializers.CharField(
        max_length=6,
        min_length=6,
        write_only=True,
        help_text="Premier code OTP généré par l'application après scan du QR code."
    )

    def validate_code(self, valeur):
        if not valeur.isdigit():
            raise serializers.ValidationError(
                "Le code OTP doit contenir uniquement des chiffres."
            )
        return valeur


# =============================================================================
# DÉSACTIVATION DU 2FA
# =============================================================================
class Desactiver2FASerializer(serializers.Serializer):
    mot_de_passe = serializers.CharField(write_only=True)

    def validate_mot_de_passe(self, value):
        utilisateur = self.context['request'].user

        if not utilisateur.check_password(value):
            raise serializers.ValidationError("Mot de passe incorrect.")

        return value

# =============================================================================
# CHANGER MOT DE PASSE
# =============================================================================
class ChangerMotDePasseSerializer(serializers.Serializer):

    ancien_mot_de_passe = serializers.CharField(write_only=True)
    nouveau_mot_de_passe = serializers.CharField(write_only=True, min_length=8)
    confirmation = serializers.CharField(write_only=True)

    def validate(self, data):
        utilisateur = self.context['request'].user

        # ✔ vérifier ancien mot de passe
        if not utilisateur.check_password(data['ancien_mot_de_passe']):
            raise serializers.ValidationError({
                'ancien_mot_de_passe': "Mot de passe actuel incorrect."
            })

        # ✔ confirmation
        if data['nouveau_mot_de_passe'] != data['confirmation']:
            raise serializers.ValidationError({
                'confirmation': "Les mots de passe ne correspondent pas."
            })

        # ✔ empêcher reuse ancien password
        if data['ancien_mot_de_passe'] == data['nouveau_mot_de_passe']:
            raise serializers.ValidationError({
                'nouveau_mot_de_passe': "Le nouveau mot de passe doit être différent."
            })

        return data

# =============================================================================
# CHANGER CODE PIN
# =============================================================================

class ChangerPINSerializer(serializers.Serializer):
    """
    Permet à un utilisateur de changer son code PIN de caisse.
    """

    nouveau_pin = serializers.CharField(
        write_only=True,
        min_length=4,
        max_length=6,
        help_text="Nouveau code PIN (4 à 6 chiffres)."
    )

    confirmation_pin = serializers.CharField(
        write_only=True,
        help_text="Répétition du nouveau PIN."
    )

    def validate(self, data):
        if not data['nouveau_pin'].isdigit():
            raise serializers.ValidationError(
                {'nouveau_pin': "Le PIN doit contenir uniquement des chiffres."}
            )

        if data['nouveau_pin'] != data['confirmation_pin']:
            raise serializers.ValidationError(
                {'confirmation_pin': "Les deux PIN ne correspondent pas."}
            )

        return data


# =============================================================================
# VÉRIFICATION PIN CAISSE (déverrouillage rapide)
# =============================================================================
class VerifierPINSerializer(serializers.Serializer):
    """
    Vérifie le code PIN pour déverrouillage rapide POS.
    """

    code_pin = serializers.CharField(
        write_only=True,
        min_length=4,
        max_length=6
    )

    def validate(self, data):
        request = self.context['request']
        utilisateur = request.user

        if not utilisateur.actif:
            raise serializers.ValidationError("Utilisateur inactif.")

        if not check_password(data['code_pin'], utilisateur.code_pin):
            raise serializers.ValidationError("Code PIN incorrect.")

        data['utilisateur'] = utilisateur
        return data
# =============================================================================
# JOURNAL AUDIT (lecture seule)
# =============================================================================

class JournalAuditSerializer(serializers.ModelSerializer):
    """
    Lecture seule — la boîte noire ne peut être ni créée ni modifiée via l'API.
    Accessible uniquement aux administrateurs.
    """

    utilisateur_nom = serializers.SerializerMethodField()

    class Meta:
        model = JournalAudit
        fields = [
            'id', 'utilisateur', 'utilisateur_nom',
            'action', 'entite', 'entite_id',
            'ancienne_valeur', 'nouvelle_valeur',
            'date_heure', 'adresse_ip',
        ]
        read_only_fields = fields

    def get_utilisateur_nom(self, obj):
        """Retourne le nom complet de l'utilisateur ou 'Système' si null."""
        if obj.utilisateur:
            return f"{obj.utilisateur.prenom} {obj.utilisateur.nom}"
        return "Système"


# =============================================================================
# PARAMETRE
# =============================================================================

class ParametreSerializer(serializers.ModelSerializer):
    """
    Gestion des paramètres de configuration.
    Accessible uniquement aux administrateurs et gérants.
    """

    class Meta:
        model = Parametre
        fields = [
            'id', 'cle', 'valeur', 'type',
            'description', 'magasin',
        ]
        read_only_fields = ['id']

    def validate_cle(self, valeur):
        """
        Vérifie l'unicité de la clé lors d'une création.
        Lors d'une mise à jour, exclut l'instance courante.
        """
        qs = Parametre.objects.filter(cle=valeur)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError(
                f"La clé '{valeur}' existe déjà."
            )
        return valeur