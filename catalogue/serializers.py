"""
=============================================================================
SERIALIZERS — APP : catalogue
=============================================================================
Couvre :
  - CategorieSerializer
  - MarqueSerializer
  - CollectionSerializer
  - ArticleSerializer      (lecture complète, création, mise à jour)
  - DeclinaisonSerializer  (avec stock et alertes)
  - MouvementStockSerializer
  - InventaireSerializer
  - LigneInventaireSerializer

Règles appliquées :
  - prix_achat_ht est CONFIDENTIEL → write_only ou exclu selon le contexte.
  - Les champs calculés (marge_brute, prix_effectif, en_alerte_stock)
    sont en read_only via SerializerMethodField.
  - Le code_barres est généré automatiquement si absent (dans le model.save()).
=============================================================================
"""

import base64
import io
import json

import qrcode
from rest_framework import serializers
from catalogue.models import (
    Categorie, Marque, Collection, Article,
    Declinaison, MouvementStock, Inventaire, LigneInventaire
)


def generer_qr_code_data_url(valeur):
    """Génère un QR code PNG encodé en data URL à partir d'une valeur texte."""
    if not valeur:
        return None
    qr = qrcode.QRCode(box_size=10, border=4)
    qr.add_data(str(valeur))
    qr.make(fit=True)
    image = qr.make_image(fill_color='black', back_color='white')
    buffer = io.BytesIO()
    image.save(buffer, format='PNG')
    encoded = base64.b64encode(buffer.getvalue()).decode('utf-8')
    return f'data:image/png;base64,{encoded}'


# =============================================================================
# CATEGORIE
# =============================================================================

class CategorieSerializer(serializers.ModelSerializer):
    """
    Sérialise une catégorie avec sa hiérarchie parent.
    Le champ 'chemin' affiche la hiérarchie complète pour le breadcrumb Next.js.
    """

    chemin = serializers.SerializerMethodField(
        help_text="Chemin hiérarchique complet. Ex : 'Vêtements > Femme > Robes'."
    )

    class Meta:
        model = Categorie
        fields = [
            'id', 'libelle', 'description',
            'categorie_parent', 'ordre', 'chemin',
        ]
        read_only_fields = ['id', 'chemin']

    def get_chemin(self, obj):
        """Construit le chemin hiérarchique complet de la catégorie."""
        chemin = [obj.libelle]
        parent = obj.categorie_parent
        while parent:
            chemin.insert(0, parent.libelle)
            parent = parent.categorie_parent
        return ' > '.join(chemin)


class CategorieResumeSerializer(serializers.ModelSerializer):
    """Version allégée pour les listes déroulantes dans les formulaires."""

    class Meta:
        model = Categorie
        fields = ['id', 'libelle']
        read_only_fields = ['id', 'libelle']


# =============================================================================
# MARQUE
# =============================================================================

class MarqueSerializer(serializers.ModelSerializer):

    class Meta:
        model = Marque
        fields = ['id', 'nom', 'logo', 'description']
        read_only_fields = ['id']


class MarqueResumeSerializer(serializers.ModelSerializer):

    class Meta:
        model = Marque
        fields = ['id', 'nom']
        read_only_fields = ['id', 'nom']


# =============================================================================
# COLLECTION
# =============================================================================

class CollectionSerializer(serializers.ModelSerializer):

    class Meta:
        model = Collection
        fields = [
            'id', 'nom', 'saison', 'annee',
            'date_debut', 'date_fin',
        ]
        read_only_fields = ['id']

    def validate(self, data):
        """Vérifie que date_fin est postérieure à date_debut si renseignée."""
        date_debut = data.get('date_debut')
        date_fin = data.get('date_fin')
        if date_debut and date_fin and date_fin <= date_debut:
            raise serializers.ValidationError(
                {'date_fin': "La date de fin doit être postérieure à la date de début."}
            )
        return data


# =============================================================================
# DECLINAISON
# =============================================================================

