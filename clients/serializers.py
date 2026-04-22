"""
=============================================================================
SERIALIZERS — APP : clients
=============================================================================
"""

from rest_framework import serializers
from clients.models import Client, Avoir


# =============================================================================
# CLIENT
# =============================================================================

class ClientSerializer(serializers.ModelSerializer):
    """
    Serializer complet du client.
    Utilisé pour la fiche client et la recherche en caisse.
    """

    nom_complet = serializers.CharField(read_only=True)
    avoirs_actifs = serializers.SerializerMethodField()

    class Meta:
        model = Client
        fields = [
            'id', 'nom', 'prenom', 'nom_complet',
            'telephone', 'email', 'adresse',
            'date_naissance', 'genre', 'date_inscription',
            'points_fidelite', 'niveau_fidelite',
            'numero_carte_fidelite', 'actif', 'notes',
            'magasin', 'avoirs_actifs',
        ]
        read_only_fields = [
            'id', 'nom_complet', 'date_inscription',
            'points_fidelite', 'niveau_fidelite',
            'avoirs_actifs',
        ]

    def get_avoirs_actifs(self, obj):
        """Retourne le total des avoirs utilisables pour ce client."""
        avoirs = obj.avoirs.filter(statut='actif')
        total = sum(a.solde for a in avoirs)
        return {
            'nombre': avoirs.count(),
            'total_disponible': float(total),
        }

    def validate_telephone(self, valeur):
        if valeur:
            qs = Client.objects.filter(telephone=valeur)
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError(
                    "Ce numéro de téléphone est déjà utilisé par un autre client."
                )
        return valeur

    def validate_email(self, valeur):
        if valeur:
            qs = Client.objects.filter(email=valeur)
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError(
                    "Cet email est déjà utilisé par un autre client."
                )
        return valeur


class ClientResumeSerializer(serializers.ModelSerializer):
    """
    Version allégée pour l'affichage en caisse lors de la recherche rapide.
    Retourne uniquement les infos nécessaires pour identifier le client.
    """

    class Meta:
        model = Client
        fields = [
            'id', 'nom', 'prenom',
            'telephone', 'numero_carte_fidelite',
            'points_fidelite', 'niveau_fidelite',
        ]
        read_only_fields = fields


class RechercheClientSerializer(serializers.Serializer):
    """
    Serializer pour la recherche rapide d'un client en caisse.
    Le terme de recherche est comparé au téléphone, email et numéro de carte.
    """

    terme = serializers.CharField(
        min_length=3,
        help_text=(
            "Terme de recherche : numéro de téléphone, email, "
            "ou numéro de carte de fidélité."
        )
    )


# =============================================================================
# AVOIR
# =============================================================================

class AvoirSerializer(serializers.ModelSerializer):
    """
    Sérialise un avoir client avec son solde calculé.
    """

    solde = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        read_only=True,
        help_text="Solde restant = montant - montant_utilise."
    )

    client_nom = serializers.SerializerMethodField()

    class Meta:
        model = Avoir
        fields = [
            'id', 'client', 'client_nom', 'numero',
            'montant', 'montant_utilise', 'solde',
            'date_expiration', 'statut', 'date_creation',
        ]
        read_only_fields = [
            'id', 'numero', 'montant_utilise',
            'solde', 'statut', 'date_creation', 'client_nom',
        ]

    def get_client_nom(self, obj):
        return str(obj.client)

    def validate_montant(self, valeur):
        if valeur <= 0:
            raise serializers.ValidationError(
                "Le montant de l'avoir doit être supérieur à 0."
            )
        return valeur


class AvoirResumeSerializer(serializers.ModelSerializer):
    """
    Version allégée pour le sélecteur de mode de paiement en caisse.
    """

    solde = serializers.DecimalField(
        max_digits=12, decimal_places=2, read_only=True
    )

    class Meta:
        model = Avoir
        fields = ['id', 'numero', 'solde', 'date_expiration', 'statut']
        read_only_fields = fields


