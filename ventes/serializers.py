"""
=============================================================================
SERIALIZERS — APP : ventes
=============================================================================
Couvre :
  - CaisseSerializer
  - SessionCaisseSerializer  (ouverture, fermeture, état)
  - LigneVenteSerializer
  - VenteSerializer          (lecture complète + ticket)
  - VenteCreationSerializer  (création POS en une seule requête)
  - PaiementSerializer
  - RetourSerializer
  - LigneRetourSerializer

Flux POS local :
  1. POST /sessions-caisse/ouvrir/         → ouvre la session
  2. POST /ventes/                         → crée vente + lignes + paiements
  3. GET  /ventes/{id}/ticket/             → génère le ticket
  4. POST /retours/                        → retour d'articles
  5. POST /sessions-caisse/{id}/fermer/   → ferme la session
=============================================================================
"""

from rest_framework import serializers
from django.db import transaction
from django.utils import timezone
from catalogue.models import Declinaison
from catalogue.serializers import generer_qr_code_data_url
from ventes.models import (
    Caisse, SessionCaisse, Vente, LigneVente, Paiement, Retour, LigneRetour
)


# =============================================================================
# CAISSE
# =============================================================================

class CaisseSerializer(serializers.ModelSerializer):
    """Sérialise un terminal point de vente."""

    solde_actuel = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        read_only=True,
        allow_null=True,
        help_text="Solde calculé depuis la session ouverte. Null si aucune session active."
    )

    session_ouverte = serializers.SerializerMethodField(
        help_text="Informations de la session ouverte, ou null."
    )

    class Meta:
        model = Caisse
        fields = [
            'id', 'libelle', 'emplacement',
            'actif', 'magasin',
            'solde_actuel', 'session_ouverte',
        ]
        read_only_fields = ['id', 'solde_actuel', 'session_ouverte']

    def get_session_ouverte(self, obj):
        session = obj.sessions.filter(statut='ouverte').first()
        if session:
            return {
                'id': str(session.id),
                'vendeur': f"{session.vendeur.prenom} {session.vendeur.nom}",
                'date_ouverture': session.date_ouverture,
                'total_encaisse': float(session.total_encaisse),
            }
        return None


# =============================================================================
# SESSION CAISSE
# =============================================================================

class SessionCaisseOuvertureSerializer(serializers.ModelSerializer):
    """
    Serializer pour OUVRIR une session de caisse.
    La caissière déclare le fond de caisse présent dans le tiroir.
    """

    class Meta:
        model = SessionCaisse
        fields = ['caisse', 'fond_caisse']

    def validate_caisse(self, caisse):
        """Vérifie que la caisse est active et n'a pas déjà une session ouverte."""
        if not caisse.actif:
            raise serializers.ValidationError(
                "Cette caisse est désactivée."
            )
        if caisse.sessions.filter(statut='ouverte').exists():
            raise serializers.ValidationError(
                f"La caisse '{caisse.libelle}' a déjà une session ouverte."
            )
        return caisse

    def create(self, validated_data):
        validated_data['vendeur'] = self.context['request'].user
        validated_data['date_ouverture'] = timezone.now()
        validated_data['statut'] = 'ouverte'
        return SessionCaisse.objects.create(**validated_data)

class SessionCaisseFermetureSerializer(serializers.Serializer):
    """
    Serializer pour FERMER une session de caisse.
    Le gérant ou la caissière déclare le montant espèces compté dans le tiroir.
    L'écart est calculé automatiquement.
    """

    montant_especes_compte = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Montant en espèces physiquement compté dans le tiroir à la fermeture."
    )

    observation = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Commentaire libre sur la fermeture de caisse."
    )


class SessionCaisseSerializer(serializers.ModelSerializer):
    """Lecture complète d'une session de caisse avec ses KPI."""

    caisse_libelle = serializers.CharField(
        source='caisse.libelle', read_only=True
    )
    vendeur_nom = serializers.SerializerMethodField()
    delta_especes = serializers.SerializerMethodField()

    class Meta:
        model = SessionCaisse
        fields = [
            'id', 'caisse', 'caisse_libelle',
            'vendeur', 'vendeur_nom',
            'date_ouverture', 'date_fermeture',
            'fond_caisse', 'total_encaisse',
            'total_especes', 'total_carte',
            'statut', 'delta_especes',
        ]
        read_only_fields = fields

    def get_vendeur_nom(self, obj):
        return f"{obj.vendeur.prenom} {obj.vendeur.nom}"

    def get_delta_especes(self, obj):
        """
        Écart de caisse = (fond_caisse + total_especes) - montant_especes_compte.
        Disponible uniquement après fermeture.
        Null si la session est encore ouverte.
        """
        return None  # Calculé lors de la fermeture, stocké ailleurs si besoin