class DeclinaisonSerializer(serializers.ModelSerializer):
    """
    Sérialise une déclinaison avec son stock et ses alertes.
    Utilisé dans la grille tailles/coloris du POS et de la fiche produit.
    """

    prix_effectif = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        read_only=True,
        help_text="Prix réel = prix_vente_specifique si défini, sinon prix de l'article parent."
    )

    qr_code_data_url = serializers.SerializerMethodField(
        help_text="QR code de la déclinaison encodé en data URL."
    )

    en_alerte_stock = serializers.BooleanField(
        read_only=True,
        help_text="True si stock_actuel <= stock_minimum."
    )

    class Meta:
        model = Declinaison
        fields = [
            'id', 'article', 'taille', 'coloris',
            'code_barres', 'qr_code_data_url',
            'stock_actuel', 'stock_minimum',
            'stock_maximum', 'prix_vente_specifique',
            'prix_effectif', 'en_alerte_stock', 'actif',
        ]
        read_only_fields = [
            'id', 'code_barres', 'qr_code_data_url',
            'prix_effectif', 'en_alerte_stock',
        ]

    def validate(self, data):
        """Vérifie que stock_minimum <= stock_maximum si les deux sont renseignés."""
        stock_min = data.get('stock_minimum', 0)
        stock_max = data.get('stock_maximum')
        if stock_max is not None and stock_min > stock_max:
            raise serializers.ValidationError(
                {'stock_maximum': "Le stock maximum doit être supérieur au stock minimum."}
            )
        return data

    def get_qr_code_data_url(self, obj):
        return generer_qr_code_data_url(obj.code_barres)


class DeclinaisonPOSSerializer(serializers.ModelSerializer):
    """
    Version allégée pour le POS.
    Retourne uniquement les infos nécessaires pour le scan et l'ajout au panier.
    """

    prix_effectif = serializers.DecimalField(
        max_digits=12, decimal_places=2, read_only=True
    )
    designation_article = serializers.CharField(
        source='article.designation', read_only=True
    )
    reference_article = serializers.CharField(
        source='article.reference', read_only=True
    )

    qr_code_data_url = serializers.SerializerMethodField(
        help_text="QR code de la déclinaison encodé en data URL."
    )

    class Meta:
        model = Declinaison
        fields = [
            'id', 'reference_article', 'designation_article',
            'taille', 'coloris', 'code_barres', 'qr_code_data_url',
            'stock_actuel', 'prix_effectif',
        ]
        read_only_fields = fields

    def get_qr_code_data_url(self, obj):
        return generer_qr_code_data_url(obj.code_barres)


# =============================================================================
# ARTICLE
# =============================================================================

class ArticleLectureSerializer(serializers.ModelSerializer):
    """
    Serializer de LECTURE complet pour la fiche produit et le catalogue.

    prix_achat_ht est inclus ici car ce serializer est utilisé côté admin.
    Pour le frontend client, utiliser ArticleCatalogueSerializer.
    """

    marque = MarqueResumeSerializer(read_only=True)
    categorie = CategorieResumeSerializer(read_only=True)
    collection = serializers.StringRelatedField(read_only=True)
    declinaisons = DeclinaisonSerializer(many=True, read_only=True)
    marge_brute = serializers.DecimalField(
        max_digits=12, decimal_places=2, read_only=True
    )
    photo = serializers.SerializerMethodField()
    class Meta:
        model = Article
        fields = [
            'id', 'reference', 'designation', 'description',
            'marque', 'categorie', 'collection', 'fournisseur',
            'prix_achat_ht',        # Confidentiel — admin seulement
            'prix_vente_ttc', 'taux_tva',
            'genre', 'actif', 'photo',
            'magasin', 'date_ajout',
            'marge_brute', 'declinaisons',
        ]
        read_only_fields = ['id', 'date_ajout', 'marge_brute', 'declinaisons']

    def get_photo(self, obj):
        request = self.context.get('request')
        if obj.photo:
            return request.build_absolute_uri(obj.photo.url)
        return None

class ArticleCatalogueSerializer(serializers.ModelSerializer):
    """
    Version SANS prix_achat_ht pour l'affichage catalogue et le POS.
    Ne jamais exposer le prix d'achat au frontend vendeur.
    """

    marque = MarqueResumeSerializer(read_only=True)
    categorie = CategorieResumeSerializer(read_only=True)
    declinaisons = DeclinaisonPOSSerializer(many=True, read_only=True)
    photo = serializers.SerializerMethodField()

    class Meta:
        model = Article
        fields = [
            'id', 'reference', 'designation', 'description',
            'marque', 'categorie', 'collection',
            'prix_vente_ttc', 'taux_tva',
            'genre', 'actif', 'photo', 'date_ajout',
            'declinaisons',
        ]
        read_only_fields = fields

    def get_photo(self, obj):
        request = self.context.get('request')
        if obj.photo:
            return request.build_absolute_uri(obj.photo.url)
        return None

