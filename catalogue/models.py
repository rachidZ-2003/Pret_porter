from django.db import models

# Create your models here.
"""
=============================================================================
APP : catalogue
=============================================================================
Gère tout ce qui concerne les produits et le stock :
  - Categorie      : arborescence de classification des articles
  - Marque         : référentiel des marques distribuées
  - Collection     : saisons commerciales (PE 2026, AH 2025...)
  - Article        : modèle de vêtement ou accessoire (concept général)
  - Declinaison    : variante concrète et stockable (taille + coloris)
  - MouvementStock : journal immuable de tous les changements de stock
  - Inventaire     : séances de comptage physique du stock

Relation clé à retenir :
  Article (concept)  →  Declinaison (unité de stock)
  Un T-shirt col V   →  T-shirt col V / S / Noir
                        T-shirt col V / M / Noir
                        T-shirt col V / L / Blanc
=============================================================================
"""


from django.db import models


# =============================================================================
# CATEGORIE
# =============================================================================

class Categorie(models.Model):
   

    libelle = models.CharField(
        max_length=150,
        help_text="Nom affiché de la catégorie. Ex : 'Robes', 'Chaussures', 'Accessoires'."
    )

    description = models.TextField(
        blank=True,
        help_text="Description optionnelle affichée en en-tête de la page de catégorie."
    )

    categorie_parent = models.ForeignKey(
        'self',
        on_delete=models.PROTECT,   # On ne supprime pas une catégorie parente si elle a des enfants
        null=True,
        blank=True,
        related_name='sous_categories',
        help_text=(
            "Catégorie parente. Null = catégorie racine. "
            "Permet la hiérarchie auto-référente. "
            "PROTECT : impossible de supprimer si des sous-catégories existent."
        )
    )

    ordre = models.PositiveIntegerField(
        default=0,
        help_text="Ordre d'affichage dans le menu. Triées par ordre croissant."
    )

    class Meta:
        verbose_name = "Catégorie"
        verbose_name_plural = "Catégories"
        ordering = ['ordre', 'libelle']

    def __str__(self):
        if self.categorie_parent:
            return f"{self.categorie_parent} > {self.libelle}"
        return self.libelle


# =============================================================================
# MARQUE
# =============================================================================

class Marque(models.Model):
   
    nom = models.CharField(
        max_length=150,
        unique=True,
        help_text="Nom de la marque. Unique pour éviter les doublons."
    )

    logo = models.ImageField(
        upload_to='marques/logos/',
        null=True,
        blank=True,
        help_text="Logo affiché dans le catalogue et les fiches produits."
    )

    description = models.TextField(
        blank=True,
        help_text="Présentation de la marque, affichée sur sa page dédiée."
    )

    class Meta:
        verbose_name = "Marque"
        verbose_name_plural = "Marques"
        ordering = ['nom']

    def __str__(self):
        return self.nom


# =============================================================================
# COLLECTION
# =============================================================================

class Collection(models.Model):
   
    SAISON_CHOICES = [
        ('PE',           'Printemps-Été'),
        ('AH',           'Automne-Hiver'),
        ('toute_saison', 'Toute saison'),
    ]

    nom = models.CharField(
        max_length=150,
        help_text="Intitulé de la collection. Ex : 'Printemps-Été 2026'."
    )

    saison = models.CharField(
        max_length=20,
        choices=SAISON_CHOICES,
        help_text="Saison commerciale. Combinée avec 'annee' pour l'identification."
    )

    annee = models.PositiveIntegerField(
        help_text="Année de la collection. Ex : 2026."
    )

    date_debut = models.DateField(
        help_text="Date de mise en vente officielle de la collection."
    )

    date_fin = models.DateField(
        null=True,
        blank=True,
        help_text="Date de fin de commercialisation. Null = collection permanente sans fin."
    )

    class Meta:
        verbose_name = "Collection"
        verbose_name_plural = "Collections"
        ordering = ['-annee', 'saison']

    def __str__(self):
        return f"{self.nom} ({self.annee})"


# =============================================================================
# ARTICLE
# =============================================================================

