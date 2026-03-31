import os
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.urls import reverse
from django.conf import settings

# PDF
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib.enums import TA_RIGHT, TA_CENTER, TA_LEFT


# ✅ EMAIL CLIENT + FACTURE
def send_order_confirmation_email(order):
    try:
        subject = f"Confirmation de votre commande #{order.id} 📝"

        base_url = getattr(settings, 'SITE_URL', 'https://cinderaproduitsnaturels.com')
        order_path = reverse('products:order_detail', args=[order.id])
        order_url = f"{base_url}{order_path}"

        html_content = render_to_string(
            "emails/order_confirmation_email.html",
            {
                "order": order,
                "order_url": order_url,
            }
        )

        email = EmailMessage(
            subject,
            html_content,
            settings.DEFAULT_FROM_EMAIL,
            [order.email]
        )
        email.content_subtype = "html"

        # ✅ Générer et attacher PDF
        pdf_path = generate_invoice_pdf(order)

        if pdf_path and os.path.exists(pdf_path):
            email.attach_file(pdf_path)

        email.send(fail_silently=False)

        # ✅ Nettoyage fichier
        if pdf_path and os.path.exists(pdf_path):
            os.remove(pdf_path)

        print(f"✅ Email client + facture envoyé à {order.email}")

    except Exception as e:
        print(f"❌ Erreur email client: {e}")


# ✅ EMAIL ADMIN
def send_new_order_admin_email(order):
    if not getattr(settings, 'ADMIN_EMAIL', None):
        return

    try:
        subject = f"🛒 Nouvelle commande #{order.id} - {order.total_price} FCFA"

        html_content = render_to_string(
            "emails/admin_new_order_notification.html",
            {
                "order": order,
                "site_url": getattr(settings, 'SITE_URL', 'https://cinderaproduitsnaturels.com')
            }
        )

        email = EmailMessage(
            subject,
            html_content,
            settings.DEFAULT_FROM_EMAIL,
            [settings.ADMIN_EMAIL]
        )
        email.content_subtype = "html"
        email.send(fail_silently=False)

        print("✅ Email admin envoyé")

    except Exception as e:
        print(f"❌ Erreur email admin: {e}")

def generate_invoice_pdf(order):
    file_name = f"facture_{order.id}.pdf"
    file_path = os.path.join(settings.MEDIA_ROOT, file_name)
    
    doc = SimpleDocTemplate(
        file_path,
        pagesize=A4,
        rightMargin=1.5*cm, leftMargin=1.5*cm,
        topMargin=2*cm, bottomMargin=2*cm
    )

    elements = []
    styles = getSampleStyleSheet()

    # --- DÉFINITION DES COULEURS ---
    COLOR_GREEN = colors.HexColor('#014215')
    COLOR_ORANGE = colors.HexColor('#fd7e14')
    COLOR_LIGHT_GREY = colors.HexColor('#f8f9fa')
    COLOR_TEXT = colors.HexColor('#333333')
    COLOR_BORDER = colors.HexColor('#eeeeee')

    # --- STYLES PERSONNALISÉS ---
    styles.add(ParagraphStyle(
        name='CompanyTitle', 
        fontSize=15, 
        textColor=COLOR_GREEN,
        fontName='Helvetica-Bold', 
        spaceAfter=2
    ))
    styles.add(ParagraphStyle(
        name='InvoiceTitle', 
        fontSize=20, 
        textColor=COLOR_ORANGE,
        fontName='Helvetica-Bold', 
        alignment=TA_RIGHT
    ))
    styles.add(ParagraphStyle(
        name='SmallGrey', 
        fontSize=9, 
        textColor=colors.grey, 
        alignment=TA_LEFT
    ))
    styles.add(ParagraphStyle(
        name='TotalBig', 
        fontSize=16, 
        textColor=colors.white, # Texte blanc sur fond vert
        fontName='Helvetica-Bold', 
        alignment=TA_RIGHT
    ))
    styles.add(ParagraphStyle(
        name='SectionHeader', 
        fontSize=10, 
        textColor=COLOR_GREEN,
        fontName='Helvetica-Bold', 
        spaceBefore=10,
        spaceAfter=5
    ))

    # --- 1. EN-TÊTE (LOGO + TITRE FACTURE) ---
    logo_path = os.path.join(settings.STATIC_ROOT, "img/logo.jpg")
    
    # Gestion du logo (avec fallback si le fichier n'existe pas)
    if os.path.exists(logo_path):
        logo = Image(logo_path, width=3*cm, height=3*cm)
    else:
        logo = Paragraph("<b>CINDERA</b>", styles['CompanyTitle'])

    # Bloc gauche: Logo + Infos entreprise
    company_info = [
        logo,
        Spacer(1, 5),
        Paragraph("", styles['CompanyTitle']),
        Spacer(1, 5),
        Paragraph("", styles['SmallGrey']),
    ]

    # Bloc droit: Titre Facture + Numéro + Date
    # Bloc droit: Titre Facture + Numéro + Date
