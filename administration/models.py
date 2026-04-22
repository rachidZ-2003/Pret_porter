from django.db import models

# Create your models here.
"""
=============================================================================
APP : administration
=============================================================================
Contient les classes transversales qui gouvernent tout le système :
  - Magasin     : la boutique physique (supporte le multi-boutiques)
  - Role        : ensemble de permissions accordées à un groupe d'utilisateurs
  - Utilisateur : compte de connexion (vendeur, gérant, gestionnaire stock...)
  - JournalAudit: boîte noire immuable de toutes les actions critiques
  - Parametre   : table clé-valeur pour les réglages sans redéploiement

Pourquoi cette app en premier ?
  Toutes les autres apps (ventes, catalogue, clients...) ont des FK vers
  Magasin et Utilisateur. Django résout les dépendances entre apps grâce aux
  strings 'app.Modele', donc l'ordre d'import n'est pas un problème,
  mais conceptuellement cette app est le socle du système.
=============================================================================
"""


from django.contrib.auth.hashers import make_password, check_password
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
import pyotp
import random
import string


# =============================================================================
# MAGASIN
# =============================================================================

class Magasin(models.Model):
   

    nom = models.CharField(
        max_length=150,
        help_text="Nom commercial affiché sur les tickets et factures. Ex : 'Boutique Fatou Mode'."
    )

    adresse = models.TextField(
        help_text="Adresse complète imprimée sur les documents commerciaux."
    )

    telephone = models.CharField(
        max_length=30,
        blank=True,
        help_text="Téléphone de contact affiché sur les tickets."
    )

    email = models.EmailField(
        blank=True,
        help_text="Email de contact du magasin."
    )

    logo = models.ImageField(
        upload_to='magasins/logos/',
        null=True,
        blank=True,
        help_text="Logo affiché sur les tickets imprimés et dans l'interface Next.js."
    )

    devise = models.CharField(
        max_length=10,
        default='XOF',
        help_text=(
            "Code ISO de la devise locale. XOF = FCFA (Afrique de l'Ouest), "
            "EUR, MAD... Utilisé pour formater tous les montants affichés."
        )
    )

    taux_tva_defaut = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=18.00,
        help_text=(
            "Taux de TVA par défaut (en %) appliqué aux nouveaux articles créés "
            "dans ce magasin. Peut être surchargé article par article."
        )
    )

    actif = models.BooleanField(
        default=True,
        help_text="Si False, la boutique n'est plus accessible dans l'interface."
    )

    class Meta:
        verbose_name = "Magasin"
        verbose_name_plural = "Magasins"
        ordering = ['nom']

    def __str__(self):
        return self.nom


# =============================================================================
# ROLE
# =============================================================================

class Role(models.Model):
   

    libelle = models.CharField(
        max_length=100,
        unique=True,
        help_text="Nom du rôle. Ex : 'Administrateur', 'Vendeur'."
    )

    description = models.TextField(
        blank=True,
        help_text="Description des droits accordés par ce rôle, affichée dans l'admin."
    )

    permissions = models.JSONField(
        default=dict,
        help_text=(
            "Dictionnaire JSON des permissions accordées. "
            "Exemple : {'vente.create': true, 'config.edit': false}. "
            "Vérifié par une permission class DRF custom."
        )
    )

    class Meta:
        verbose_name = "Rôle"
        verbose_name_plural = "Rôles"
        ordering = ['libelle']

    def __str__(self):
        return self.libelle

    def a_permission(self, cle: str) -> bool:
        """Vérifie si ce rôle possède une permission donnée."""
        return bool(self.permissions.get(cle, False))


# =============================================================================
# UTILISATEUR
# =============================================================================

from django.contrib.auth.base_user import BaseUserManager

class UtilisateurManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Email obligatoire")

        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        return self.create_user(email, password, **extra_fields)