class Article(models.Model):
  
    GENRE_CHOICES = [
        ('homme',  'Homme'),
        ('femme',  'Femme'),
        ('enfant', 'Enfant'),
        ('mixte',  'Mixte'),
    ]

    reference = models.CharField(
        max_length=100,
        unique=True,
        help_text=(
            "Code article interne lisible. Ex : 'ART-2026-001'. "
            "Unique dans tout le catalogue. Généré séquentiellement par le backend."
        )
    )

    designation = models.CharField(
        max_length=200,
        help_text="Nom commercial affiché en boutique et sur le ticket de caisse."
    )

    description = models.TextField(
        blank=True,
        help_text="Description détaillée : matière, entretien, conseils de port."
    )

    marque = models.ForeignKey(
        'Marque',
        on_delete=models.PROTECT,
        related_name='articles',
        help_text="Marque de l'article. PROTECT : impossible de supprimer une marque utilisée."
    )

    categorie = models.ForeignKey(
        'Categorie',
        on_delete=models.PROTECT,
        related_name='articles',
        help_text="Catégorie de l'article (pouvant être hiérarchique). Ex : Vêtements > Femme > Robes."
    )

    collection = models.ForeignKey(
        'Collection',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='articles',
        help_text="Collection saisonnière. Null si article permanent au catalogue."
    )

    fournisseur = models.ForeignKey(
        'founisseurs.Fournisseur',   # FK cross-app via string pour éviter les imports circulaires
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='articles',
        help_text="Fournisseur principal de cet article pour les réapprovisionnements."
    )

    # --- Prix ---
    prix_achat_ht = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text=(
            "Prix d'achat hors taxes auprès du fournisseur. "
            "CONFIDENTIEL — ne jamais transmettre au frontend client."
        )
    )

    prix_vente_ttc = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text=(
            "Prix de vente public TTC. "
            "Peut être surchargé au niveau de la déclinaison (prix_vente_specifique)."
        )
    )

    taux_tva = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=18.00,
        help_text="Taux de TVA applicable en %. Ex : 18.00. Dépend de la réglementation locale."
    )

    # --- Classification ---
    genre = models.CharField(
        max_length=20,
        choices=GENRE_CHOICES,
        default='mixte',
        help_text="Genre cible. Utilisé pour le filtrage dans le catalogue."
    )

    # --- Statut ---
    actif = models.BooleanField(
        default=True,
        help_text=(
            "Si False, l'article n'apparaît plus dans le catalogue ni en caisse (soft delete). "
            "L'historique des ventes est conservé."
        )
    )

    # --- Médias ---
    photo = models.ImageField(
        upload_to='articles/photos/',
        null=True,
        blank=True,
        help_text="Photo principale. URL servie par l'API REST et affichée par Next.js."
    )

    magasin = models.ForeignKey(
        'administration.Magasin',
        on_delete=models.PROTECT,
        related_name='articles',
        help_text="Magasin auquel appartient cet article. Permet l'isolation multi-boutiques."
    )

    date_ajout = models.DateTimeField(
        auto_now_add=True,
        help_text="Date d'ajout au catalogue, générée automatiquement."
    )

    class Meta:
        verbose_name = "Article"
        verbose_name_plural = "Articles"
        ordering = ['designation']
        indexes = [
            models.Index(fields=['reference']),
            models.Index(fields=['magasin', 'actif']),
        ]

    def __str__(self):
        return f"[{self.reference}] {self.designation}"

    @property
    def marge_brute(self):
        """
        Calcule la marge brute en FCFA = prix_vente_ttc - prix_achat_ht.
        Propriété non stockée, calculée à la volée.
        """
        return self.prix_vente_ttc - self.prix_achat_ht


# =============================================================================
# DECLINAISON
# =============================================================================