class ArticleEcritureSerializer(serializers.ModelSerializer):
    marque_id = serializers.PrimaryKeyRelatedField(
        queryset=Marque.objects.all(), source='marque'
    )
    categorie_id = serializers.PrimaryKeyRelatedField(
        queryset=Categorie.objects.all(), source='categorie'
    )
    collection_id = serializers.PrimaryKeyRelatedField(
        queryset=Collection.objects.all(), source='collection',
        required=False, allow_null=True
    )
    # Champ virtuel pour recevoir les déclinaisons en JSON
    declinaisons = serializers.CharField(required=False, write_only=True)

    class Meta:
        model = Article
        fields = [
            'reference', 'designation', 'description',
            'marque_id', 'categorie_id', 'collection_id', 'fournisseur',
            'prix_achat_ht', 'prix_vente_ttc', 'taux_tva',
            'genre', 'actif', 'photo', 'magasin',
            'declinaisons',  # ← champ virtuel
        ]
    def _traiter_declinaisons(self, article, declinaisons_json, is_create):
        if not declinaisons_json:
            return

        try:
            declinaisons = json.loads(declinaisons_json)
        except (json.JSONDecodeError, TypeError):
            return

        if not is_create:
            submitted_ids = []
            for d in declinaisons:
                did = d.get('id')
                if did:
                    try:
                        submitted_ids.append(int(did))
                    except:
                        pass

            article.declinaisons.exclude(id__in=submitted_ids).update(actif=False)

        for d in declinaisons:
            dec_id = d.get('id')

            if dec_id:
                try:
                    dec = Declinaison.objects.get(id=dec_id, article=article)
                    stock_avant = dec.stock_actuel

                    # champs classiques
                    dec.taille = d.get('taille', dec.taille)
                    dec.coloris = d.get('coloris', dec.coloris)
                    dec.stock_minimum = int(d.get('stock_minimum', dec.stock_minimum))
                    dec.stock_maximum = int(d['stock_maximum']) if d.get('stock_maximum') else None
                    dec.prix_vente_specifique = d.get('prix_vente_specifique')
                    dec.actif = d.get('actif', dec.actif)

                    # 🔥 ajout de stock
                    quantite_ajout = int(d.get('quantite_ajout', 0))

                    if quantite_ajout > 0:
                        dec.stock_actuel += quantite_ajout

                        MouvementStock.objects.create(
                            declinaison=dec,
                            type='entree',
                            quantite=quantite_ajout,
                            quantite_avant=stock_avant,
                            quantite_apres=dec.stock_actuel,
                            motif='Ajout de stock',
                        )

                    dec.save()

                except Declinaison.DoesNotExist:
                    pass

            else:
                # 🔥 création
                stock_initial = int(d.get('stock_initial', 0))

                dec = Declinaison.objects.create(
                    article=article,
                    taille=d.get('taille', ''),
                    coloris=d.get('coloris', ''),
                    stock_actuel=stock_initial,
                    stock_minimum=int(d.get('stock_minimum', 0)),
                    stock_maximum=d.get('stock_maximum'),
                    prix_vente_specifique=d.get('prix_vente_specifique'),
                    actif=d.get('actif', True),
                )

                if stock_initial > 0:
                    MouvementStock.objects.create(
                        declinaison=dec,
                        type='entree',
                        quantite=stock_initial,
                        quantite_avant=0,
                        quantite_apres=stock_initial,
                        motif='Stock initial',
                    )
    def create(self, validated_data):
        declinaisons_json = validated_data.pop('declinaisons', None)
        article = Article.objects.create(**validated_data)
        self._traiter_declinaisons(article, declinaisons_json, is_create=True)
        return article

    def update(self, instance, validated_data):
        declinaisons_json = validated_data.pop('declinaisons', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        self._traiter_declinaisons(instance, declinaisons_json, is_create=False)
        return instance
    
    def validate_prix_vente_ttc(self, valeur):
        if valeur <= 0:
            raise serializers.ValidationError(
                "Le prix de vente TTC doit être supérieur à 0."
            )
        return valeur

    def validate(self, data):
        """Vérifie que le prix de vente est supérieur au prix d'achat."""
        prix_achat = data.get('prix_achat_ht', 0)
        prix_vente = data.get('prix_vente_ttc', 0)
        if prix_achat > 0 and prix_vente <= prix_achat:
            raise serializers.ValidationError(
                "Le prix de vente TTC devrait être supérieur au prix d'achat HT."
            )
        return data
    



# =============================================================================
# MOUVEMENT STOCK
# =============================================================================

class MouvementStockSerializer(serializers.ModelSerializer):
    """
    Lecture seule des mouvements de stock.
    Les mouvements sont créés uniquement par les services métier (signaux Django),
    jamais directement via l'API.
    """

    declinaison_info = serializers.SerializerMethodField()
    utilisateur_nom = serializers.SerializerMethodField()

    class Meta:
        model = MouvementStock
        fields = [
            'id', 'declinaison', 'declinaison_info',
            'type', 'quantite', 'quantite_avant', 'quantite_apres',
            'motif', 'date_heure', 'utilisateur', 'utilisateur_nom',
            'source',
        ]
        read_only_fields = fields

    def get_declinaison_info(self, obj):
        """Retourne les infos lisibles de la déclinaison."""
        d = obj.declinaison
        return {
            'article': d.article.designation,
            'taille': d.taille,
            'coloris': d.coloris,
            'code_barres': d.code_barres,
        }

    def get_utilisateur_nom(self, obj):
        if obj.utilisateur:
            return f"{obj.utilisateur.prenom} {obj.utilisateur.nom}"
        return "Automatique"


class AjustementStockSerializer(serializers.Serializer):
    """
    Serializer pour les ajustements manuels de stock (hors inventaire).
    Utilisé par les gestionnaires pour corriger des erreurs ou enregistrer
    une casse, un vol, etc.
    """

    declinaison_id = serializers.PrimaryKeyRelatedField(
        queryset=Declinaison.objects.all(),
        source='declinaison',
        help_text="Déclinaison à ajuster."
    )

    type = serializers.ChoiceField(
        choices=[
            ('ajustement_positif', 'Ajustement positif'),
            ('ajustement_negatif', 'Ajustement négatif'),
        ],
        help_text="Sens de l'ajustement."
    )

    quantite = serializers.IntegerField(
        min_value=1,
        help_text="Nombre d'unités à ajuster. Toujours positif."
    )

    motif = serializers.CharField(
        max_length=255,
        help_text="Raison de l'ajustement : casse, vol, erreur de comptage..."
    )

    def validate(self, data):
        """
        Vérifie qu'un ajustement négatif ne met pas le stock en négatif.
        """
        declinaison = data['declinaison']
        if (data['type'] == 'ajustement_negatif' and
                data['quantite'] > declinaison.stock_actuel):
            raise serializers.ValidationError(
                f"Impossible : la quantité à retirer ({data['quantite']}) "
                f"dépasse le stock actuel ({declinaison.stock_actuel})."
            )
        return data


# =============================================================================
# INVENTAIRE
# =============================================================================

class LigneInventaireSerializer(serializers.ModelSerializer):
    """Sérialise une ligne d'inventaire avec l'écart calculé."""

    ecart = serializers.IntegerField(read_only=True)
    declinaison_info = serializers.SerializerMethodField()

    class Meta:
        model = LigneInventaire
        fields = [
            'id', 'inventaire', 'declinaison', 'declinaison_info',
            'quantite_theorique', 'quantite_comptee', 'ecart',
        ]
        read_only_fields = ['id', 'quantite_theorique', 'ecart', 'declinaison_info']

    def get_declinaison_info(self, obj):
        d = obj.declinaison
        return {
            'designation': d.article.designation,
            'taille': d.taille,
            'coloris': d.coloris,
            'code_barres': d.code_barres,
        }

    def validate_quantite_comptee(self, valeur):
        if valeur < 0:
            raise serializers.ValidationError(
                "La quantité comptée ne peut pas être négative."
            )
        return valeur


class InventaireSerializer(serializers.ModelSerializer):
    """
    Sérialise un inventaire avec toutes ses lignes.
    La validation de l'inventaire (statut → valide) est déclenchée
    via une action séparée dans la vue (POST /inventaires/{id}/valider/).
    """

    lignes = LigneInventaireSerializer(many=True, read_only=True)
    nombre_ecarts = serializers.SerializerMethodField()

    class Meta:
        model = Inventaire
        fields = [
            'id', 'date_inventaire', 'type', 'statut',
            'magasin', 'utilisateur', 'observation',
            'lignes', 'nombre_ecarts',
        ]
        read_only_fields = ['id', 'statut', 'lignes', 'nombre_ecarts']

    def get_nombre_ecarts(self, obj):
        from django.db.models import F
        import catalogue.models as models
        """Retourne le nombre de lignes avec un écart non nul."""
        return obj.lignes.exclude(
            quantite_comptee=models.F('quantite_theorique')
        ).count() if obj.pk else 0

    def validate(self, data):
        """
        Vérifie qu'il n'y a pas déjà un inventaire en cours pour ce magasin.
        """
        

        magasin = data.get('magasin')
        if magasin:
            inventaire_en_cours = Inventaire.objects.filter(
                magasin=magasin,
                statut='en_cours'
            )
            if self.instance:
                inventaire_en_cours = inventaire_en_cours.exclude(pk=self.instance.pk)

            if inventaire_en_cours.exists():
                raise serializers.ValidationError(
                    "Un inventaire est déjà en cours pour ce magasin. "
                    "Terminez-le avant d'en créer un nouveau."
                )
        return data