# =============================================================================
# =============================================================================
# SERIALIZERS — APP : fournisseurs
# =============================================================================
# =============================================================================

from founisseurs.models import Fournisseur, CommandeFournisseur, LigneCommande


# =============================================================================
# FOURNISSEUR
# =============================================================================

class FournisseurSerializer(serializers.ModelSerializer):

    class Meta:
        model = Fournisseur
        fields = [
            'id', 'raison_sociale', 'contact',
            'telephone', 'email', 'adresse', 'pays',
            'delai_livraison', 'conditions_paiement',
            'actif', 'notes', 'magasin',
        ]
        read_only_fields = ['id']


class FournisseurResumeSerializer(serializers.ModelSerializer):
    """Version allégée pour les listes déroulantes."""

    class Meta:
        model = Fournisseur
        fields = ['id', 'raison_sociale', 'telephone', 'delai_livraison']
        read_only_fields = fields


# =============================================================================
# LIGNE COMMANDE
# =============================================================================

class LigneCommandeSerializer(serializers.ModelSerializer):
    """
    Sérialise une ligne de bon de commande fournisseur.
    Chaque ligne représente un article dans une taille et un coloris précis.
    """

    quantite_restante = serializers.IntegerField(read_only=True)
    est_soldee = serializers.BooleanField(read_only=True)

    # Infos lisibles de la déclinaison pour l'affichage du reçu
    declinaison_info = serializers.SerializerMethodField()

    class Meta:
        model = LigneCommande
        fields = [
            'id', 'commande', 'declinaison', 'declinaison_info',
            'quantite_commandee', 'quantite_recue',
            'prix_achat_unitaire', 'total_ligne',
            'quantite_restante', 'est_soldee',
        ]
        read_only_fields = [
            'id', 'total_ligne',
            'quantite_restante', 'est_soldee',
            'declinaison_info',
        ]

    def get_declinaison_info(self, obj):
        d = obj.declinaison
        return {
            'reference': d.article.reference,
            'designation': d.article.designation,
            'taille': d.taille,
            'coloris': d.coloris,
            'code_barres': d.code_barres,
        }

    def validate(self, data):
        """
        Vérifie que la quantité reçue ne dépasse pas la quantité commandée.
        """
        qte_commandee = data.get(
            'quantite_commandee',
            self.instance.quantite_commandee if self.instance else 0
        )
        qte_recue = data.get(
            'quantite_recue',
            self.instance.quantite_recue if self.instance else 0
        )
        if qte_recue > qte_commandee:
            raise serializers.ValidationError(
                {
                    'quantite_recue': (
                        f"La quantité reçue ({qte_recue}) ne peut pas dépasser "
                        f"la quantité commandée ({qte_commandee})."
                    )
                }
            )
        return data


class LigneCommandeCreationSerializer(serializers.ModelSerializer):
    """
    Serializer simplifié pour la création des lignes lors de la création
    d'un bon de commande (création imbriquée dans CommandeFournisseurSerializer).
    """

    class Meta:
        model = LigneCommande
        fields = [
            'declinaison', 'quantite_commandee', 'prix_achat_unitaire'
        ]

    def validate_quantite_commandee(self, valeur):
        if valeur <= 0:
            raise serializers.ValidationError(
                "La quantité commandée doit être supérieure à 0."
            )
        return valeur


# =============================================================================
# COMMANDE FOURNISSEUR
# =============================================================================