class Declinaison(models.Model):
   

    article = models.ForeignKey(
        'Article',
        on_delete=models.CASCADE,
        related_name='declinaisons',
        help_text=(
            "Article parent. related_name='declinaisons' permet "
            "article.declinaisons.all() pour récupérer toutes les variantes."
        )
    )

    taille = models.CharField(
        max_length=20,
        help_text=(
            "Taille textuelle : XS, S, M, L, XL, XXL, ou numérique pour chaussures (38, 39...). "
            "Libre pour s'adapter à tous les secteurs."
        )
    )

    coloris = models.CharField(
        max_length=100,
        help_text="Nom de la couleur. Ex : 'Noir', 'Blanc', 'Bleu marine'. Affiché dans la grille."
    )

    code_barres = models.CharField(
        max_length=50,
        unique=True,
        help_text=(
            "Code EAN13 scannable par le lecteur de caisse. "
            "Généré automatiquement dans save() si laissé vide, "
            "ou saisi manuellement si l'article vient avec son propre code-barres fournisseur."
        )
    )

    # --- Stock ---
    stock_actuel = models.IntegerField(
        default=0,
        help_text=(
            "Quantité physiquement disponible en boutique. "
            "Décrémenté à chaque vente validée, incrémenté à chaque réception fournisseur. "
            "NE JAMAIS modifier directement — passer par un MouvementStock."
        )
    )

    stock_minimum = models.IntegerField(
        default=0,
        help_text=(
            "Seuil d'alerte de réapprovisionnement. "
            "Si stock_actuel <= stock_minimum, une alerte est générée."
        )
    )

    stock_maximum = models.IntegerField(
        null=True,
        blank=True,
        help_text=(
            "Stock cible maximal. "
            "Permet de calculer la quantité optimale à commander : stock_maximum - stock_actuel."
        )
    )

    # --- Prix spécifique (optionnel) ---
    prix_vente_specifique = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=(
            "Prix spécifique pour cette déclinaison, remplaçant le prix de l'article parent. "
            "Null = utiliser article.prix_vente_ttc."
        )
    )

    actif = models.BooleanField(
        default=True,
        help_text=(
            "Déclinaison désactivée = ne peut plus être vendue. "
            "Permet de retirer une taille épuisée définitivement sans supprimer l'historique."
        )
    )

    class Meta:
        verbose_name = "Déclinaison"
        verbose_name_plural = "Déclinaisons"
        ordering = ['article', 'taille', 'coloris']
        # Une même combinaison article+taille+coloris doit être unique
        constraints = [
            models.UniqueConstraint(
                fields=['article', 'taille', 'coloris'],
                name='unique_declinaison_article_taille_coloris'
            )
        ]
        indexes = [
            models.Index(fields=['code_barres']),
            models.Index(fields=['article', 'actif']),
        ]

    def __str__(self):
        return f"{self.article.designation} / {self.taille} / {self.coloris}"

    @property
    def prix_effectif(self):
        """Retourne le prix réel de vente : spécifique si défini, sinon celui de l'article parent."""
        return self.prix_vente_specifique if self.prix_vente_specifique else self.article.prix_vente_ttc

    @property
    def en_alerte_stock(self):
        """True si le stock est au niveau ou en dessous du seuil minimum."""
        return self.stock_actuel <= self.stock_minimum

    def save(self, *args, **kwargs):
        """Génère un code-barres unique si non fourni."""
        if not self.code_barres:
            # En première passe, on sauvegarde pour obtenir l'ID si nécessaire.
            super().save(*args, **kwargs)
            if not self.code_barres:
                self.code_barres = str(self.id).replace('-', '')[:13].upper()
                super().save(update_fields=['code_barres'])
            return
        super().save(*args, **kwargs)


# =============================================================================
# MOUVEMENT STOCK
# =============================================================================

class MouvementStock(models.Model):
   
    TYPE_CHOICES = [
        ('entree',             'Entrée (réception fournisseur)'),
        ('sortie',             'Sortie (vente)'),
        ('ajustement_positif', 'Ajustement positif (inventaire)'),
        ('ajustement_negatif', 'Ajustement négatif (casse/vol)'),
        ('retour_client',      'Retour client remis en stock'),
    ]


    declinaison = models.ForeignKey(
        'Declinaison',
        on_delete=models.PROTECT,
        related_name='mouvements_stock',
        help_text="Déclinaison concernée par ce mouvement de stock."
    )

    type = models.CharField(
        max_length=30,
        choices=TYPE_CHOICES,
        help_text="Nature du mouvement. La quantite est toujours positive ; le type indique le sens."
    )

    quantite = models.PositiveIntegerField(
        help_text="Nombre d'unités déplacées. Toujours positif."
    )

    quantite_avant = models.IntegerField(
        help_text=(
            "Stock AVANT le mouvement. Capturé automatiquement "
            "pour permettre l'audit et la reconstruction de l'historique."
        )
    )

    quantite_apres = models.IntegerField(
        help_text=(
            "Stock APRÈS le mouvement. "
            "= quantite_avant + quantite (entrée/ajustement_positif/retour_client) "
            "ou quantite_avant - quantite (sortie/ajustement_negatif)."
        )
    )

    motif = models.CharField(
        max_length=255,
        blank=True,
        help_text=(
            "Raison de l'ajustement manuel : 'casse', 'vol', 'erreur d'inventaire'. "
            "Vide pour les mouvements automatiques (vente, réception)."
        )
    )

    date_heure = models.DateTimeField(
        auto_now_add=True,
        help_text="Horodatage côté serveur. Indispensable pour reconstituer l'historique dans l'ordre."
    )

    utilisateur = models.ForeignKey(
        'administration.Utilisateur',
        on_delete=models.SET_NULL,
        null=True,
        related_name='mouvements_stock',
        help_text=(
            "Utilisateur à l'origine du mouvement. "
            "Pour les mouvements automatiques (vente), c'est le vendeur."
        )
    )

    # Référence optionnelle vers l'objet source du mouvement
    # (vente_id, commande_id, inventaire_id) stockée en JSON pour flexibilité
    source = models.JSONField(
        null=True,
        blank=True,
        help_text=(
            "Référence vers l'objet à l'origine du mouvement. "
            "Ex : {'type': 'vente', 'id': 'uuid-de-la-vente'}. "
            "Permet de retrouver la vente ou la commande liée à ce mouvement."
        )
    )

    class Meta:
        verbose_name = "Mouvement de stock"
        verbose_name_plural = "Mouvements de stock"
        ordering = ['-date_heure']
        indexes = [
            models.Index(fields=['declinaison', 'date_heure']),
            models.Index(fields=['type', 'date_heure']),
        ]

    def __str__(self):
        return f"{self.get_type_display()} | {self.declinaison} | qté {self.quantite} | {self.date_heure:%d/%m/%Y %H:%M}"