class Utilisateur(AbstractBaseUser, PermissionsMixin):
   
    USERNAME_FIELD = "email"
    objects = UtilisateurManager()
    REQUIRED_FIELDS = ["nom", "prenom"]
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    nom = models.CharField(
        max_length=100,
        help_text="Nom de famille, affiché dans l'interface et les rapports."
    )

    prenom = models.CharField(
        max_length=100,
        help_text="Prénom."
    )

    email = models.EmailField(
        unique=True,
        help_text=(
            "Email professionnel. Utilisé pour les notifications système "
            "et la réinitialisation de mot de passe."
        )
    )

    role = models.ForeignKey(
        'Role',
        on_delete=models.PROTECT,   # On ne supprime pas un rôle encore utilisé
        null=True,
        blank=True,
        related_name='utilisateurs',
        help_text=(
            "Rôle déterminant les permissions (admin, vendeur). "
            "PROTECT : impossible de supprimer un rôle tant qu'un utilisateur le porte."
        )
    )

    actif = models.BooleanField(
        default=True,
        help_text=(
            "Compte désactivé = impossible de se connecter. "
            "Préférer la désactivation à la suppression pour conserver l'historique."
        )
    )

   

    code_pin = models.CharField(
        max_length=128,     # Stocké hashé (make_password produit ~128 chars)
        blank=True,
        help_text=(
            "Code PIN à 4-6 chiffres pour déverrouillage rapide de la caisse. "
            "Hashé en base avec make_password()."
        )
    )

    deux_facteurs_secret = models.CharField(
        max_length=64,
        blank=True,
        help_text="Secret TOTP utilisé pour générer les codes 2FA."
    )

    deux_facteurs_actif = models.BooleanField(
        default=False,
        help_text="Indique si le 2FA est activé pour cet utilisateur."
    )

    deux_facteurs_methode = models.CharField(
        max_length=20,
        choices=[
            ('totp', 'Application'),
            ('sms', 'SMS'),
            ('email', 'Email'),
        ],
        default='totp',
        help_text="Méthode choisie pour la double authentification."
    )

    codes_secours = models.JSONField(
        default=list,
        blank=True,
        help_text=(
            "Codes de secours utilisables une seule fois lorsque le 2FA est activé."
        )
    )

    derniere_connexion = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Date de dernière connexion validée."
    )

    date_creation = models.DateTimeField(
        auto_now_add=True,
        help_text="Date de création du compte utilisateur."
    )

    magasin = models.ForeignKey(
        'Magasin',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='utilisateurs',
        help_text=(
            "Magasin de rattachement principal. "
            "Null pour les administrateurs ayant accès à toutes les boutiques."
        )
    )

    class Meta:
        verbose_name = "Utilisateur"
        verbose_name_plural = "Utilisateurs"
        ordering = ['nom', 'prenom']

    @property
    def username(self):
        return self.email

    @property
    def is_authenticated(self):
        return True

    @property
    def is_anonymous(self):
        return False

    def __str__(self):
        return f"{self.prenom} {self.nom} ({self.email})"

   

    def generate_2fa_secret(self, methode: str = 'totp') -> str:
        self.deux_facteurs_secret = pyotp.random_base32()
        self.deux_facteurs_methode = methode
        self.deux_facteurs_actif = False
        self.codes_secours = []
        self.save(update_fields=['deux_facteurs_secret', 'deux_facteurs_methode', 'deux_facteurs_actif', 'codes_secours'])
        return self.deux_facteurs_secret

    def get_otpauth_url(self) -> str:
        if not self.deux_facteurs_secret:
            return ''
        return pyotp.totp.TOTP(self.deux_facteurs_secret).provisioning_uri(
            name=self.email,
            issuer_name='PretAPoter',
        )

    def verifier_code_totp(self, code: str) -> bool:
        if not self.deux_facteurs_secret:
            return False
        totp = pyotp.TOTP(self.deux_facteurs_secret)
        return totp.verify(code, valid_window=1)

    def generer_codes_secours(self, nombre: int = 10) -> list[str]:
        codes = [
            ''.join(random.choices(string.digits, k=8))
            for _ in range(nombre)
        ]
        self.codes_secours = codes
        self.save(update_fields=['codes_secours'])
        return codes

    def confirmer_deux_facteurs(self, code: str) -> list[str] | None:
        if not self.verifier_code_totp(code):
            return None
        self.deux_facteurs_actif = True
        codes = self.generer_codes_secours()
        self.save(update_fields=['deux_facteurs_actif', 'codes_secours'])
        return codes

    def utiliser_code_secours(self, code: str) -> bool:
        if code in self.codes_secours:
            self.codes_secours = [c for c in self.codes_secours if c != code]
            self.save(update_fields=['codes_secours'])
            return True
        return False

    def set_pin(self, pin_brut: str):
        """Hash et stocke le code PIN. Appeler cette méthode, jamais affecter directement."""
        self.code_pin = make_password(pin_brut)

    def a_permission(self, cle: str) -> bool:
        """Délègue la vérification de permission au rôle associé."""
        if self.role:
            return self.role.a_permission(cle)
        return False


