from django.db import models

# Create your models here.
"""
APP : ventes
"""

from django.db import models

class Caisse(models.Model):
   
    libelle = models.CharField(
        max_length=100,
        help_text="Nom affiché du poste. Ex : 'Caisse principale', 'Caisse rapide'."
    )

    emplacement = models.CharField(
        max_length=150,
        blank=True,
        help_text="Description physique de l'emplacement dans le magasin."
    )

    actif = models.BooleanField(
        default=True,
        help_text="Si False, la caisse ne peut plus être ouverte. Permet de désactiver un poste."
    )

    magasin = models.ForeignKey(
        'administration.Magasin',
        on_delete=models.PROTECT,
        related_name='caisses',
        help_text="Magasin auquel appartient cette caisse."
    )

    class Meta:
        verbose_name = "Caisse"
        verbose_name_plural = "Caisses"
        ordering = ['magasin', 'libelle']

    def __str__(self):
        return f"{self.libelle} — {self.magasin}"

    @property
    def solde_actuel(self):
        """
        Solde actuel = fond_caisse + total_especes de la session ouverte.
        Non stocké en base, calculé dynamiquement.
        Retourne None si aucune session n'est ouverte.
        """
        session = self.sessions.filter(statut='ouverte').first()
        if session:
            return session.fond_caisse + session.total_especes
        return None


# =============================================================================
# SESSION CAISSE
# =============================================================================

class SessionCaisse(models.Model):
   
    STATUT_CHOICES = [
        ('ouverte', 'Ouverte'),
        ('fermee',  'Fermée'),
    ]

    caisse = models.ForeignKey(
        'Caisse',
        on_delete=models.PROTECT,
        related_name='sessions',
        help_text="Caisse physique concernée."
    )

    vendeur = models.ForeignKey(
        'administration.Utilisateur',
        on_delete=models.PROTECT,
        related_name='sessions_caisse',
        help_text="Utilisateur ayant ouvert la session."
    )

    date_ouverture = models.DateTimeField(
        help_text="Moment d'ouverture de la session, enregistré côté serveur."
    )

    date_fermeture = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Moment de fermeture. Null si la session est encore ouverte."
    )

    fond_caisse = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text="Montant en espèces présent dans le tiroir à l'ouverture, déclaré manuellement."
    )

    total_encaisse = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text="Cumul de toutes les ventes encaissées pendant la session. Mis à jour en temps réel."
    )

    total_especes = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text="Part du total encaissé en espèces. Permet le contrôle du tiroir à la fermeture."
    )

    total_carte = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text="Part du total encaissé par carte bancaire et mobile money."
    )

    statut = models.CharField(
        max_length=20,
        choices=STATUT_CHOICES,
        default='ouverte',
        help_text="Une seule session 'ouverte' par caisse à la fois."
    )

    class Meta:
        verbose_name = "Session de caisse"
        verbose_name_plural = "Sessions de caisse"
        ordering = ['-date_ouverture']

    def __str__(self):
        return f"Session {self.caisse} — {self.date_ouverture:%d/%m/%Y} — {self.get_statut_display()}"

    def clean(self):
        """Vérifie qu'il n'y a pas déjà une session ouverte sur cette caisse."""
        from django.core.exceptions import ValidationError
        if self.statut == 'ouverte':
            sessions_ouvertes = SessionCaisse.objects.filter(
                caisse=self.caisse,
                statut='ouverte'
            ).exclude(pk=self.pk)
            if sessions_ouvertes.exists():
                raise ValidationError(
                    f"La caisse '{self.caisse}' a déjà une session ouverte. "
                    "Fermez-la avant d'en ouvrir une nouvelle."
                )


# =============================================================================
# VENTE
# =============================================================================