# =============================================================================
# INVENTAIRE
# =============================================================================

class Inventaire(models.Model):
   
    TYPE_CHOICES = [
        ('complet', 'Complet (tout le stock)'),
        ('partiel', 'Partiel (sélection de rayons ou catégories)'),
    ]

    STATUT_CHOICES = [
        ('en_cours', 'En cours'),
        ('valide',   'Validé'),
        ('annule',   'Annulé'),
    ]

    date_inventaire = models.DateTimeField(
        help_text="Date et heure de réalisation de l'inventaire."
    )

    type = models.CharField(
        max_length=20,
        choices=TYPE_CHOICES,
        help_text="Portée de l'inventaire : complet ou partiel."
    )

    statut = models.CharField(
        max_length=20,
        choices=STATUT_CHOICES,
        default='en_cours',
        help_text=(
            "État de l'inventaire. "
            "Un seul inventaire 'en_cours' autorisé par magasin à la fois."
        )
    )

    magasin = models.ForeignKey(
        'administration.Magasin',
        on_delete=models.PROTECT,
        related_name='inventaires',
        help_text="Magasin concerné par l'inventaire."
    )

    utilisateur = models.ForeignKey(
        'administration.Utilisateur',
        on_delete=models.PROTECT,
        related_name='inventaires',
        help_text="Responsable de l'inventaire (gestionnaire ou gérant)."
    )

    observation = models.TextField(
        blank=True,
        help_text=(
            "Notes libres sur les conditions de l'inventaire : "
            "zone concernée, anomalies constatées, conditions particulières."
        )
    )

    class Meta:
        verbose_name = "Inventaire"
        verbose_name_plural = "Inventaires"
        ordering = ['-date_inventaire']

    def __str__(self):
        return f"Inventaire {self.get_type_display()} — {self.date_inventaire:%d/%m/%Y} — {self.get_statut_display()}"


# =============================================================================
# LIGNE INVENTAIRE
# =============================================================================

class LigneInventaire(models.Model):
   

    inventaire = models.ForeignKey(
        'Inventaire',
        on_delete=models.CASCADE,
        related_name='lignes',
        help_text="Inventaire auquel appartient cette ligne. CASCADE : supprimé avec l'inventaire."
    )

    declinaison = models.ForeignKey(
        'Declinaison',
        on_delete=models.PROTECT,
        related_name='lignes_inventaire',
        help_text="Déclinaison comptée."
    )

    quantite_theorique = models.IntegerField(
        help_text="Stock enregistré en base au moment du début de l'inventaire."
    )

    quantite_comptee = models.IntegerField(
        help_text="Quantité physiquement comptée sur le terrain par le responsable."
    )

    class Meta:
        verbose_name = "Ligne d'inventaire"
        verbose_name_plural = "Lignes d'inventaire"
        constraints = [
            models.UniqueConstraint(
                fields=['inventaire', 'declinaison'],
                name='unique_ligne_inventaire_declinaison'
            )
        ]

    def __str__(self):
        return f"{self.declinaison} | théorique={self.quantite_theorique} | compté={self.quantite_comptee}"

    @property
    def ecart(self):
        """Écart = compté - théorique. Positif = surplus, négatif = manquant."""
        return self.quantite_comptee - self.quantite_theorique