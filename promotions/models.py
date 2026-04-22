from django.db import models

# Create your models here.
"""
APP : promotions
"""

from django.db import models

class Promotion(models.Model):
   
    TYPE_CHOICES = [
        ('pourcentage',  'Pourcentage (ex. -20%)'),
        ('valeur_fixe',  'Valeur fixe (ex. -5 000 FCFA)'),
        ('offre_panier', 'Offre panier (ex. 2 achetés = 1 offert)'),
    ]

    PORTEE_CHOICES = [
        ('article',    'Article spécifique'),
        ('categorie',  'Catégorie entière'),
        ('panier',     'Panier global'),
        ('client',     'Segment client spécifique'),
    ]

    nom = models.CharField(
        max_length=150,
        help_text="Nom interne de la promotion. Ex : 'Soldes été 2026 -30%'."
    )

    description = models.TextField(
        blank=True,
        help_text="Description affichée au client en boutique ou sur le ticket."
    )

    type = models.CharField(
        max_length=20,
        choices=TYPE_CHOICES,
        help_text="Nature de la remise."
    )

    valeur = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text=(
            "Valeur de la remise : "
            "20.00 pour 20% (si type=pourcentage), "
            "ou 5000.00 FCFA (si type=valeur_fixe)."
        )
    )

    portee = models.CharField(
        max_length=20,
        choices=PORTEE_CHOICES,
        help_text="Sur quoi s'applique la promotion."
    )

    # Cibles optionnelles selon la portée
    article_cible = models.ForeignKey(
        'catalogue.Article',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='promotions',
        help_text="Article ciblé si portee='article'. Null sinon."
    )

    categorie_cible = models.ForeignKey(
        'catalogue.Categorie',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='promotions',
        help_text="Catégorie ciblée si portee='categorie'. Null sinon."
    )

    # Conditions d'application
    date_debut = models.DateTimeField(
        help_text="Début de validité. La promotion est inactive avant cette date."
    )

    date_fin = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Fin de validité. Null = promotion permanente sans date de fin."
    )

    montant_min_panier = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Panier minimum requis pour déclencher la promotion. Null = pas de minimum."
    )

    usages_max = models.IntegerField(
        null=True,
        blank=True,
        help_text="Nombre maximum total d'utilisations. Null = illimité."
    )

    usages_actuels = models.IntegerField(
        default=0,
        help_text=(
            "Compteur d'utilisations. "
            "Incrémenté atomiquement via F() expression pour éviter les race conditions."
        )
    )

    actif = models.BooleanField(
        default=True,
        help_text="Activation manuelle. Permet de préparer des promotions à l'avance."
    )

    magasin = models.ForeignKey(
        'administration.Magasin',
        on_delete=models.PROTECT,
        related_name='promotions',
        help_text="Magasin pour lequel cette promotion est valable."
    )

    class Meta:
        verbose_name = "Promotion"
        verbose_name_plural = "Promotions"
        ordering = ['-date_debut']
        indexes = [
            models.Index(fields=['magasin', 'actif', 'date_debut', 'date_fin']),
        ]

    def __str__(self):
        return f"{self.nom} ({self.get_type_display()} {self.valeur})"

