from django.db import models

# Create your models here.
"""
APP : fournisseurs
"""

from django.db import models

class Fournisseur(models.Model):
   
    raison_sociale = models.CharField(
        max_length=200,
        help_text="Nom légal complet du fournisseur."
    )

    contact = models.CharField(
        max_length=150,
        blank=True,
        help_text="Nom du contact commercial chez le fournisseur."
    )

    telephone = models.CharField(
        max_length=30,
        blank=True,
        help_text="Téléphone principal du fournisseur."
    )

    email = models.EmailField(
        blank=True,
        help_text="Email commercial pour les commandes."
    )

    adresse = models.TextField(
        blank=True,
        help_text="Adresse complète du fournisseur."
    )

    pays = models.CharField(
        max_length=100,
        blank=True,
        help_text="Pays du fournisseur. Utile pour les imports et la gestion des devises."
    )

    delai_livraison = models.PositiveIntegerField(
        default=7,
        help_text=(
            "Délai de livraison habituel en jours ouvrés. "
            "Utilisé pour calculer la date prévisionnelle de réception."
        )
    )

    conditions_paiement = models.TextField(
        blank=True,
        help_text="Conditions de règlement : virement à 30 jours, paiement à la commande, etc."
    )

    actif = models.BooleanField(
        default=True,
        help_text="Fournisseur désactivé = n'apparaît plus dans les nouveaux bons de commande."
    )

    notes = models.TextField(
        blank=True,
        help_text="Notes internes : qualité des produits, fiabilité des délais, contacts alternatifs."
    )

    magasin = models.ForeignKey(
        'administration.Magasin',
        on_delete=models.PROTECT,
        related_name='fournisseurs',
        help_text="Magasin ayant ce fournisseur dans son répertoire."
    )

    class Meta:
        verbose_name = "Fournisseur"
        verbose_name_plural = "Fournisseurs"
        ordering = ['raison_sociale']

    def __str__(self):
        return self.raison_sociale


# =============================================================================
# COMMANDE FOURNISSEUR
# =============================================================================

class CommandeFournisseur(models.Model):
   
    STATUT_CHOICES = [
        ('en_attente',          'En attente'),
        ('partiellement_recue', 'Partiellement reçue'),
        ('soldee',              'Soldée (tout reçu)'),
        ('annulee',             'Annulée'),
    ]

    numero = models.CharField(
        max_length=50,
        unique=True,
        help_text="Numéro de bon de commande. Ex : 'BC-2026-0018'. Communiqué au fournisseur."
    )

    fournisseur = models.ForeignKey(
        'Fournisseur',
        on_delete=models.PROTECT,
        related_name='commandes',
        help_text="Fournisseur destinataire de la commande."
    )

    date_commande = models.DateTimeField(
        auto_now_add=True,
        help_text="Date de création du bon de commande."
    )

    date_livraison_prevue = models.DateField(
        null=True,
        blank=True,
        help_text="Date prévisionnelle de livraison, calculée depuis delai_livraison du fournisseur."
    )

    date_livraison_effective = models.DateField(
        null=True,
        blank=True,
        help_text="Date réelle de la dernière réception. Permet d'évaluer la ponctualité du fournisseur."
    )

    statut = models.CharField(
        max_length=30,
        choices=STATUT_CHOICES,
        default='en_attente',
        help_text="État de la commande. Géré automatiquement par le service métier."
    )

    total_ht = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text=(
            "Montant total HT de la commande. "
            "Recalculé automatiquement depuis la somme des LigneCommande."
        )
    )

    utilisateur = models.ForeignKey(
        'administration.Utilisateur',
        on_delete=models.PROTECT,
        related_name='commandes_fournisseur',
        help_text="Utilisateur ayant passé la commande (gestionnaire de stock ou gérant)."
    )

    notes = models.TextField(
        blank=True,
        help_text="Instructions spéciales au fournisseur : conditionnement, priorité, références."
    )

    magasin = models.ForeignKey(
        'administration.Magasin',
        on_delete=models.PROTECT,
        related_name='commandes_fournisseur',
        help_text="Magasin pour lequel cette commande est passée."
    )

    class Meta:
        verbose_name = "Commande fournisseur"
        verbose_name_plural = "Commandes fournisseurs"
        ordering = ['-date_commande']

    def __str__(self):
        return f"{self.numero} — {self.fournisseur} — {self.get_statut_display()}"

    def recalculer_total(self):
        """
        Recalcule le total_ht depuis la somme des lignes de commande.
        À appeler après chaque ajout / modification / suppression d'une LigneCommande.
        """
        from django.db.models import Sum
        total = self.lignes.aggregate(total=Sum('total_ligne'))['total'] or 0
        self.total_ht = total
        self.save(update_fields=['total_ht'])


# =============================================================================
# LIGNE COMMANDE  ⚠️ CLASSE AJOUTÉE — manquante dans le document original
# =============================================================================

class LigneCommande(models.Model):
   
    commande = models.ForeignKey(
        'CommandeFournisseur',
        on_delete=models.CASCADE,
        related_name='lignes',
        help_text=(
            "Commande fournisseur à laquelle appartient cette ligne. "
            "CASCADE : supprimée si la commande est supprimée."
        )
    )

    declinaison = models.ForeignKey(
        'catalogue.Declinaison',
        on_delete=models.PROTECT,
        related_name='lignes_commande',
        help_text=(
            "Déclinaison précise de l'article commandé (article + taille + coloris). "
            "PROTECT : on conserve l'historique des commandes même si la déclinaison est désactivée."
        )
    )

    quantite_commandee = models.PositiveIntegerField(
        help_text="Nombre d'unités commandées au fournisseur."
    )

    quantite_recue = models.PositiveIntegerField(
        default=0,
        help_text=(
            "Nombre d'unités effectivement reçues à ce jour. "
            "Incrémenté à chaque réception partielle ou totale. "
            "Quand quantite_recue == quantite_commandee, la ligne est soldée."
        )
    )

    prix_achat_unitaire = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text=(
            "Prix d'achat unitaire HT négocié avec le fournisseur pour cette commande. "
            "Figé à la création de la ligne (peut différer du prix_achat_ht habituel de l'article)."
        )
    )

    total_ligne = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text=(
            "Montant total HT de cette ligne = quantite_commandee × prix_achat_unitaire. "
            "Calculé automatiquement dans save()."
        )
    )

    class Meta:
        verbose_name = "Ligne de commande"
        verbose_name_plural = "Lignes de commande"
        ordering = ['commande', 'declinaison']
        constraints = [
            # Une même déclinaison ne peut apparaître qu'une fois par commande
            models.UniqueConstraint(
                fields=['commande', 'declinaison'],
                name='unique_ligne_commande_declinaison'
            )
        ]

    def __str__(self):
        return (
            f"{self.declinaison} | "
            f"commandé: {self.quantite_commandee} | "
            f"reçu: {self.quantite_recue} | "
            f"{self.total_ligne} FCFA"
        )

    @property
    def quantite_restante(self):
        """Quantité encore attendue du fournisseur."""
        return self.quantite_commandee - self.quantite_recue

    @property
    def est_soldee(self):
        """True si toute la quantité commandée a été reçue."""
        return self.quantite_recue >= self.quantite_commandee

    def save(self, *args, **kwargs):
        """Calcule automatiquement le total de la ligne avant sauvegarde."""
        self.total_ligne = self.quantite_commandee * self.prix_achat_unitaire
        super().save(*args, **kwargs)
        # Met à jour le total de la commande parente
        self.commande.recalculer_total()
