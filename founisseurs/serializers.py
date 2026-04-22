"""
=============================================================================
SERIALIZERS — APP : fournisseurs
=============================================================================
Couvre :
  - FournisseurSerializer
  - LigneCommandeSerializer
  - LigneCommandeCreateSerializer
  - CommandeFournisseurSerializer (lecture)
  - CommandeFournisseurCreateSerializer (création avec lignes)

Règles :
  - total_ht et total_ligne sont calculés automatiquement
  - quantite_restante et est_soldee sont en lecture seule
  - nested serializers pour les relations
=============================================================================
"""

from rest_framework import serializers
from .models import Fournisseur, CommandeFournisseur, LigneCommande


# =============================================================================
# FOURNISSEUR
# =============================================================================

class FournisseurSerializer(serializers.ModelSerializer):
    """
    Sérialisation complète d’un fournisseur.
    """

    class Meta:
        model = Fournisseur
        fields = [
            'id',
            'raison_sociale',
            'contact',
            'telephone',
            'email',
            'adresse',
            'pays',
            'delai_livraison',
            'conditions_paiement',
            'actif',
            'notes',
            'magasin',
        ]
        read_only_fields = ['id']


# =============================================================================
# LIGNE COMMANDE (LECTURE)
# =============================================================================

class LigneCommandeSerializer(serializers.ModelSerializer):
    """
    Lecture des lignes de commande avec champs calculés.
    """

    quantite_restante = serializers.ReadOnlyField()
    est_soldee = serializers.ReadOnlyField()

    class Meta:
        model = LigneCommande
        fields = [
            'id',
            'commande',
            'declinaison',
            'quantite_commandee',
            'quantite_recue',
            'prix_achat_unitaire',
            'total_ligne',
            'quantite_restante',
            'est_soldee',
        ]
        read_only_fields = ['id', 'total_ligne']


# =============================================================================
# LIGNE COMMANDE (CRÉATION)
# =============================================================================

class LigneCommandeCreateSerializer(serializers.ModelSerializer):
    """
    Création simple d’une ligne de commande.
    """

    class Meta:
        model = LigneCommande
        fields = [
            'declinaison',
            'quantite_commandee',
            'prix_achat_unitaire',
        ]


# =============================================================================
# COMMANDE FOURNISSEUR (LECTURE)
# =============================================================================

class CommandeFournisseurSerializer(serializers.ModelSerializer):
    """
    Lecture des commandes fournisseurs avec lignes imbriquées.
    """

    fournisseur = FournisseurSerializer(read_only=True)
    lignes = LigneCommandeSerializer(many=True, read_only=True)

    class Meta:
        model = CommandeFournisseur
        fields = [
            'id',
            'numero',
            'fournisseur',
            'date_commande',
            'date_livraison_prevue',
            'date_livraison_effective',
            'statut',
            'total_ht',
            'utilisateur',
            'notes',
            'magasin',
            'lignes',
        ]
        read_only_fields = ['id', 'total_ht']


# =============================================================================
# COMMANDE FOURNISSEUR (CRÉATION)
# =============================================================================

class CommandeFournisseurCreateSerializer(serializers.ModelSerializer):
    """
    Création d'une commande fournisseur avec ses lignes.
    """

    lignes = LigneCommandeCreateSerializer(many=True)

    class Meta:
        model = CommandeFournisseur
        fields = [
            'numero',
            'fournisseur',
            'utilisateur',
            'magasin',
            'notes',
            'lignes',
        ]

    def create(self, validated_data):
        lignes_data = validated_data.pop('lignes')

        commande = CommandeFournisseur.objects.create(**validated_data)

        for ligne in lignes_data:
            LigneCommande.objects.create(commande=commande, **ligne)

        return commande