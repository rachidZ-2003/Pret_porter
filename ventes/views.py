



import os

import qrcode
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from ventes.models import (
    Caisse, SessionCaisse, Vente,
    LigneVente, Paiement, Retour, LigneRetour,
)
from django.http import HttpResponse
from django.utils import timezone
from reportlab.lib.pagesizes import A6, A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
import io

from rest_framework.permissions import  AllowAny

from ventes.serializers import (
    CaisseSerializer,
    SessionCaisseSerializer,
    SessionCaisseOuvertureSerializer,
    VenteLectureSerializer,
    VenteCreationSerializer,
    LigneVenteLectureSerializer,
    LigneVenteCreationSerializer,
    PaiementLectureSerializer,
    PaiementCreationSerializer,
    RetourLectureSerializer,
    RetourCreationSerializer,
    LigneRetourSerializer,
)


class CaisseViewSet(viewsets.ModelViewSet):
    queryset = Caisse.objects.all()
    serializer_class = CaisseSerializer


class SessionCaisseViewSet(viewsets.ModelViewSet):
    queryset = SessionCaisse.objects.all()

    def get_serializer_class(self):
        if self.action == 'create':
            return SessionCaisseOuvertureSerializer
        return SessionCaisseSerializer


class VenteViewSet(viewsets.ModelViewSet):
    queryset = Vente.objects.all()

    def get_serializer_class(self):
        if self.action == 'create':
            return VenteCreationSerializer
        return VenteLectureSerializer


    import io
import os
from django.conf import settings
from django.http import HttpResponse
from django.utils import timezone
from reportlab.lib.pagesizes import A6
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
import qrcode
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework import viewsets
from ventes.models import Vente
from ventes.serializers import VenteLectureSerializer, VenteCreationSerializer