# =============================================================================
# LIGNE VENTE
# =============================================================================

class LigneVenteCreationSerializer(serializers.ModelSerializer):
    """
    Serializer pour la création d'une ligne de vente dans le POS.
    Le frontend peut envoyer l'ID de la déclinaison ou le code-barres scanné.
    Les prix sont récupérés et figés automatiquement depuis la déclinaison.
    """

    code_barres = serializers.CharField(
        required=False,
        write_only=True,
        help_text="Code-barres scanné qui identifie la déclinaison."
    )
    declinaison = serializers.PrimaryKeyRelatedField(
        queryset=Declinaison.objects.all(),
        required=False,
        allow_null=True,
    )

    class Meta:
        model = LigneVente
        fields = ['declinaison', 'code_barres', 'quantite', 'remise_ligne']

    def validate(self, data):
        declinaison = data.get('declinaison')
        code_barres = data.get('code_barres')
        quantite = data.get('quantite')

        if not declinaison:
            if not code_barres:
                raise serializers.ValidationError(
                    "La ligne de vente doit contenir une déclinaison ou un code-barres."
                )
            try:
                declinaison = Declinaison.objects.get(code_barres=code_barres)
            except Declinaison.DoesNotExist:
                raise serializers.ValidationError(
                    {'code_barres': "Code-barres inconnu pour une déclinaison active."}
                )
            data['declinaison'] = declinaison
        
        # Vérifier que la déclinaison est active
        if not declinaison.actif:
            raise serializers.ValidationError(
                f"L'article '{declinaison}' n'est plus disponible à la vente."
            )

        if declinaison.stock_actuel < quantite:
            raise serializers.ValidationError(
                {
                    'quantite': (
                        f"Stock insuffisant pour '{declinaison}'. "
                        f"Disponible : {declinaison.stock_actuel}, demandé : {quantite}."
                    )
                }
            )

        return data

       


class LigneVenteLectureSerializer(serializers.ModelSerializer):
    """Lecture d'une ligne de vente avec les infos lisibles de la déclinaison."""

    declinaison_info = serializers.SerializerMethodField()

    class Meta:
        model = LigneVente
        fields = [
            'id', 'declinaison', 'declinaison_info',
            'quantite', 'prix_unitaire_ht', 'prix_unitaire_ttc',
            'taux_tva', 'remise_ligne', 'total_ligne_ttc',
        ]
        read_only_fields = fields

    def get_declinaison_info(self, obj):
        d = obj.declinaison
        return {
            'designation': d.article.designation,
            'reference': d.article.reference,
            'taille': d.taille,
            'coloris': d.coloris,
            'code_barres': d.code_barres,
            'qr_code_data_url': generer_qr_code_data_url(d.code_barres),
            'photo': d.article.photo.url if d.article.photo else None,
        }


# =============================================================================
# PAIEMENT
# =============================================================================
class PaiementCreationSerializer(serializers.ModelSerializer):

    class Meta:
        model = Paiement
        fields = ['mode_paiement', 'montant', 'reference', 'avoir']

    def validate(self, data):
        if data['mode_paiement'] == 'avoir':
            avoir = data.get('avoir')

            if not avoir:
                raise serializers.ValidationError(
                    {'avoir': "Un avoir doit être sélectionné pour ce mode de paiement."}
                )

            if avoir.statut != 'actif':
                raise serializers.ValidationError(
                    {'avoir': f"L'avoir '{avoir.numero}' n'est pas utilisable."}
                )

            if data['montant'] > avoir.solde:
                raise serializers.ValidationError(
                    {'montant': "Montant dépasse le solde de l'avoir."}
                )

        return data

    def create(self, validated_data):
        request = self.context['request']

        # 🔥 1. récupérer vente (OBLIGATOIRE)
        vente_id = self.context.get("vente_id")

        if not vente_id:
            raise serializers.ValidationError("Vente manquante.")

        try:
            vente = Vente.objects.get(id=vente_id)
        except Vente.DoesNotExist:
            raise serializers.ValidationError("Vente introuvable.")

        validated_data['vente'] = vente

        # 🔥 2. session caisse automatique
        session = SessionCaisse.objects.filter(
            vendeur=request.user,
            statut="ouverte"
        ).first()

        if not session:
            raise serializers.ValidationError(
                "Aucune session de caisse active."
            )

        validated_data['session_caisse'] = session

        return super().create(validated_data)
    