class CommandeFournisseurSerializer(serializers.ModelSerializer):
    """
    Serializer complet d'une commande fournisseur avec ses lignes.

    Utilisé pour :
      - Afficher le détail d'une commande
      - Générer le reçu/bon de commande PDF (toutes les lignes sont incluses)

    La création d'une commande avec ses lignes se fait en une seule requête
    grâce à la création imbriquée (lignes dans le body de la requête).
    """

    lignes = LigneCommandeSerializer(many=True, read_only=True)
    fournisseur_info = FournisseurResumeSerializer(
        source='fournisseur', read_only=True
    )
    statut_display = serializers.CharField(
        source='get_statut_display', read_only=True
    )
    nombre_articles = serializers.SerializerMethodField()

    class Meta:
        model = CommandeFournisseur
        fields = [
            'id', 'numero', 'fournisseur', 'fournisseur_info',
            'date_commande', 'date_livraison_prevue',
            'date_livraison_effective', 'statut', 'statut_display',
            'total_ht', 'utilisateur', 'notes', 'magasin',
            'lignes', 'nombre_articles',
        ]
        read_only_fields = [
            'id', 'numero', 'date_commande',
            'total_ht', 'statut', 'statut_display',
            'fournisseur_info', 'lignes', 'nombre_articles',
        ]

    def get_nombre_articles(self, obj):
        """Retourne le nombre total d'unités commandées."""
        return sum(
            ligne.quantite_commandee for ligne in obj.lignes.all()
        )


class CommandeFournisseurCreationSerializer(serializers.ModelSerializer):
    """
    Serializer de CRÉATION d'une commande fournisseur avec ses lignes en une seule fois.

    Format de la requête :
    {
        "fournisseur": "uuid-fournisseur",
        "magasin": "uuid-magasin",
        "notes": "...",
        "lignes": [
            {"declinaison": "uuid-dec1", "quantite_commandee": 10, "prix_achat_unitaire": 3000},
            {"declinaison": "uuid-dec2", "quantite_commandee": 5,  "prix_achat_unitaire": 5000}
        ]
    }
    """

    lignes = LigneCommandeCreationSerializer(
        many=True,
        help_text="Liste des articles à commander avec leurs quantités et prix."
    )

    class Meta:
        model = CommandeFournisseur
        fields = [
            'fournisseur', 'date_livraison_prevue',
            'notes', 'magasin', 'lignes',
        ]

    def validate_lignes(self, valeur):
        if not valeur:
            raise serializers.ValidationError(
                "Une commande doit contenir au moins une ligne d'article."
            )
        # Vérifier les doublons de déclinaison dans les lignes
        declinaisons = [l['declinaison'] for l in valeur]
        if len(declinaisons) != len(set(d.id for d in declinaisons)):
            raise serializers.ValidationError(
                "Une même déclinaison ne peut apparaître qu'une fois par commande."
            )
        return valeur

    def create(self, validated_data):
        """Crée la commande et toutes ses lignes en une transaction atomique."""
        from django.db import transaction
        from django.utils import timezone
        import datetime

        lignes_data = validated_data.pop('lignes')

        with transaction.atomic():
            # Générer le numéro de commande
            annee = timezone.now().year
            dernier = CommandeFournisseur.objects.filter(
                numero__startswith=f'BC-{annee}-'
            ).count()
            numero = f"BC-{annee}-{str(dernier + 1).zfill(4)}"

            # Calculer la date de livraison prévue si non fournie
            if not validated_data.get('date_livraison_prevue'):
                fournisseur = validated_data['fournisseur']
                validated_data['date_livraison_prevue'] = (
                    timezone.now().date() +
                    datetime.timedelta(days=fournisseur.delai_livraison)
                )

            commande = CommandeFournisseur.objects.create(
                numero=numero,
                utilisateur=self.context['request'].utilisateur,
                **validated_data
            )

            # Créer les lignes
            for ligne_data in lignes_data:
                LigneCommande.objects.create(commande=commande, **ligne_data)

            # Recalculer le total
            commande.recalculer_total()

        return commande