class Vente(models.Model):
  
    STATUT_CHOICES = [
        ('validee',   'Validée'),
        ('retournee', 'Retournée'),
    ]

    numero_bon = models.CharField(
        max_length=50,
        unique=True,
        help_text=(
            "Numéro de bon lisible. Ex : 'VTE-2026-00042'. "
            "Généré séquentiellement par le backend. Affiché sur le ticket de caisse."
        )
    )

    date_heure = models.DateTimeField(
        auto_now_add=True,
        help_text=(
            "Date et heure exactes de création de la vente, générées côté serveur. "
            "Ne jamais laisser le client (frontend) fournir cette valeur."
        )
    )

    statut = models.CharField(
        max_length=20,
        choices=STATUT_CHOICES,
        default='validee',
        help_text="État de la vente. 'validee' à la création, 'retournee' après traitement d'un retour."
    )

    # --- Montants (tous calculés automatiquement, ne pas modifier directement) ---
    total_ht = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text="Somme des montants HT des lignes de vente, avant TVA et remise globale."
    )

    montant_tva = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text="Montant de TVA collecté. Nécessaire pour les exports comptables."
    )

    montant_remise = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text="Montant total de remise accordée (promotions globales, remise manuelle vendeur)."
    )

    total_ttc = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text="Montant total TTC payé par le client. Affiché en grand sur le ticket."
    )

    montant_paye = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text=(
            "Somme effectivement reçue, tous modes de paiement confondus. "
            "Peut dépasser total_ttc (excès rendu en monnaie)."
        )
    )

    montant_rendu = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text="Monnaie rendue au client lors d'un paiement en espèces. = montant_paye - total_ttc si positif."
    )

    # --- Relations ---
    vendeur = models.ForeignKey(
        'administration.Utilisateur',
        on_delete=models.PROTECT,
        related_name='ventes',
        help_text="Vendeur ayant réalisé la vente. Permet le suivi des performances par vendeur."
    )

    client = models.ForeignKey(
        'clients.Client',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='ventes',
        help_text=(
            "Client associé à cette vente. "
            "Null = vente anonyme. "
            "Si renseigné, les points de fidélité sont crédités automatiquement."
        )
    )

    session_caisse = models.ForeignKey(
        'SessionCaisse',
        on_delete=models.PROTECT,
        related_name='ventes',
        help_text=(
            "Session de caisse durant laquelle la vente a été réalisée. "
            "Permet la réconciliation de caisse quotidienne."
        )
    )

    magasin = models.ForeignKey(
        'administration.Magasin',
        on_delete=models.PROTECT,
        related_name='ventes',
        help_text="Magasin où la vente a été effectuée."
    )

    class Meta:
        verbose_name = "Vente"
        verbose_name_plural = "Ventes"
        ordering = ['-date_heure']
        indexes = [
            models.Index(fields=['magasin', 'date_heure']),
            models.Index(fields=['vendeur', 'date_heure']),
            models.Index(fields=['client']),
        ]

    def __str__(self):
        return f"{self.numero_bon} — {self.total_ttc} FCFA — {self.date_heure:%d/%m/%Y %H:%M}"


# =============================================================================
# LIGNE VENTE
# =============================================================================

class LigneVente(models.Model):
   
    vente = models.ForeignKey(
        'Vente',
        on_delete=models.CASCADE,
        related_name='lignes',
        help_text="Vente à laquelle appartient cette ligne. CASCADE : supprimée avec la vente."
    )

    declinaison = models.ForeignKey(
        'catalogue.Declinaison',
        on_delete=models.PROTECT,
        related_name='lignes_vente',
        help_text=(
            "Déclinaison précise de l'article vendu (taille + coloris). "
            "PROTECT : on conserve l'historique même si la déclinaison est désactivée."
        )
    )

    quantite = models.PositiveIntegerField(
        help_text="Nombre d'unités vendues. Validation : min=1, ne peut pas dépasser le stock disponible."
    )

    # Prix figés au moment de la vente — NE PAS utiliser les prix actuels de l'article
    prix_unitaire_ht = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Prix d'une unité HT au moment de la vente. Figé pour conserver l'historique."
    )

    prix_unitaire_ttc = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Prix d'une unité TTC au moment de la vente. Affiché au client."
    )

    taux_tva = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        help_text="Taux de TVA applicable à cet article au moment de la vente. Figé pour l'historique comptable."
    )

    remise_ligne = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text="Remise en valeur absolue accordée sur cette ligne (promotion, solde). 0 si aucune remise."
    )

    total_ligne_ttc = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text=(
            "Montant total TTC de la ligne après remise. "
            "= (prix_unitaire_ttc × quantite) - remise_ligne. "
            "Calculé automatiquement dans save()."
        )
    )

    class Meta:
        verbose_name = "Ligne de vente"
        verbose_name_plural = "Lignes de vente"
        ordering = ['vente', 'declinaison']

    def __str__(self):
        return f"{self.declinaison} × {self.quantite} = {self.total_ligne_ttc} FCFA"

    def save(self, *args, **kwargs):
        """Calcule automatiquement le total de la ligne avant sauvegarde."""
        self.total_ligne_ttc = (self.prix_unitaire_ttc * self.quantite) - self.remise_ligne
        super().save(*args, **kwargs)


# =============================================================================
# PAIEMENT
# =============================================================================