class VenteViewSet(viewsets.ModelViewSet):
    queryset = Vente.objects.all()

    def get_serializer_class(self):
        if self.action == 'create':
            return VenteCreationSerializer
        return VenteLectureSerializer

    @action(detail=True, methods=['get'], url_path='ticket', permission_classes=[AllowAny])
    def ticket(self, request, pk=None):
        vente = self.get_object()
        magasin = vente.magasin

        # ── Gestion du logo ──────────────────────────────────────────────────
        logo_path = None
        if magasin and magasin.logo:
            potential_logo = os.path.join(settings.MEDIA_ROOT, magasin.logo.name)
            if os.path.exists(potential_logo):
                logo_path = potential_logo
        if not logo_path:
            default_logo = os.path.join(settings.BASE_DIR, 'static', 'images', 'logo.png')
            if os.path.exists(default_logo):
                logo_path = default_logo

        buffer = io.BytesIO()
        width, height = A6
        p = canvas.Canvas(buffer, pagesize=A6)

        # ── Palette de couleurs ───────────────────────────────────────────────
        BLACK      = (0.08, 0.08, 0.08)
        DARK_GRAY  = (0.25, 0.25, 0.25)
        MID_GRAY   = (0.55, 0.55, 0.55)
        LIGHT_GRAY = (0.92, 0.92, 0.92)
        WHITE      = (1, 1, 1)
        ACCENT     = (0.10, 0.10, 0.40)

        ML = 12
        MR = width - 12
        CW = MR - ML

        def set_color(rgb):
            p.setFillColorRGB(*rgb)

        def set_stroke(rgb):
            p.setStrokeColorRGB(*rgb)

        def hrule(y, color=MID_GRAY, thickness=0.5):
            set_stroke(color)
            p.setLineWidth(thickness)
            p.line(ML, y, MR, y)

        def filled_rect(x, y, w, h, color):
            p.setFillColorRGB(*color)
            p.rect(x, y, w, h, fill=1, stroke=0)

        # ══════════════════════════════════════════════════════════════════════
        # HEADER BAND
        # ══════════════════════════════════════════════════════════════════════
        header_h = 52
        filled_rect(0, height - header_h, width, header_h, ACCENT)

        # ── Ajout du logo (s'il existe) ──
        logo_width = 0
        logo_height = 0
        if logo_path and os.path.exists(logo_path):
            try:
                img = ImageReader(logo_path)
                iw, ih = img.getSize()
                max_h = 32
                if ih > max_h:
                    logo_width = iw * (max_h / ih)
                    logo_height = max_h
                else:
                    logo_width = iw
                    logo_height = ih
                logo_x = 8
                logo_y = height - header_h + (header_h - logo_height) / 2
                p.drawImage(logo_path, logo_x, logo_y, width=logo_width, height=logo_height, mask='auto')
            except Exception as e:
                print(f"Erreur chargement logo : {e}")

        # Texte centré (décalé si logo présent)
        text_center_x = width / 2
        if logo_width > 0:
            text_center_x = width / 2 + logo_width / 2 + 5

        set_color(WHITE)
        p.setFont("Helvetica-Bold", 14)
        p.drawCentredString(text_center_x, height - 18, "PRÊT À PORTER")
        p.setFont("Helvetica", 7)
        p.drawCentredString(text_center_x, height - 29, "Boutique de référence · Vêtements & Accessoires")
        p.drawCentredString(text_center_x, height - 38, "Tél : +226 54 22 77 12")
        set_stroke(WHITE)
        p.setLineWidth(0.3)
        p.line(ML + 10, height - 43, MR - 10, height - 43)
        p.setFont("Helvetica-Oblique", 6.5)
        p.drawCentredString(text_center_x, height - 50, "www.hoolearn.net")

        # ── Meta row ──────────────────────────────────────────────────────────
        y = height - header_h - 10
        set_color(DARK_GRAY)
        p.setFont("Helvetica", 6.5)
        p.drawString(ML, y, f"Date : {timezone.now().strftime('%d/%m/%Y  %H:%M')}")
        p.setFont("Helvetica-Bold", 6.5)
        p.drawRightString(MR, y, f"N° {vente.numero_bon}")

        hrule(y - 4, color=LIGHT_GRAY, thickness=0.8)

        # ── Vendeur / Client ──────────────────────────────────────────────────
        y -= 14
        set_color(MID_GRAY)
        p.setFont("Helvetica", 6)
        p.drawString(ML, y, "VENDEUR")
        y -= 8
        set_color(BLACK)
        p.setFont("Helvetica-Bold", 7)
        p.drawString(ML, y, f"{vente.vendeur.prenom} {vente.vendeur.nom}")
        hrule(y - 6, color=LIGHT_GRAY)

        # ══════════════════════════════════════════════════════════════════════
        # ARTICLES TABLE
        # ══════════════════════════════════════════════════════════════════════
        y -= 16
        COL_DESC  = ML
        COL_QTY   = MR - 52
        COL_PRICE = MR

        filled_rect(ML - 2, y - 2, CW + 4, 11, ACCENT)
        set_color(WHITE)
        p.setFont("Helvetica-Bold", 6.5)
        p.drawString(COL_DESC, y + 1, "ARTICLE")
        p.drawCentredString(COL_QTY + 6, y + 1, "QTÉ")
        p.drawRightString(COL_PRICE, y + 1, "PRIX UNIT.")

        y -= 3
        row_h = 11
        BOTTOM_RESERVED = 18 + 28 + 10 + 10
        lignes = list(vente.lignes.all())
        for i, ligne in enumerate(lignes):
            if y - row_h < BOTTOM_RESERVED:
                p.showPage()
                y = height - 20
                p.setFont("Helvetica", 7)
            if i % 2 == 0:
                filled_rect(ML - 2, y - row_h + 2, CW + 4, row_h, LIGHT_GRAY)
            desc = f"{ligne.declinaison.article.designation} ({ligne.declinaison.taille}/{ligne.declinaison.coloris})"
            if len(desc) > 34:
                desc = desc[:31] + "…"
            set_color(BLACK)
            p.setFont("Helvetica", 6.5)
            p.drawString(COL_DESC, y - 5, desc)
            set_color(DARK_GRAY)
            p.setFont("Helvetica-Bold", 6.5)
            p.drawCentredString(COL_QTY + 6, y - 5, str(ligne.quantite))
            set_color(BLACK)
            p.setFont("Helvetica", 6.5)
            p.drawRightString(COL_PRICE, y - 5, f"{ligne.prix_unitaire_ttc:,.0f} F")
            y -= row_h

        # ══════════════════════════════════════════════════════════════════════
        # TOTALS SECTION
        # ══════════════════════════════════════════════════════════════════════
        y -= 6
        hrule(y, color=ACCENT, thickness=1)
        y -= 2
        QR_SIZE = 28
        QR_MARGIN = 6

        def total_row(label, value, bold=False, color=BLACK):
            nonlocal y
            y -= 11
            set_color(MID_GRAY)
            p.setFont("Helvetica", 6.5)
            p.drawString(ML, y, label)
            set_color(color)
            font = "Helvetica-Bold" if bold else "Helvetica"
            p.setFont(font, 6.5 if not bold else 8)
            p.drawRightString(MR, y, value)

        total_row("Prix Total  :", f"{vente.total_ttc:,.0f} F", bold=True, color=ACCENT)
        total_row("Payé :",      f"{vente.montant_paye:,.0f} F")
        y -= (QR_SIZE + QR_MARGIN)

        # Payment mode pill
        paiement = vente.paiements.first()
        if paiement:
            y -= 12
            mode = paiement.get_mode_paiement_display()
            pill_w = p.stringWidth(f"  {mode}  ", "Helvetica-Bold", 6.5) + 4
            filled_rect(ML, y - 2, pill_w, 10, LIGHT_GRAY)
            set_color(DARK_GRAY)
            p.setFont("Helvetica-Bold", 6.5)
            p.drawString(ML + 2, y + 1, f"💳  {mode}")

        # ── QR Code ────────────────────────────────────────────────────────────
        try:
            qr_img = qrcode.make(vente.numero_bon)
            qr_io = io.BytesIO()
            qr_img.save(qr_io, format='PNG')
            qr_io.seek(0)
            qr_size = 28
            qr_y = y
            p.drawImage(ImageReader(qr_io), MR - qr_size, qr_y, width=qr_size, height=qr_size, mask='auto')
        except Exception:
            pass

        # ── Footer ────────────────────────────────────────────────────────────
        footer_h = 18
        footer_y = y - 20
        footer_y = max(footer_y, 2)
        filled_rect(0, footer_y, width, footer_h, ACCENT)
        set_color(WHITE)
        p.setFont("Helvetica-Oblique", 6)
        p.drawCentredString(width / 2, footer_y + 10, "Merci de votre visite ! Bonne suite a vous")
        p.drawCentredString(width / 2, footer_y + 3, "A bientôt chez Prêt à Porter !")

        p.showPage()
        p.save()

        buffer.seek(0)
        response = HttpResponse(buffer, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="ticket_{vente.numero_bon}.pdf"'
        return response


class LigneVenteViewSet(viewsets.ModelViewSet):
    queryset = LigneVente.objects.all()

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return LigneVenteCreationSerializer
        return LigneVenteLectureSerializer


class PaiementViewSet(viewsets.ModelViewSet):
    queryset = Paiement.objects.all()

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return PaiementCreationSerializer
        return PaiementLectureSerializer
     

     
    def get_serializer_context(self):
        context = super().get_serializer_context()

        context["vente_id"] = self.request.data.get("vente_id")

        return context


class RetourViewSet(viewsets.ModelViewSet):
    queryset = Retour.objects.all()

    def get_serializer_class(self):
        if self.action == 'create':
            return RetourCreationSerializer
        return RetourLectureSerializer


class LigneRetourViewSet(viewsets.ModelViewSet):
    queryset = LigneRetour.objects.all()
    serializer_class = LigneRetourSerializer