class ReceptionLigneSerializer(serializers.Serializer):
    """
    Serializer pour enregistrer une réception partielle ou totale
    d'une ligne de commande fournisseur.
    Génère automatiquement un MouvementStock d'entrée.
    """

    ligne_id = serializers.PrimaryKeyRelatedField(
        queryset=LigneCommande.objects.all(),
        source='ligne',
        help_text="ID de la ligne de commande reçue."
    )

    quantite_recue = serializers.IntegerField(
        min_value=1,
        help_text="Quantité effectivement reçue pour cette ligne."
    )

    def validate(self, data):
        ligne = data['ligne']
        nouvelle_qte = ligne.quantite_recue + data['quantite_recue']
        if nouvelle_qte > ligne.quantite_commandee:
            raise serializers.ValidationError(
                {
                    'quantite_recue': (
                        f"La réception totale ({nouvelle_qte}) dépasserait "
                        f"la quantité commandée ({ligne.quantite_commandee})."
                    )
                }
            )
        return data


# =============================================================================
# =============================================================================
# SERIALIZERS — APP : promotions
# =============================================================================
# =============================================================================

from promotions.models import Promotion
from django.utils import timezone


class PromotionSerializer(serializers.ModelSerializer):
    """
    Serializer complet d'une promotion.
    Inclut la vérification de validité temporelle et des usages.
    """

    est_active_maintenant = serializers.SerializerMethodField(
        help_text="True si la promotion est active à cet instant précis."
    )

    usages_restants = serializers.SerializerMethodField(
        help_text="Nombre d'utilisations restantes. Null si illimité."
    )

    type_display = serializers.CharField(
        source='get_type_display', read_only=True
    )

    portee_display = serializers.CharField(
        source='get_portee_display', read_only=True
    )

    class Meta:
        model = Promotion
        fields = [
            'id', 'nom', 'description',
            'type', 'type_display', 'valeur',
            'portee', 'portee_display',
            'article_cible', 'categorie_cible',
            'date_debut', 'date_fin',
            'montant_min_panier',
            'usages_max', 'usages_actuels', 'usages_restants',
            'actif', 'magasin',
            'est_active_maintenant',
        ]
        read_only_fields = [
            'id', 'usages_actuels',
            'est_active_maintenant', 'usages_restants',
            'type_display', 'portee_display',
        ]

    def get_est_active_maintenant(self, obj):
        """Vérifie si la promotion est applicable à l'instant présent."""
        maintenant = timezone.now()
        if not obj.actif:
            return False
        if maintenant < obj.date_debut:
            return False
        if obj.date_fin and maintenant > obj.date_fin:
            return False
        if obj.usages_max and obj.usages_actuels >= obj.usages_max:
            return False
        return True

    def get_usages_restants(self, obj):
        if obj.usages_max is None:
            return None
        return max(0, obj.usages_max - obj.usages_actuels)

    def validate(self, data):
        date_debut = data.get('date_debut')
        date_fin = data.get('date_fin')
        if date_debut and date_fin and date_fin <= date_debut:
            raise serializers.ValidationError(
                {'date_fin': "La date de fin doit être postérieure à la date de début."}
            )

        # Vérifier la cohérence portée / cible
        portee = data.get('portee')
        article_cible = data.get('article_cible')
        categorie_cible = data.get('categorie_cible')

        if portee == 'article' and not article_cible:
            raise serializers.ValidationError(
                {'article_cible': "Un article cible est requis pour une promotion de portée 'article'."}
            )

        if portee == 'categorie' and not categorie_cible:
            raise serializers.ValidationError(
                {'categorie_cible': "Une catégorie cible est requise pour une promotion de portée 'categorie'."}
            )

        # Vérifier la valeur selon le type
        valeur = data.get('valeur', 0)
        type_promo = data.get('type')
        if type_promo == 'pourcentage' and not (0 < valeur <= 100):
            raise serializers.ValidationError(
                {'valeur': "Pour un pourcentage, la valeur doit être entre 0 et 100."}
            )

        return data


class PromotionResumeSerializer(serializers.ModelSerializer):
    """
    Version allégée pour l'affichage des badges remise sur les articles en POS.
    """

    class Meta:
        model = Promotion
        fields = ['id', 'nom', 'type', 'valeur', 'portee']
        read_only_fields = fields