class Paiement(models.Model):
   
    MODE_CHOICES = [
        ('especes',       'Espèces'),
        ('carte',         'Carte bancaire'),
        ('mobile_money',  'Mobile Money (Wave, Orange Money...)'),
        ('avoir',         'Avoir client'),
        ('bon_cadeau',    'Bon cadeau'),
        ('cheque',        'Chèque'),
    ]

    STATUT_CHOICES = [
        ('valide',     'Valide'),
        ('rejete',     'Rejeté (carte refusée)'),
        ('en_attente', 'En attente (chèque à encaisser)'),
    ]

    vente = models.ForeignKey(
        'Vente',
        on_delete=models.CASCADE,
        related_name='paiements',
        help_text="Vente associée à ce règlement."
    )

    mode_paiement = models.CharField(
        max_length=30,
        choices=MODE_CHOICES,
        help_text="Mode de paiement utilisé."
    )

    montant = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text=(
            "Montant encaissé via ce mode. "
            "La somme de tous les paiements d'une vente doit correspondre au total TTC."
        )
    )

    reference = models.CharField(
        max_length=100,
        blank=True,
        help_text=(
            "Numéro de transaction externe : numéro de chèque, référence carte, "
            "code mobile money. Laissé vide pour les espèces."
        )
    )

    date_heure = models.DateTimeField(
        auto_now_add=True,
        help_text="Horodatage du paiement côté serveur."
    )

    statut = models.CharField(
        max_length=20,
        choices=STATUT_CHOICES,
        default='valide',
        help_text="État du paiement. Permet le suivi des paiements différés (chèques)."
    )

    avoir = models.ForeignKey(
        'clients.Avoir',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='utilisations',
        help_text="Avoir utilisé si mode_paiement='avoir'. Null sinon."
    )

    session_caisse = models.ForeignKey(
        'SessionCaisse',
        on_delete=models.PROTECT,
        related_name='paiements',
        help_text="Caisse sur laquelle le paiement a été enregistré. Permet la réconciliation quotidienne."
    )

    class Meta:
        verbose_name = "Paiement"
        verbose_name_plural = "Paiements"
        ordering = ['-date_heure']

    def __str__(self):
        return f"{self.get_mode_paiement_display()} — {self.montant} FCFA — {self.vente.numero_bon}"


# =============================================================================
# RETOUR
# =============================================================================

class Retour(models.Model):
   
    TYPE_RETOUR_CHOICES = [
        ('remboursement', 'Remboursement (espèces ou carte)'),
        ('echange',       'Échange (nouvelle vente créée)'),
        ('avoir',         'Avoir (crédit sur compte client)'),
    ]

    STATUT_CHOICES = [
        ('valide', 'Validé'),
        ('annule', 'Annulé'),
    ]

    vente_originale = models.ForeignKey(
        'Vente',
        on_delete=models.PROTECT,
        related_name='retours',
        help_text="Vente d'origine concernée par le retour. Permet la traçabilité complète."
    )

    date_retour = models.DateTimeField(
        auto_now_add=True,
        help_text="Horodatage du retour enregistré côté serveur."
    )

    motif = models.TextField(
        help_text="Raison du retour saisie par le vendeur : défaut produit, taille incorrecte, etc."
    )

    type_retour = models.CharField(
        max_length=20,
        choices=TYPE_RETOUR_CHOICES,
        help_text="Nature du retour : remboursement, échange ou avoir."
    )

    montant_rembourse = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text="Montant restitué au client. 0 si type = échange ou avoir."
    )

    avoir = models.OneToOneField(
        'clients.Avoir',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='retour_source',
        help_text="Avoir généré si type_retour='avoir'. Null pour les remboursements directs."
    )

    vendeur = models.ForeignKey(
        'administration.Utilisateur',
        on_delete=models.PROTECT,
        related_name='retours_traites',
        help_text="Vendeur ayant traité le retour, pour traçabilité et responsabilité."
    )

    statut = models.CharField(
        max_length=20,
        choices=STATUT_CHOICES,
        default='valide',
        help_text="État du retour."
    )

    class Meta:
        verbose_name = "Retour"
        verbose_name_plural = "Retours"
        ordering = ['-date_retour']

    def __str__(self):
        return (
            f"Retour {self.get_type_retour_display()} "
            f"— {self.vente_originale.numero_bon} "
            f"— {self.date_retour:%d/%m/%Y}"
        )


# =============================================================================
# LIGNE RETOUR
# =============================================================================

class LigneRetour(models.Model):
   
    retour = models.ForeignKey(
        'Retour',
        on_delete=models.CASCADE,
        related_name='lignes',
        help_text="Retour auquel appartient cette ligne."
    )

    ligne_vente_originale = models.ForeignKey(
        'LigneVente',
        on_delete=models.PROTECT,
        related_name='lignes_retour',
        help_text=(
            "Ligne de vente originale concernée par ce retour. "
            "Permet de vérifier qu'on ne retourne pas plus que ce qui a été acheté."
        )
    )

    quantite_retournee = models.PositiveIntegerField(
        help_text=(
            "Nombre d'unités retournées. "
            "Validation : quantite_retournee <= ligne_vente_originale.quantite."
        )
    )

    montant_rembourse_ligne = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text="Montant remboursé pour cette ligne = quantite_retournee × prix_unitaire_ttc."
    )

    class Meta:
        verbose_name = "Ligne de retour"
        verbose_name_plural = "Lignes de retour"

    def __str__(self):
        return f"{self.ligne_vente_originale.declinaison} × {self.quantite_retournee} retournés"