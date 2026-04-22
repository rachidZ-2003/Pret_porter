from urllib import request

from django.http import HttpResponse
import io

import qrcode
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import serializers

from catalogue.models import (
    Categorie, Marque, Collection, Article,
    Declinaison, MouvementStock, Inventaire, LigneInventaire,
)
from catalogue.serializers import (
    ArticleCatalogueSerializer,
    CategorieSerializer,
    MarqueSerializer,
    CollectionSerializer,
    ArticleLectureSerializer,
    ArticleEcritureSerializer,
    DeclinaisonSerializer,
    MouvementStockSerializer,
    InventaireSerializer,
    LigneInventaireSerializer,
)


class DeclinaisonReapprovisionnementSerializer(serializers.Serializer):
    quantite = serializers.IntegerField(
        min_value=1,
        help_text="Quantité à ajouter au stock lors du réapprovisionnement."
    )
    motif = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Motif ou référence de la réception fournisseur."
    )


class CategorieViewSet(viewsets.ModelViewSet):
    queryset = Categorie.objects.all()
    serializer_class = CategorieSerializer


class MarqueViewSet(viewsets.ModelViewSet):
    queryset = Marque.objects.all()
    serializer_class = MarqueSerializer


class CollectionViewSet(viewsets.ModelViewSet):
    queryset = Collection.objects.all()
    serializer_class = CollectionSerializer


class ArticleViewSet(viewsets.ModelViewSet):
    queryset = Article.objects.all()
   

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return ArticleEcritureSerializer
        return ArticleLectureSerializer


class DeclinaisonViewSet(viewsets.ModelViewSet):
    queryset = Declinaison.objects.all()
    serializer_class = DeclinaisonSerializer

    @action(detail=False, methods=['get'], url_path='par-code-barres')
    def par_code_barres(self, request):
        code = request.query_params.get('code_barres') or request.query_params.get('code')
        if not code:
            return Response(
                {'detail': "Paramètre 'code_barres' requis."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        declinaison = Declinaison.objects.filter(code_barres=code).first()
        if not declinaison:
            return Response(
                {'detail': "Déclinaison introuvable pour ce code-barres."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(self.get_serializer(declinaison).data)

    @action(detail=True, methods=['post'], url_path='reapprovisionner')
    def reapprovisionner(self, request, pk=None):
        declinaison = self.get_object()
        serializer = DeclinaisonReapprovisionnementSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        quantite = serializer.validated_data['quantite']
        motif = serializer.validated_data.get('motif', '')

        stock_avant = declinaison.stock_actuel
        declinaison.stock_actuel += quantite
        declinaison.save(update_fields=['stock_actuel'])

        MouvementStock.objects.create(
            declinaison=declinaison,
            type='entree',
            quantite=quantite,
            quantite_avant=stock_avant,
            quantite_apres=declinaison.stock_actuel,
            utilisateur=getattr(request, 'user', None),
            motif=motif,
            source={'type': 'reapprovisionnement', 'motif': motif},
        )

        return Response(self.get_serializer(declinaison).data)

    @action(detail=True, methods=['get'], url_path='qr-code')
    def qr_code(self, request, pk=None):
        declinaison = self.get_object()
        code_barres = declinaison.code_barres
        if not code_barres:
            return Response(
                {'detail': "Aucun code-barres défini pour cette déclinaison."},
                status=status.HTTP_404_NOT_FOUND,
            )

        qr = qrcode.QRCode(box_size=10, border=4)
        qr.add_data(str(code_barres))
        qr.make(fit=True)
        image = qr.make_image(fill_color='black', back_color='white')
        buffer = io.BytesIO()
        image.save(buffer, format='PNG')
        buffer.seek(0)

        response = HttpResponse(buffer.getvalue(), content_type='image/png')
        response['Content-Disposition'] = (
            f'attachment; filename="declinaison-{declinaison.id}-qr.png"'
        )
        return response


class MouvementStockViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = MouvementStock.objects.all()
    serializer_class = MouvementStockSerializer


class InventaireViewSet(viewsets.ModelViewSet):
    queryset = Inventaire.objects.all()
    serializer_class = InventaireSerializer


class LigneInventaireViewSet(viewsets.ModelViewSet):
    queryset = LigneInventaire.objects.all()
    serializer_class = LigneInventaireSerializer