class PaiementLectureSerializer(serializers.ModelSerializer):

    mode_display = serializers.CharField(
        source='get_mode_paiement_display', read_only=True
    )

    class Meta:
        model = Paiement
        fields = [
            'id', 'vente', 'mode_paiement', 'mode_display',
            'montant', 'reference', 'date_heure',
            'statut', 'avoir', 'session_caisse',
        ]
        read_only_fields = fields


# =============================================================================
# VENTE — LECTURE
# =============================================================================

class VenteLectureSerializer(serializers.ModelSerializer):
    """
    Lecture complète d'une vente avec toutes ses lignes et paiements.
    Utilisé pour l'historique, le ticket de caisse, et les rapports.
    """

    lignes = LigneVenteLectureSerializer(many=True, read_only=True)
    paiements = PaiementLectureSerializer(many=True, read_only=True)
    vendeur_nom = serializers.SerializerMethodField()
    client_nom = serializers.SerializerMethodField()
    statut_display = serializers.CharField(
        source='get_statut_display', read_only=True
    )

    class Meta:
        model = Vente
        fields = [
            'id', 'numero_bon', 'date_heure', 'statut', 'statut_display',
            'total_ht', 'montant_tva', 'montant_remise',
            'total_ttc', 'montant_paye', 'montant_rendu',
            'vendeur', 'vendeur_nom',
            'client', 'client_nom',
            'session_caisse', 'magasin',
            'lignes', 'paiements',
        ]
        read_only_fields = fields

    def get_vendeur_nom(self, obj):
        return f"{obj.vendeur.prenom} {obj.vendeur.nom}"

    def get_client_nom(self, obj):
        if obj.client:
            return str(obj.client)
        return "Client anonyme"


