from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import units
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
from django.conf import settings
import os

def generate_invoice_pdf(order):

    file_path = os.path.join(
        settings.MEDIA_ROOT,
        f"invoices/invoice_{order.id}.pdf"
    )

    os.makedirs(os.path.dirname(file_path), exist_ok=True)

    doc = SimpleDocTemplate(file_path)
    elements = []
    styles = getSampleStyleSheet()

    elements.append(Paragraph(f"Facture N° {order.id}", styles['Title']))
    elements.append(Spacer(1, 12))

    elements.append(Paragraph(
        f"Client : {order.first_name} {order.last_name}",
        styles['Normal']
    ))

    elements.append(Paragraph(
        f"Email : {order.email}",
        styles['Normal']
    ))

    elements.append(Spacer(1, 12))

    data = [["Produit", "Quantité", "Prix Unitaire", "Total"]]

    for item in order.items.all():
        data.append([
            item.product.name,
            str(item.quantity),
            f"{item.price} €",
            f"{item.get_cost()} €"
        ])

    data.append(["", "", "Total", f"{order.total_price} €"])

    table = Table(data, colWidths=[200, 80, 100, 100])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))

    elements.append(table)

    doc.build(elements)

    return f"invoices/invoice_{order.id}.pdf"
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect

def admin_or_manager_required(view_func):
    """
    Restreint l'accès aux utilisateurs avec rôle admin ou gestionnaire
    """
    def _wrapped_view(request, *args, **kwargs):
        if request.user.is_authenticated:
            if request.user.is_manager or request.user.is_admin_role:
                return view_func(request, *args, **kwargs)
            else:
                raise PermissionDenied("Vous n'avez pas la permission d'accéder à cette page.")
        else:
            return redirect('products:login')  # redirige si non connecté
    return _wrapped_view