# --- 1. EN-TÊTE (LOGO + TITRE FACTURE) ---

# --- EN-TÊTE FACTURE ---
    if order.payment_method:
        payment_text = str(order.payment_method)
    else:
        payment_text = "Non défini"
    
    invoice_info = [
        Paragraph(f"FACTURE N° {order.id}", styles['InvoiceTitle']),
        Spacer(1, 15),
        Paragraph(
            f"Date: {order.created_at.strftime('%d/%m/%Y')}",
            ParagraphStyle('DateStyle', alignment=TA_RIGHT, textColor=colors.grey)
        ),
        Spacer(1, 5),
        Paragraph(
            f"Statut: {payment_text}",
            ParagraphStyle(
                'StatusStyle',
                alignment=TA_RIGHT,
                textColor=COLOR_GREEN,
                fontName='Helvetica-Bold'
            )
        )
    ]
    header_table = Table([[company_info, invoice_info]], colWidths=[11*cm, 7*cm])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
    ]))
    elements.append(header_table)
    
    # Ligne de séparation élégante
    elements.append(Spacer(1, 0.5*cm))
    line_table = Table([['']], colWidths=[18*cm])
    line_table.setStyle(TableStyle([('LINEABOVE', (0, 0), (-1, 0), 1, COLOR_GREEN)]))
    elements.append(line_table)
    elements.append(Spacer(1, 1*cm))

    # --- 2. ADRESSES (CLIENT & LIVRAISON) ---
    # Style pour le contenu des adresses
    addr_style = ParagraphStyle('AddrStyle', fontSize=10, leading=14, textColor=COLOR_TEXT)
    header_addr_style = ParagraphStyle('HeaderAddr', fontSize=9, textColor=COLOR_ORANGE, fontName='Helvetica-Bold')

    # Colonne Gauche : Facturation
    billing_content = [
        Paragraph("ADRESSE DE FACTURATION", header_addr_style),
        Spacer(1, 3),
        Paragraph(f"<b>{order.first_name} {order.last_name}</b>", addr_style),
        Paragraph(order.address, addr_style),
        Paragraph(f"{order.postal_code} {order.city}", addr_style),
    ]

    # Colonne Droite : Livraison
    shipping_content = [
        Paragraph("ADRESSE DE LIVRAISON", header_addr_style),
        Spacer(1, 3),
        Paragraph(f"<b>{order.first_name} {order.last_name}</b>", addr_style),
        Paragraph(order.address, addr_style),
        Paragraph(f"Zone: {order.zone}", addr_style),
    ]

    addr_table = Table([[billing_content, shipping_content]], colWidths=[9*cm, 9*cm])
    addr_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        # Bordures gauches colorées pour identifier les blocs
        ('LINEBEFORE', (0, 0), (0, -1), 3, COLOR_GREEN), # Barre verte gauche
        ('LEFTPADDING', (0, 0), (0, -1), 10),
        ('LINEBEFORE', (1, 0), (1, -1), 3, COLOR_ORANGE), # Barre orange gauche
        ('LEFTPADDING', (1, 0), (1, -1), 10),
    ]))
    elements.append(addr_table)
    elements.append(Spacer(1, 1.5*cm))

    # --- 3. TABLEAU DES ARTICLES ---
    # En-têtes
    table_header = [
        Paragraph("<b>Produit</b>", ParagraphStyle('th', textColor=colors.white, fontName='Helvetica-Bold')),
        Paragraph("<b>Qté</b>", ParagraphStyle('th', textColor=colors.white, alignment=TA_CENTER, fontName='Helvetica-Bold')),
        Paragraph("<b>Prix Unit.</b>", ParagraphStyle('th', textColor=colors.white, alignment=TA_RIGHT, fontName='Helvetica-Bold')),
        Paragraph("<b>Total</b>", ParagraphStyle('th', textColor=colors.white, alignment=TA_RIGHT, fontName='Helvetica-Bold')),
    ]
    table_data = [table_header]

    # Contenu
    for item in order.items.all():
        table_data.append([
            Paragraph(item.product_name, ParagraphStyle('cell', fontSize=10)),
            str(item.quantity),
            f"{item.price:,.0f} FCFA".replace(',', ' '),
            f"{item.total_price:,.0f} FCFA".replace(',', ' ')
        ])

    art_table = Table(table_data, colWidths=[8*cm, 2.5*cm, 3.5*cm, 4*cm])
    
    art_style = TableStyle([
        # Header Style
        ('BACKGROUND', (0, 0), (-1, 0), COLOR_GREEN),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('TOPPADDING', (0, 0), (-1, 0), 12),
        
        # Body Style
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
        ('ALIGN', (1, 1), (-1, -1), 'RIGHT'), # Aligner les chiffres à droite
        ('ALIGN', (1, 1), (1, -1), 'CENTER'), # Quantité au centre
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        
        # Padding du corps
        ('TOPPADDING', (0, 1), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 10),
        ('LEFTPADDING', (0, 0), (0, -1), 10),
        ('RIGHTPADDING', (-1, 0), (-1, -1), 10),

        # Grille / Lignes
        # Pas de grille complète, juste des lignes horizontales légères
        ('LINEBELOW', (0, 0), (-1, 0), 1, COLOR_GREEN), # Ligne sous le header
        ('LINEBELOW', (0, 1), (-1, -1), 0.5, COLOR_BORDER), # Lignes légères entre les rows
        
        # Zebra striping (Alternance de couleurs)
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, COLOR_LIGHT_GREY]),
    ])
    art_table.setStyle(art_style)
    elements.append(art_table)
    elements.append(Spacer(1, 1.5*cm))

    # --- 4. TOTAUX ---
    totals_data = [
        ["Sous-total HT", f"{order.subtotal:,.0f} FCFA".replace(',', ' ')],
    ]
    if order.discount_amount > 0:
        totals_data.append(["Remise", f"- {order.discount_amount:,.0f} FCFA".replace(',', ' ')])
    
    totals_data.append([
    "Livraison",
    f"{order.shipping_cost:,.0f} FCFA".replace(',', ' ')
    if order.shipping_cost > 0 else "Livraison à la charge du client"
])
    
    # Ligne finale du Total
    totals_data.append([
        Paragraph("<b>TOTAL TTC</b>", ParagraphStyle('TotalLabel', fontSize=14, textColor=colors.white, alignment=TA_RIGHT)),
        Paragraph(f"<b>{order.total_price:,.0f} FCFA</b>".replace(',', ' '), ParagraphStyle('TotalValue', fontSize=14, textColor=colors.white, alignment=TA_RIGHT))
    ])

    tot_table = Table(totals_data, colWidths=[11*cm, 7*cm])
    
    tot_style = TableStyle([
        # Style standard pour les lignes du haut
        ('ALIGN', (0, 0), (-1, -2), 'RIGHT'), # Tout à droite sauf la dernière ligne qu'on va customiser
        ('FONTNAME', (0, 0), (-1, -2), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -2), 11),
        ('TEXTCOLOR', (0, 0), (-1, -2), COLOR_TEXT),
        ('TOPPADDING', (0, 0), (-1, -2), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -2), 5),

        # Style spécial pour la ligne TOTAL (dernière ligne = index -1)
        ('BACKGROUND', (0, -1), (-1, -1), COLOR_GREEN), # Fond vert
        ('TEXTCOLOR', (0, -1), (-1, -1), colors.white), # Texte blanc
        ('TOPPADDING', (0, -1), (-1, -1), 12),
        ('BOTTOMPADDING', (0, -1), (-1, -1), 12),
        # On enlève l'alignement forcé pour laisser le ParagraphStyle gérer
    ])
    tot_table.setStyle(tot_style)
    elements.append(tot_table)

    # --- 5. PIED DE PAGE ---
    elements.append(Spacer(1, 3*cm))
    
    # Ligne séparatrice
    line_table_footer = Table([['']], colWidths=[18*cm])
    line_table_footer.setStyle(TableStyle([('LINEABOVE', (0, 0), (-1, 0), 1, colors.lightgrey)]))
    elements.append(line_table_footer)
    elements.append(Spacer(1, 0.3*cm))

    footer_style = ParagraphStyle('FooterStyle', fontSize=8, textColor=colors.grey, alignment=TA_CENTER, leading=12)
    elements.append(Paragraph(
        "CINDERA PRODUITS NATURELS - Prenons soin de nous!<br/>"
        "Sacré Coeur 3 Montagne Villa 9678 - Tel: 338425040 / 777431698<br/>"
        "NINEA: 010413946 / RCCM SN.DKR.2023.M.26514",
        footer_style
    ))

    doc.build(elements)
    return file_path
    

