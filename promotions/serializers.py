"""
=============================================================================
SERIALIZERS — APP : promotions
=============================================================================
"""

from rest_framework import serializers
from .models import Promotion


class PromotionSerializer(serializers.ModelSerializer):
    """
    Serializer principal pour lecture et écriture des promotions.
    """

    type_display = serializers.CharField(source='get_type_display', read_only=True)
    portee_display = serializers.CharField(source='get_portee_display', read_only=True)

    class Meta:
        model = Promotion
        fields = [
            'id',
            'nom',
            'description',
            'type',
            'type_display',
            'valeur',
            'portee',
            'portee_display',
            'article_cible',
            'categorie_cible',
            'date_debut',
            'date_fin',
            'montant_min_panier',
            'usages_max',
            'usages_actuels',
            'actif',
            'magasin',
        ]

        read_only_fields = ['id', 'usages_actuels']

    # =========================================================
    # VALIDATION MÉTIER
    # =========================================================
    def validate(self, data):
        portee = data.get('portee')

        # 🔥 cohérence article
        if portee == 'article' and not data.get('article_cible'):
            raise serializers.ValidationError(
                "Une promotion sur article doit avoir un article_cible."
            )

        # 🔥 cohérence catégorie
        if portee == 'categorie' and not data.get('categorie_cible'):
            raise serializers.ValidationError(
                "Une promotion sur catégorie doit avoir une categorie_cible."
            )

        # 🔥 incohérence panier
        if portee == 'panier' and data.get('article_cible'):
            raise serializers.ValidationError(
                "Une promotion panier ne doit pas cibler un article."
            )

        # 🔥 validation dates
        if data.get('date_fin') and data.get('date_debut'):
            if data['date_fin'] < data['date_debut']:
                raise serializers.ValidationError(
                    "La date de fin doit être après la date de début."
                )

        return data


class PromotionCreateSerializer(serializers.ModelSerializer):
    """
    Serializer dédié à la création (optionnel).
    """

    class Meta:
        model = Promotion
        fields = [
            'nom',
            'description',
            'type',
            'valeur',
            'portee',
            'article_cible',
            'categorie_cible',
            'date_debut',
            'date_fin',
            'montant_min_panier',
            'usages_max',
            'actif',
            'magasin',
        ]