# =============================================================================
# VENTE — CRÉATION POS (requête unique)
# =============================================================================
class VenteCreationSerializer(serializers.Serializer):
    """
    Création d'une vente POS en une seule requête.
    """

    session_caisse_id = serializers.PrimaryKeyRelatedField(
        queryset=SessionCaisse.objects.filter(statut='ouverte'),
        source='session_caisse'
    )

    client_id = serializers.PrimaryKeyRelatedField(
        queryset=__import__('clients.models', fromlist=['Client']).Client.objects.filter(actif=True),
        source='client',
        required=False,
        allow_null=True
    )

    lignes = LigneVenteCreationSerializer(many=True)
    paiements = PaiementCreationSerializer(many=True)

    # =========================================================
    # VALIDATIONS
    # =========================================================

    def validate_lignes(self, value):
        if not value:
            raise serializers.ValidationError("La vente doit contenir au moins un article.")
        return value

    def validate_paiements(self, value):
        if not value:
            raise serializers.ValidationError("La vente doit contenir au moins un paiement.")
        return value

    def validate(self, data):
        from decimal import Decimal

        lignes = data.get("lignes", [])
        paiements = data.get("paiements", [])

        total_ttc = Decimal("0")

        for ligne in lignes:
            declinaison = ligne["declinaison"]
            quantite = ligne["quantite"]
            remise = ligne.get("remise_ligne", Decimal("0"))

            prix = declinaison.prix_effectif
            total_ttc += (prix * quantite) - remise

        total_paye = sum(p["montant"] for p in paiements)

        if total_paye < total_ttc:
            raise serializers.ValidationError(
                {
                    "paiements": f"Paiement insuffisant ({total_paye} < {total_ttc})"
                }
            )

        data["total_ttc_calcule"] = total_ttc
        data["total_paye_calcule"] = total_paye
        return data

    # =========================================================
    # CREATE
    # =========================================================

    @transaction.atomic
    def create(self, validated_data):
        from decimal import Decimal
        from collections import defaultdict
        from catalogue.models import MouvementStock

        request = self.context["request"]
        utilisateur = request.user

        session = validated_data["session_caisse"]
        client = validated_data.get("client")

        lignes_data = validated_data["lignes"]
        paiements_data = validated_data["paiements"]

        total_ttc = validated_data["total_ttc_calcule"]
        total_paye = validated_data["total_paye_calcule"]

        # =====================================================
        # 1️⃣ NUMERO DE BON
        # =====================================================
        annee = timezone.now().year
        count = Vente.objects.filter(numero_bon__startswith=f"VTE-{annee}-").count()
        numero_bon = f"VTE-{annee}-{str(count + 1).zfill(5)}"

        # =====================================================
        # 2️⃣ CALCUL HT / TVA
        # =====================================================
        total_ht = Decimal("0")
        montant_tva = Decimal("0")

        for ligne in lignes_data:
            d = ligne["declinaison"]
            q = ligne["quantite"]

            taux = d.article.taux_tva / 100
            prix_ttc = d.prix_effectif
            prix_ht = prix_ttc / (1 + taux)

            total_ht += prix_ht * q
            montant_tva += (prix_ttc - prix_ht) * q

        montant_rendu = max(Decimal("0"), total_paye - total_ttc)

        # =====================================================
        # 3️⃣ CREATION VENTE
        # =====================================================
        vente = Vente.objects.create(
            numero_bon=numero_bon,
            statut="validee",
            total_ht=total_ht,
            montant_tva=montant_tva,
            total_ttc=total_ttc,
            montant_paye=total_paye,
            montant_rendu=montant_rendu,
            vendeur=utilisateur,
            client=client,
            session_caisse=session,
            magasin=session.caisse.magasin,
        )

        # =====================================================
        # 4️⃣ LIGNES DE VENTE (inchangé)
        # =====================================================
        for ligne in lignes_data:
            declinaison = ligne["declinaison"]
            qte = ligne["quantite"]
            remise = ligne.get("remise_ligne", Decimal("0"))

            taux_tva = declinaison.article.taux_tva
            prix_ttc = declinaison.prix_effectif
            prix_ht = prix_ttc / (1 + taux_tva / 100)

            LigneVente.objects.create(
                vente=vente,
                declinaison=declinaison,
                quantite=qte,
                prix_unitaire_ht=prix_ht,
                prix_unitaire_ttc=prix_ttc,
                taux_tva=taux_tva,
                remise_ligne=remise,
            )

        # =====================================================
        # 5️⃣ STOCK + MOUVEMENTS (FIX IMPORTANT)
        # =====================================================
        groupes = defaultdict(int)

        for ligne in lignes_data:
            groupes[ligne["declinaison"].id] += ligne["quantite"]

        for declinaison_id, total_qte in groupes.items():
            declinaison = Declinaison.objects.get(id=declinaison_id)

            stock_avant = declinaison.stock_actuel
            declinaison.stock_actuel -= total_qte
            declinaison.save(update_fields=["stock_actuel"])

            MouvementStock.objects.create(
                declinaison=declinaison,
                type="sortie",
                quantite=total_qte,
                quantite_avant=stock_avant,
                quantite_apres=declinaison.stock_actuel,
                utilisateur=utilisateur,
                source={"type": "vente", "id": str(vente.id)},
            )

        # =====================================================
        # 6️⃣ PAIEMENTS
        # =====================================================
        total_especes = Decimal("0")
        total_carte = Decimal("0")

        for p in paiements_data:
            Paiement.objects.create(
                vente=vente,
                session_caisse=session,
                **p,
            )

            if p["mode_paiement"] == "especes":
                total_especes += p["montant"]
            else:
                total_carte += p["montant"]

        SessionCaisse.objects.filter(pk=session.pk).update(
            total_encaisse=session.total_encaisse + total_ttc,
            total_especes=session.total_especes + total_especes,
            total_carte=session.total_carte + total_carte,
        )

        return vente
# =============================================================================
# RETOUR
# =============================================================================

class LigneRetourSerializer(serializers.ModelSerializer):
    """Sérialise une ligne de retour."""

    declinaison_info = serializers.SerializerMethodField()

    class Meta:
        model = LigneRetour
        fields = [
            'id', 'retour', 'ligne_vente_originale',
            'declinaison_info',
            'quantite_retournee', 'montant_rembourse_ligne',
        ]
        read_only_fields = ['id', 'declinaison_info']

    def get_declinaison_info(self, obj):
        d = obj.ligne_vente_originale.declinaison
        return {
            'designation': d.article.designation,
            'taille': d.taille,
            'coloris': d.coloris,
        }


class LigneRetourCreationSerializer(serializers.ModelSerializer):
    """Serializer pour la saisie des lignes lors d'un retour."""

    class Meta:
        model = LigneRetour
        fields = ['ligne_vente_originale', 'quantite_retournee']

    def validate(self, data):
        ligne_originale = data['ligne_vente_originale']
        qte_retournee = data['quantite_retournee']

        # Vérifier qu'on ne retourne pas plus que ce qui a été acheté
        deja_retourne = sum(
            lr.quantite_retournee
            for lr in ligne_originale.lignes_retour.all()
        )
        if deja_retourne + qte_retournee > ligne_originale.quantite:
            raise serializers.ValidationError(
                {
                    'quantite_retournee': (
                        f"Impossible de retourner {qte_retournee} unités. "
                        f"Quantité achetée : {ligne_originale.quantite}, "
                        f"déjà retournée : {deja_retourne}."
                    )
                }
            )
        return data