# =============================================================================
# JOURNAL AUDIT
# =============================================================================

class JournalAudit(models.Model):
   
    utilisateur = models.ForeignKey(
        'Utilisateur',
        on_delete=models.SET_NULL,  # Si l'utilisateur est supprimé, on garde la trace
        null=True,
        related_name='actions_audit',
        help_text="Utilisateur ayant déclenché l'action."
    )

    action = models.CharField(
        max_length=100,
        help_text=(
            "Verbe de l'opération. Ex : 'CREATE', 'UPDATE', 'DELETE', "
            "'LOGIN', 'VALIDER_VENTE', 'CLOTURER_CAISSE'."
        )
    )

    entite = models.CharField(
        max_length=100,
        help_text=(
            "Nom de la classe Django concernée. "
            "Ex : 'Vente', 'Article', 'MouvementStock'. Permet de filtrer par type d'objet."
        )
    )

    entite_id = models.UUIDField(
        null=True,
        blank=True,
        help_text=(
            "UUID de l'objet modifié. Combiné avec 'entite' pour retrouver l'enregistrement source. "
            "Pas de vraie FK pour éviter les contraintes de suppression."
        )
    )

    ancienne_valeur = models.JSONField(
        null=True,
        blank=True,
        help_text=(
            "Snapshot JSON de l'état de l'objet AVANT la modification. "
            "Null pour un CREATE."
        )
    )

    nouvelle_valeur = models.JSONField(
        null=True,
        blank=True,
        help_text=(
            "Snapshot JSON de l'état de l'objet APRÈS la modification. "
            "Null pour un DELETE."
        )
    )

    date_heure = models.DateTimeField(
        auto_now_add=True,
        help_text="Horodatage côté serveur. Généré automatiquement, non modifiable."
    )

    adresse_ip = models.GenericIPAddressField(
        null=True,
        blank=True,
        help_text="IP du poste ayant effectué l'action. Utile pour les audits de sécurité."
    )

    class Meta:
        verbose_name = "Journal d'audit"
        verbose_name_plural = "Journal d'audit"
        ordering = ['-date_heure']
        # Index sur entite + entite_id pour les recherches d'historique par objet
        indexes = [
            models.Index(fields=['entite', 'entite_id']),
            models.Index(fields=['utilisateur', 'date_heure']),
        ]

    def __str__(self):
        return f"{self.action} — {self.entite} — {self.date_heure:%d/%m/%Y %H:%M}"

    def save(self, *args, **kwargs):
        """Empêche toute modification d'une entrée d'audit existante."""
        if self.pk:
            raise PermissionError("Les entrées du journal d'audit sont immuables.")
        super().save(*args, **kwargs)


# =============================================================================
# PARAMETRE
# =============================================================================

class Parametre(models.Model):
  
    TYPE_CHOICES = [
        ('string',  'Texte'),
        ('integer', 'Entier'),
        ('boolean', 'Booléen (true/false)'),
        ('decimal', 'Décimal'),
        ('json',    'JSON'),
    ]

  

    cle = models.CharField(
        max_length=200,
        unique=True,
        help_text=(
            "Clé unique en snake_case avec namespace. "
            "Ex : 'fidelite.taux_points_par_fcfa', 'ticket.texte_pied', "
            "'avoir.duree_validite_jours'."
        )
    )

    valeur = models.TextField(
        help_text=(
            "Valeur stockée sous forme de texte. "
            "La conversion vers le bon type (int, bool, JSON) est faite "
            "par ParametreService selon le champ 'type'."
        )
    )

    type = models.CharField(
        max_length=20,
        choices=TYPE_CHOICES,
        default='string',
        help_text="Type de la valeur. Utilisé par ParametreService pour le cast automatique."
    )

    description = models.TextField(
        blank=True,
        help_text=(
            "Explication de l'effet de ce paramètre, affichée dans l'interface "
            "d'administration pour aider le gérant à comprendre ce qu'il modifie."
        )
    )

    magasin = models.ForeignKey(
        'Magasin',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='parametres',
        help_text=(
            "Si renseigné, ce paramètre s'applique uniquement à ce magasin. "
            "Si null, c'est un paramètre global commun à toutes les boutiques."
        )
    )

    class Meta:
        verbose_name = "Paramètre"
        verbose_name_plural = "Paramètres"
        ordering = ['cle']

    def __str__(self):
        return f"{self.cle} = {self.valeur}"
