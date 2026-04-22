from django.db import models

# Create your models here.
from django.db import models

# Create your models here.
"""
APP : clients
"""

from django.db import models

class Client(models.Model):
   
    GENRE_CHOICES = [
        ('homme',      'Homme'),
        ('femme',      'Femme'),
        ('non_precise', 'Non précisé'),
    ]

    NIVEAU_FIDELITE_CHOICES = [
        ('bronze',  'Bronze'),
        ('argent',  'Argent'),
        ('or',      'Or'),
        ('platine', 'Platine'),
    ]

    nom = models.CharField(
        max_length=100,
        help_text="Nom de famille du client."
    )

    prenom = models.CharField(
        max_length=100,
        help_text="Prénom du client."
    )

    telephone = models.CharField(
        max_length=30,
        unique=True,
        null=True,
        blank=True,
        help_text=(
            "Numéro de téléphone principal. Utilisé comme identifiant rapide en caisse. "
            "Format international recommandé (+226 XX XX XX XX). "
            "unique=True avec null=True : plusieurs clients peuvent ne pas avoir de téléphone."
        )
    )

    email = models.EmailField(
        unique=True,
        null=True,
        blank=True,
        help_text="Adresse email. Utilisée pour les notifications et le programme fidélité digital."
    )

    adresse = models.TextField(
        blank=True,
        help_text="Adresse postale complète. Optionnelle."
    )

    date_naissance = models.DateField(
        null=True,
        blank=True,
        help_text="Utilisée pour envoyer un SMS/email d'anniversaire avec une offre."
    )

    genre = models.CharField(
        max_length=20,
        choices=GENRE_CHOICES,
        default='non_precise',
        help_text="Permet la segmentation marketing par genre."
    )

    date_inscription = models.DateTimeField(
        auto_now_add=True,
        help_text="Date de création du compte client."
    )

    # --- Fidélité ---
    points_fidelite = models.IntegerField(
        default=0,
        help_text=(
            "Solde actuel de points de fidélité. "
            "Incrémenté à chaque achat validé, décrémenté à l'utilisation."
        )
    )

    niveau_fidelite = models.CharField(
        max_length=20,
        choices=NIVEAU_FIDELITE_CHOICES,
        default='bronze',
        help_text=(
            "Niveau fidélité : bronze, argent, or, platine. "
            "Recalculé automatiquement selon le montant total dépensé sur 12 mois glissants."
        )
    )

    numero_carte_fidelite = models.CharField(
        max_length=50,
        unique=True,
        null=True,
        blank=True,
        help_text="Numéro de carte fidélité physique ou virtuelle. Scannable en caisse via code-barres."
    )

    # --- Statut ---
    actif = models.BooleanField(
        default=True,
        help_text=(
            "Soft delete. Un client inactif n'apparaît plus dans les recherches "
            "mais son historique des achats est conservé."
        )
    )

    notes = models.TextField(
        blank=True,
        help_text="Notes internes du vendeur sur le client : préférences, tailles habituelles."
    )

    magasin = models.ForeignKey(
        'administration.Magasin',
        on_delete=models.PROTECT,
        related_name='clients',
        help_text="Magasin où le client a été enregistré."
    )

    class Meta:
        verbose_name = "Client"
        verbose_name_plural = "Clients"
        ordering = ['nom', 'prenom']
        indexes = [
            models.Index(fields=['telephone']),
            models.Index(fields=['numero_carte_fidelite']),
        ]

    def __str__(self):
        return f"{self.prenom} {self.nom}"

    @property
    def nom_complet(self):
        return f"{self.prenom} {self.nom}"


# =============================================================================
# AVOIR
# =============================================================================

class Avoir(models.Model):
    
    STATUT_CHOICES = [
        ('actif',   'Actif (utilisable)'),
        ('utilise', 'Utilisé (solde = 0)'),
        ('expire',  'Expiré (date dépassée)'),
    ]

    client = models.ForeignKey(
        'Client',
        on_delete=models.PROTECT,
        related_name='avoirs',
        help_text="Client bénéficiaire de l'avoir."
    )

    numero = models.CharField(
        max_length=50,
        unique=True,
        help_text="Numéro lisible de l'avoir. Ex : 'AV-2026-0042'. Imprimé sur le reçu de retour."
    )

    montant = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Valeur totale initiale de l'avoir."
    )

    montant_utilise = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text="Part déjà consommée en caisse. Incrémenté à chaque utilisation partielle."
    )

    date_expiration = models.DateField(
        help_text="Date limite d'utilisation. Au-delà, l'avoir passe en statut 'expire'."
    )

    statut = models.CharField(
        max_length=20,
        choices=STATUT_CHOICES,
        default='actif',
        help_text="État de l'avoir."
    )

    date_creation = models.DateTimeField(
        auto_now_add=True,
        help_text="Date de création de l'avoir."
    )

    class Meta:
        verbose_name = "Avoir"
        verbose_name_plural = "Avoirs"
        ordering = ['-date_creation']

    def __str__(self):
        return f"{self.numero} — {self.client} — solde {self.solde} FCFA"

    @property
    def solde(self):
        """Solde restant = montant initial - montant déjà utilisé."""
        return self.montant - self.montant_utilise