class RetourCreationSerializer(serializers.Serializer):
    """
    Crée un retour complet avec ses lignes en une seule requête.

    {
        "vente_originale_id": "uuid",
        "motif": "Taille incorrecte",
        "type_retour": "avoir",
        "lignes": [
            {"ligne_vente_originale": "uuid-ligne", "quantite_retournee": 1}
        ]
    }
    """

    vente_originale_id = serializers.PrimaryKeyRelatedField(
        queryset=Vente.objects.filter(statut='validee'),
        source='vente_originale',
        help_text="Vente d'origine. Doit être au statut 'validee'."
    )

    motif = serializers.CharField(
        help_text="Raison du retour : défaut produit, taille incorrecte, etc."
    )

    type_retour = serializers.ChoiceField(
        choices=[
            ('remboursement', 'Remboursement'),
            ('echange', 'Échange'),
            ('avoir', 'Avoir'),
        ]
    )

    lignes = LigneRetourCreationSerializer(many=True)

    def validate_lignes(self, valeur):
        if not valeur:
            raise serializers.ValidationError(
                "Le retour doit contenir au moins une ligne."
            )
        return valeur

    @transaction.atomic
    def create(self, validated_data):
        from decimal import Decimal
        from catalogue.models import MouvementStock

        utilisateur = self.context['request'].user
        vente = validated_data['vente_originale']
        lignes_data = validated_data['lignes']
        type_retour = validated_data['type_retour']

        # Calculer le montant total remboursé
        montant_total = Decimal('0')
        for ligne_data in lignes_data:
            ligne_orig = ligne_data['ligne_vente_originale']
            qte = ligne_data['quantite_retournee']
            montant_total += ligne_orig.prix_unitaire_ttc * qte

        # --- Créer l'avoir si nécessaire ---
        avoir = None
        if type_retour == 'avoir' and vente.client:
            from clients.models import Avoir
            from django.utils import timezone
            import datetime

            annee = timezone.now().year
            dernier = Avoir.objects.filter(
                numero__startswith=f'AV-{annee}-'
            ).count()
            numero_avoir = f"AV-{annee}-{str(dernier + 1).zfill(4)}"

            avoir = Avoir.objects.create(
                client=vente.client,
                numero=numero_avoir,
                montant=montant_total,
                date_expiration=(
                    timezone.now().date() + datetime.timedelta(days=365)
                ),
                statut='actif',
            )

        # --- Créer le retour ---
        retour = Retour.objects.create(
            vente_originale=vente,
            motif=validated_data['motif'],
            type_retour=type_retour,
            montant_rembourse=montant_total if type_retour == 'remboursement' else Decimal('0'),
            avoir=avoir,
            vendeur=utilisateur,
            statut='valide',
        )

        # --- Créer les lignes et remettre le stock ---
        for ligne_data in lignes_data:
            ligne_orig = ligne_data['ligne_vente_originale']
            qte = ligne_data['quantite_retournee']
            declinaison = ligne_orig.declinaison

            LigneRetour.objects.create(
                retour=retour,
                ligne_vente_originale=ligne_orig,
                quantite_retournee=qte,
                montant_rembourse_ligne=ligne_orig.prix_unitaire_ttc * qte,
            )

            # Remettre en stock
            stock_avant = declinaison.stock_actuel
            declinaison.stock_actuel += qte
            declinaison.save(update_fields=['stock_actuel'])

            MouvementStock.objects.create(
                declinaison=declinaison,
                type='retour_client',
                quantite=qte,
                quantite_avant=stock_avant,
                quantite_apres=declinaison.stock_actuel,
                utilisateur=utilisateur,
                source={'type': 'retour', 'id': str(retour.id)},
            )

        # --- Mettre à jour le statut de la vente originale ---
        vente.statut = 'retournee'
        vente.save(update_fields=['statut'])

        return retour


class RetourLectureSerializer(serializers.ModelSerializer):
    """Lecture complète d'un retour avec ses lignes."""

    lignes = LigneRetourSerializer(many=True, read_only=True)
    type_retour_display = serializers.CharField(
        source='get_type_retour_display', read_only=True
    )
    vendeur_nom = serializers.SerializerMethodField()

    class Meta:
        model = Retour
        fields = [
            'id', 'vente_originale', 'date_retour',
            'motif', 'type_retour', 'type_retour_display',
            'montant_rembourse', 'avoir',
            'vendeur', 'vendeur_nom',
            'statut', 'lignes',
        ]
        read_only_fields = fields

    def get_vendeur_nom(self, obj):
        return f"{obj.vendeur.prenom} {obj.vendeur.nom}"