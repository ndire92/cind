import logging
from decimal import Decimal
import os
import json
import traceback
from django.http import FileResponse, HttpResponse

import requests
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.core.mail import EmailMessage
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db import transaction
from django.db.models import Q, Sum, Count, Min, Max
from django.http import JsonResponse, HttpResponse, FileResponse
from django.shortcuts import render, redirect, get_object_or_404, reverse
from django.template.loader import render_to_string
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from urllib3 import request
from django.template.loader import render_to_string
from django.conf import settings
import os
# ReportLab imports
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors

# Imports locaux
from .decorators import admin_or_manager_required
from .models import (
    Banner, Product, Category, Order, OrderItem, ProductImage, ShippingZone,
    NewsletterSubscriber, PaymentMethod, Coupon, ShopInfo, BlogPost, Feature, Feature1, Video,
    User, Transaction, SiteSettings, Feature_about, TeamMember, StaticPage
)
from .forms import (
    AboutSettingsForm, BannerForm, NewsletterSettingsForm, PaymentMethodForm, 
    WellnessSettingsForm, SiteSettingsForm, ProductForm, ProductImageFormSet, 
    OrderCreateForm, PromoSettingsForm, ShippingZoneForm, UserRegistrationForm, 
    ShopInfoForm, BlogPostForm, CategoryForm, FeatureForm, FeatureForm1, VideoForm, 
    TeamMemberForm, FeatureaboutForm, StaticPageForm
)

logger = logging.getLogger(__name__)

# ============================================================================
# HELPERS
# ============================================================================

def is_manager(user):
    return user.is_authenticated and (user.is_manager() or user.is_admin_role())

def get_cart(request):
    return request.session.get('cart', {})

# --- FONCTIONS EMAIL ---

def send_order_confirmation_email(order):
    """Envoie l'email de confirmation au CLIENT"""
    try:
        subject = f"Confirmation de votre commande #{order.id} 📝"
        html_content = render_to_string("emails/order_confirmation_email.html", {
            "order": order,
            "site_url": getattr(settings, 'SITE_URL', "http://127.0.0.1:8888")
        })
        email = EmailMessage(subject, html_content, settings.DEFAULT_FROM_EMAIL, [order.email])
        email.content_subtype = "html"
        email.send(fail_silently=False)
        print(f"✅ Email confirmation envoyé à {order.email}")
    except Exception as e:
        print(f"❌ Erreur envoi email confirmation: {e}")

def send_new_order_admin_email(order):
    """Envoie une notification au MARCHAND"""
    if not hasattr(settings, 'ADMIN_EMAIL'): return
    try:
        subject = f"🛒 Nouvelle Commande #{order.id} - {order.total_price} FCFA"
        html_content = render_to_string("emails/admin_new_order_notification.html", {
            "order": order,
            "site_url": getattr(settings, 'SITE_URL', "http://127.0.0.1:8888")
        })
        email = EmailMessage(subject, html_content, settings.DEFAULT_FROM_EMAIL, [settings.ADMIN_EMAIL])
        email.content_subtype = "html"
        email.send(fail_silently=False)
    except Exception as e:
        print(f"❌ Erreur envoi email admin: {e}")

def send_invoice_email(order):
    """Envoie la facture PDF lors de l'expédition"""
    subject = f"Votre commande #{order.id} a été expédiée 🚚"
    html_content = render_to_string("emails/invoice_email.html", {"order": order})
    email = EmailMessage(subject, html_content, settings.DEFAULT_FROM_EMAIL, [order.email])
    email.content_subtype = "html"
    
    pdf_path = generate_invoice_pdf(order)
    if pdf_path and os.path.exists(pdf_path):
        email.attach_file(pdf_path)
    email.send(fail_silently=False)

def generate_invoice_pdf(order):
    file_path = os.path.join(settings.MEDIA_ROOT, f"invoice_{order.id}.pdf")
    doc = SimpleDocTemplate(file_path)
    elements = []
    styles = getSampleStyleSheet()
    elements.append(Paragraph(f"Facture #{order.id}", styles["Title"]))
    elements.append(Spacer(1, 12))
    data = [["Produit", "Quantité", "Prix"]]
    for item in order.items.all():
        data.append([item.product_name, str(item.quantity), f"{item.price} FCFA"])
    table = Table(data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.grey),
        ('GRID', (0,0), (-1,-1), 1, colors.black),
    ]))
    elements.append(table)
    doc.build(elements)
    return file_path


# ============================================================================
# VUES PUBLIQUES (Frontend)
# ============================================================================

def index(request):
    shop_info = ShopInfo.get_instance()
    banners = Banner.objects.all()
    categories = Category.objects.all()
    products = Product.objects.filter(available=True)
    features = Feature.objects.filter(is_active=True)[:3]
    featured_video = Video.objects.filter(is_active=True).first()
    
    category_id = request.GET.get('category')
    active_category = None
    if category_id:
        active_category = get_object_or_404(Category, id=category_id)
        products = products.filter(category=active_category)
    
    featured_products = products[:4]
    posts = BlogPost.objects.filter(is_active=True)[:3]
    featured_post = posts.first()
    site_settings = SiteSettings.objects.first()

    return render(request, 'shop/index.html', {
        'shop_info': shop_info, 'products': featured_products, 'posts': posts,
        'featured_post': featured_post, 'banners': banners, 'categories': categories,
        'current_category': active_category, 'settings': site_settings,
        'features': features, 'featured_video': featured_video,
    })

def shop(request):
    categories = Category.objects.all()
    category_id = request.GET.get('category')
    current_category = None
    products = Product.objects.filter(available=True)
    if category_id:
        current_category = get_object_or_404(Category, id=category_id)
        products = products.filter(category=current_category)
    
    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')
    if min_price: products = products.filter(price_ht__gte=min_price)
    if max_price: products = products.filter(price_ht__lte=max_price)
    
    price_range = products.aggregate(min_price=Min('price_ht'), max_price=Max('price_ht'))
    return render(request, 'shop/shop.html', {
        'categories': categories, 'products': products, 'current_category': current_category,
        'price_range': price_range, 'selected_min_price': min_price, 'selected_max_price': max_price,
    })

def product_list(request):
    return shop(request)

def category_list(request, slug):
    category = get_object_or_404(Category, slug=slug)
    products = Product.objects.filter(category=category, available=True)
    return render(request, 'shop/category.html', {'category': category, 'products': products})

def product_detail(request, id, slug):
    product = get_object_or_404(Product, id=id, slug=slug, available=True)
    related_products = Product.objects.filter(category=product.category).exclude(id=product.id)[:4]
    return render(request, 'shop/product_detail.html', {'product': product, 'related_products': related_products})

# --- Auth & Profile ---
def register_view(request):
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Inscription réussie !")
            return redirect('products:shop')
    else:
        form = UserRegistrationForm()
    return render(request, 'shop/auth/register.html', {'form': form})

def login_view(request):
    return LoginView.as_view(template_name='shop/auth/login.html')(request)

def logout_view(request):
    logout(request)
    return redirect('products:shop')

@login_required
def profile(request):
    orders = request.user.orders.all()
    return render(request, 'shop/auth/profile.html', {'orders': orders})

# --- Static Pages ---
def about_page(request):
    shop_info = ShopInfo.get_instance()
    fea = Feature_about.objects.filter(is_active=True)[:3]
    team_members = TeamMember.objects.all()
    return render(request, 'shop/about.html', {'shop_info': shop_info, 'fea': fea, 'team_members': team_members})

def bien_etre(request):
    config = ShopInfo.get_instance()
    features1 = Feature1.objects.filter(is_active=True)[:3]
    
    video_list = Video.objects.filter(is_active=True).order_by('-created_at')
    paginator_video = Paginator(video_list, 3)
    videos = paginator_video.get_page(request.GET.get('video_page'))

    post_list = BlogPost.objects.filter(is_active=True).order_by('-created_at')
    blog_posts = Paginator(post_list, 3).get_page(request.GET.get('blog_page'))

    return render(request, 'shop/bien_etre.html', {
        'config': config, 'features1': features1, 'videos': videos, 'blog_posts': blog_posts,
    })

def post_detail(request, slug):
    post = get_object_or_404(BlogPost, slug=slug, is_active=True)
    return render(request, 'shop/blog_detail.html', {'post': post, 'config': ShopInfo.get_instance()})

def static_page_view(request, slug):
    page = get_object_or_404(StaticPage, slug=slug)
    return render(request, 'shop/static_page.html', {'page': page})

def livraison_view(request): return render(request, "dashboard/pages/livraison.html")
def conditions_view(request): return render(request, "dashboard/pages/conditions.html")
def confidentialite_view(request): return render(request, "dashboard/pages/confidentialite.html")

# --- Cart ---
def cart_detail(request):
    cart = get_cart(request)
    items, total = [], Decimal('0.00')
    for product_id, item_data in cart.items():
        product = get_object_or_404(Product, id=product_id)
        price = Decimal(item_data.get('price', product.price_ht))
        qty = int(item_data.get('quantity', 0))
        items.append({'product': product, 'quantity': qty, 'price': price, 'total': price * qty})
        total += price * qty
    return render(request, 'shop/cart/detail.html', {'items': items, 'total': total})

def cart_add(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    cart = get_cart(request)
    quantity = int(request.POST.get('quantity', 1))
    pid = str(product_id)
    cart[pid] = {'quantity': cart.get(pid, {}).get('quantity', 0) + quantity, 'price': str(product.price_ht)}
    request.session['cart'] = cart
    messages.success(request, "Produit ajouté au panier.")
    return redirect('products:cart_detail')

def cart_remove(request, product_id):
    cart = get_cart(request)
    if str(product_id) in cart: del cart[str(product_id)]
    request.session['cart'] = cart
    return redirect('products:cart_detail')

def cart_update(request, product_id):
    cart = get_cart(request)
    quantity = int(request.POST.get('quantity', 0))
    pid = str(product_id)
    if quantity > 0 and pid in cart: cart[pid]['quantity'] = quantity
    elif pid in cart: del cart[pid]
    request.session['cart'] = cart
    return redirect('products:cart_detail')

# --- Newsletter ---
def newsletter_subscribe(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        if email:
            _, created = NewsletterSubscriber.objects.get_or_create(email=email)
            msg = "Merci ! Vous êtes inscrit." if created else "Vous êtes déjà inscrit."
            messages.success(request, msg)
        return redirect(request.META.get('HTTP_REFERER', 'home'))
    return redirect('home')

# ============================================================================
# COMMANDE & PAIEMENT
# ============================================================================

def order_create(request):
    cart = get_cart(request)
    if not cart: return redirect('products:shop')
    
    cart_total = Decimal('0.00')
    for item in cart.values(): cart_total += Decimal(item['price']) * int(item['quantity'])

    if request.method == 'POST':
        form = OrderCreateForm(request.POST, user=request.user)
        if form.is_valid():
            try:
                with transaction.atomic():
                    order = form.save(commit=False)
                    if request.user.is_authenticated: order.user = request.user
                    
                    payment_method = form.cleaned_data.get('payment_method')
                    order.payment_method = payment_method
                    order.payment_fee = payment_method.extra_fee if payment_method else Decimal('0.00')

                    subtotal = Decimal('0.00')
                    items_to_create = []
                    for product_id, item_data in cart.items():
                        product = get_object_or_404(Product, id=product_id)
                        price = Decimal(item_data['price'])
                        qty = int(item_data['quantity'])
                        subtotal += price * qty
                        items_to_create.append(OrderItem(product=product, product_name=product.name, price=price, quantity=qty))

                    order.subtotal = subtotal
                    order.vat_rate = Decimal('0.00')  # TVA mise à 0
                    order.vat_amount = (subtotal * order.vat_rate) / Decimal('100')

                    # Livraison
                    zone_code = form.cleaned_data.get('zone')
                    shipping_cost, found_zone = Decimal('0.00'), None
                    for z in ShippingZone.objects.all():
                        if zone_code in z.get_zone_codes(): found_zone = z; break
                    if found_zone:
                        shipping_cost = Decimal('0.00') if found_zone.free_shipping else found_zone.price
                        order.shipping_zone = found_zone
                        if hasattr(order, 'shipping_note') and hasattr(found_zone, 'note'):
                            order.shipping_note = found_zone.note or ""
                    order.shipping_cost = shipping_cost

                    # Remises
                    discount_rate = Decimal('0.00')
                    if request.user.is_authenticated:
                        if not Order.objects.filter(user=request.user).exists():
                            discount_rate = Decimal('15.00')
                            messages.success(request, "🎉 Bienvenue ! Remise de 15% appliquée.")
                        elif NewsletterSubscriber.objects.filter(email=request.user.email).exists():
                            discount_rate = Decimal('10.00')
                            messages.success(request, "💌 Remise de 10% appliquée.")
                    
                    auto_disc = (subtotal * discount_rate) / Decimal('100')
                    coupon_disc = Decimal('0.00')
                    coupon = form.cleaned_data.get('coupon')
                    if coupon and coupon.active and coupon.valid_from <= timezone.now() <= coupon.valid_to:
                        coupon_disc = (subtotal * coupon.discount_percent) / Decimal('100')
                        messages.info(request, f"Code promo '{coupon.code}' appliqué.")

                    order.discount_amount = auto_disc + coupon_disc
                    order.total_price = order.subtotal + order.vat_amount + order.shipping_cost + order.payment_fee - order.discount_amount
                    order.payment_status = Order.PaymentStatus.PENDING
                    order.save()

                    for item in items_to_create: item.order = order
                    OrderItem.objects.bulk_create(items_to_create)
                    request.session['cart'] = {}

                    # Redirection & Envoi Email
                    pm_slug = payment_method.slug if payment_method else None

                    if pm_slug == "paydunya":
                        return redirect("products:paydunya_init", order_id=order.id)
                    if order.payment_method.slug == "dexpay":
                        return redirect("products:dexpay_init", order.id)


                    # Paiement hors ligne (ex : cash livraison)
                    transaction.on_commit(lambda o=order: send_order_confirmation_email(o))
                    transaction.on_commit(lambda o=order: send_new_order_admin_email(o))

                    return redirect("products:order_confirmation", order_id=order.id)

            except Exception as e:
                logger.error(f"Erreur création commande: {e}")
                messages.error(request, "Erreur lors de la création de la commande.")
                return render(request, 'shop/orders/create.html', {'form': form, 'total': cart_total})
    
    else:
        form = OrderCreateForm(user=request.user)
    
    return render(request, 'shop/orders/create.html', {'form': form, 'total': cart_total})

def order_confirmation(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    return render(request, 'shop/orders/confirmation.html', {'order': order})



def shipping_cost_ajax(request):
    zone_code = request.GET.get('zone')
    cost = Order.get_shipping_cost_by_zone(zone_code)
    return JsonResponse({'cost': str(cost)})



from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.enums import TA_RIGHT, TA_LEFT, TA_CENTER
from django.conf import settings
import os

def generate_invoice_pdf(order):
    file_name = f"facture_{order.id}.pdf"
    file_path = os.path.join(settings.MEDIA_ROOT, file_name)
    
    doc = SimpleDocTemplate(file_path, pagesize=A4,
                            rightMargin=2*cm, leftMargin=2*cm,
                            topMargin=2*cm, bottomMargin=2*cm)

    elements = []
    styles = getSampleStyleSheet()

    # Styles personnalisés
    styles.add(ParagraphStyle(name='CompanyTitle', fontSize=24, textColor=colors.HexColor('#014215'), fontName='Helvetica-Bold', spaceAfter=10))
    styles.add(ParagraphStyle(name='InvoiceTitle', fontSize=36, textColor=colors.HexColor('#fd7e14'), fontName='Helvetica-Bold', alignment=TA_RIGHT))
    styles.add(ParagraphStyle(name='Small', fontSize=9, textColor=colors.grey))
    styles.add(ParagraphStyle(name='Total', fontSize=14, textColor=colors.HexColor('#014215'), fontName='Helvetica-Bold', alignment=TA_RIGHT))
    
    # --- EN-TÊTE ---
    # Gauche : Logo / Nom
    company_info = [
        Paragraph("Cindera 🌿", styles['CompanyTitle']),
        Paragraph("Produits Naturels 100% Locaux", styles['Small']),
        Paragraph("Dakar, Sénégal", styles['Small']),
        Paragraph("Tel: +221 77 743 16 98", styles['Small']),
    ]
    
    # Droite : Titre Facture
    invoice_info = [
        Paragraph("FACTURE", styles['InvoiceTitle']),
        Spacer(1, 0.5*cm),
        Paragraph(f"N° {order.id}", styles['Normal']),
        Paragraph(f"Date: {order.created_at.strftime('%d/%m/%Y')}", styles['Normal']),
    ]

    # Tableau pour l'en-tête (Logo à gauche, Infos à droite)
    header_table = Table([[company_info, invoice_info]], colWidths=[10*cm, 6*cm])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 1*cm))

    # --- CLIENT ---
    client_data = [
        [Paragraph("<b>Facturer à :</b>", styles['Normal']), "", Paragraph("<b>Livrer à :</b>", styles['Normal']), ""],
        [order.first_name + " " + order.last_name, "", order.first_name + " " + order.last_name, ""],
        [order.address, "", order.address, ""],
        [f"{order.postal_code} {order.city}", "", f"Zone: {order.zone}", ""],
    ]
    
    client_table = Table(client_data, colWidths=[6*cm, 3*cm, 6*cm, 3*cm])
    client_table.setStyle(TableStyle([
        ('BOX', (0, 0), (0, -1), 1, colors.HexColor('#014215')), # Bordure gauche verte
        ('BOX', (2, 0), (2, -1), 1, colors.HexColor('#fd7e14')), # Bordure gauche orange
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f8f9fa')),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
        ('SPAN', (0, 1), (1, -1)), # Fusionne les cellules pour l'adresse
        ('SPAN', (2, 1), (3, -1)),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('RIGHTPADDING', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    elements.append(client_table)
    elements.append(Spacer(1, 1*cm))

    # --- TABLEAU DES ARTICLES ---
    table_data = [["Description", "Qté", "Prix Unitaire", "Total"]]
    
    for item in order.items.all():
        table_data.append([
            item.product_name,
            str(item.quantity),
            f"{item.price} FCFA",
            f"{item.total_price} FCFA"
        ])

    art_table = Table(table_data, colWidths=[8*cm, 2.5*cm, 4*cm, 4*cm])
    art_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#014215')), # Header vert
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
        ('ALIGN', (1, 1), (-1, -1), 'RIGHT'), # Chiffres à droite
        ('ALIGN', (0, 1), (0, -1), 'LEFT'),   # Texte à gauche
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
        
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('TOPPADDING', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
        ('TOPPADDING', (0, 1), (-1, -1), 8),
        
        ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f9f9f9')]), # Lignes alternées
    ]))
    elements.append(art_table)
    elements.append(Spacer(1, 1*cm))

    # --- TOTAUX ---
    totals_data = [
        ["Sous-total HT", f"{order.subtotal} FCFA"],
    ]
    
    if order.discount_amount > 0:
        totals_data.append(["Remise", f"- {order.discount_amount} FCFA"])
        
    totals_data.append(["Livraison", f"{order.shipping_cost} FCFA" if order.shipping_cost > 0 else "Gratuite"])
    totals_data.append(["", ""])
    totals_data.append(["Total TTC", f"{order.total_price} FCFA"])

    tot_table = Table(totals_data, colWidths=[10*cm, 6*cm])
    tot_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('FONTNAME', (0, 0), (-1, -2), 'Helvetica'),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, -1), (-1, -1), 14),
        ('TEXTCOLOR', (1, -1), (1, -1), colors.HexColor('#014215')), # Total en vert
        ('LINEABOVE', (0, -1), (-1, -1), 2, colors.HexColor('#014215')), # Ligne au-dessus du total
        ('TOPPADDING', (0, -1), (-1, -1), 10),
        ('BOTTOMPADDING', (0, -1), (-1, -1), 10),
    ]))
    elements.append(tot_table)

    # --- PIED DE PAGE ---
    elements.append(Spacer(1, 2*cm))
    styles.add(ParagraphStyle(name='Footer', fontSize=8, textColor=colors.grey, alignment=TA_CENTER))
    elements.append(Paragraph("Merci pour votre confiance !<br/>Cindera Produits Naturels • Sénégal", styles['Footer']))

    doc.build(elements)
    return file_path

def invoice_download(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    
    try:
        # On génère le PDF
        pdf_path = generate_invoice_pdf(order)
        
        if pdf_path and os.path.exists(pdf_path):
            # On renvoie le fichier au navigateur
            return FileResponse(
                open(pdf_path, 'rb'), 
                as_attachment=True, 
                filename=f"facture_{order.id}.pdf"
            )
        else:
            return HttpResponse("Erreur de génération", status=500)
            
    except Exception as e:
        print(f"Erreur PDF: {e}")
        return HttpResponse("Erreur serveur", status=500)

# --- PAIEMENT PAYDUNYA ---
# --- PAIEMENT PAYDUNYA ---
def paydunya_init(request, order_id):

    order = get_object_or_404(Order, id=order_id)

    if order.payment_status == Order.PaymentStatus.PAID:
        return redirect("products:order_confirmation", order_id=order.id)

    url = "https://app.paydunya.com/api/v1/checkout-invoice/create"

    headers = {
        "Content-Type": "application/json",
        "PAYDUNYA-MASTER-KEY": settings.PAYDUNYA_MASTER_KEY,
        "PAYDUNYA-PRIVATE-KEY": settings.PAYDUNYA_PRIVATE_KEY,
        "PAYDUNYA-TOKEN": settings.PAYDUNYA_TOKEN,
    }

    data = {
        "invoice": {
            "total_amount": float(order.total_price),
            "description": f"Commande #{order.id}",
        },
        "store": {
            "name": "Cindera",
            "website_url": "https://cinderaproduitsnaturels.com",
        },
        "actions": {
            "callback_url": f"https://cinderaproduitsnaturels.com/boutique/paydunya_callback/{order.id}/",
            "return_url": f"https://cinderaproduitsnaturels.com/boutique/payment/success/{order.id}/",
            "cancel_url": f"https://cinderaproduitsnaturels.com/boutique/order_cancelled/{order.id}/",
        },
    }

    try:
        resp = requests.post(url, json=data, headers=headers, timeout=30)
        result = resp.json()
    except Exception as e:
        logger.error(f"Erreur PayDunya : {e}")
        return redirect("products:checkout")

    if result.get("response_code") == "00":

        order.transaction_id = result.get("token")
        order.gateway = "paydunya"
        order.save()

        return redirect(result["response_text"])

    return redirect("products:checkout")
    


@csrf_exempt
def paydunya_callback(request, order_id):

    order = get_object_or_404(Order, id=order_id)

    if order.payment_status == Order.PaymentStatus.PAID:
        return JsonResponse({"status": "already_paid"})

    verify_url = "https://app.paydunya.com/api/v1/checkout-invoice/confirm/"

    headers = {
        "Content-Type": "application/json",
        "PAYDUNYA-MASTER-KEY": settings.PAYDUNYA_MASTER_KEY,
        "PAYDUNYA-PRIVATE-KEY": settings.PAYDUNYA_PRIVATE_KEY,
        "PAYDUNYA-TOKEN": settings.PAYDUNYA_TOKEN,
    }

    try:
        resp = requests.post(
            verify_url,
            json={"token": order.transaction_id},
            headers=headers,
            timeout=30
        )
        result = resp.json()

    except Exception as e:
        logger.error(f"Webhook PayDunya erreur : {e}")
        return JsonResponse({"status": "error"})

    if result.get("invoice_status") == "completed":

        order.payment_status = Order.PaymentStatus.PAID
        order.save()

        Transaction.objects.create(
            order=order,
            external_reference=order.transaction_id,
            description=f"Paiement PayDunya #{order.id}",
            type=Transaction.TypeChoices.INCOME,
            amount=order.total_price,
            status="completed",
        )

        send_order_confirmation_email(order)
        send_new_order_admin_email(order)

    return JsonResponse({"status": "ok"})



def payment_success(request, order_id):
    """
    Page affichée après paiement réussi.
    Met à jour le statut de la commande et crée la transaction si nécessaire.
    """
    order = get_object_or_404(Order, id=order_id)

    # Si pas de transaction, retourne au checkout
    if not order.transaction_id:
        logger.warning(f"Commande {order.id} sans transaction_id")
        return redirect("products:checkout")

    # Si la commande est déjà payée, afficher directement le template succès
    if order.payment_status == Order.PaymentStatus.PAID:
        return render(request, "shop/orders/payment_success.html", {"order": order})

    # Vérification selon la passerelle
    if hasattr(order, "gateway"):
        if order.gateway == "paydunya":
            # Vérification PayDunya via API
            try:
                headers = {
                    "Content-Type": "application/json",
                    "PAYDUNYA-MASTER-KEY": settings.PAYDUNYA_MASTER_KEY,
                    "PAYDUNYA-PRIVATE-KEY": settings.PAYDUNYA_PRIVATE_KEY,
                    "PAYDUNYA-TOKEN": settings.PAYDUNYA_TOKEN,
                }
                resp = requests.post(
                    "https://app.paydunya.com/api/v1/checkout-invoice/confirm/",
                    json={"token": order.transaction_id},
                    headers=headers,
                    timeout=30
                )
                result = resp.json()
                if result.get("invoice_status") == "completed":
                    order.payment_status = Order.PaymentStatus.PAID
                    order.save()
            except Exception as e:
                logger.error(f"Erreur vérification PayDunya : {e}")

        elif order.gateway == "dexpay":
            # Pour DexPay, considérer payé si transaction existante
            if order.transaction_id:
                order.payment_status = Order.PaymentStatus.PAID
                order.save()

    else:
        # Si gateway non définie, considérer comme payé
        order.payment_status = Order.PaymentStatus.PAID
        order.save()

    # Créer la transaction si elle n’existe pas
    if not Transaction.objects.filter(external_reference=order.transaction_id).exists():
        Transaction.objects.create(
            order=order,
            external_reference=order.transaction_id,
            description=f"Paiement {getattr(order, 'gateway', 'Autre').capitalize()} #{order.id}",
            type=Transaction.TypeChoices.INCOME,
            amount=order.total_price,
            status=Transaction.StatusChoices.COMPLETED,
        )

    # Notifications
    send_order_confirmation_email(order)
    send_new_order_admin_email(order)

    # Afficher la page de succès
    return render(request, "shop/orders/payment_success.html", {"order": order})


@csrf_exempt
def dexpay_callback(request, order_id):
    """
    Webhook DexPay pour mise à jour automatique du statut de la commande.
    """
    try:
        data = json.loads(request.body)
        order = get_object_or_404(Order, id=order_id)

        status = data.get("status")
        if status == "success":
            order.payment_status = Order.PaymentStatus.PAID
        elif status == "failed":
            order.payment_status = Order.PaymentStatus.FAILED
        else:
            order.payment_status = Order.PaymentStatus.PENDING

        order.save()
        logger.info(f"Order {order.id} updated to {order.payment_status}")

        # Créer transaction si nécessaire
        if order.payment_status == Order.PaymentStatus.PAID:
            if not Transaction.objects.filter(external_reference=order.transaction_id).exists():
                Transaction.objects.create(
                    order=order,
                    external_reference=order.transaction_id,
                    description=f"Paiement DexPay #{order.id}",
                    type=Transaction.TypeChoices.INCOME,
                    amount=order.total_price,
                    status=Transaction.StatusChoices.COMPLETED,
                )
                send_order_confirmation_email(order)
                send_new_order_admin_email(order)

        return JsonResponse({"message": "Order updated", "status": order.payment_status})

    except Exception as e:
        logger.error(f"DexPay webhook error: {e}")
        return JsonResponse({"error": str(e)}, status=400)
        
def order_cancelled(request, order_id):

    order = get_object_or_404(Order, id=order_id)

    order.payment_status = Order.PaymentStatus.FAILED
    order.save()

    logger.info(f"Commande {order.id} annulée")

    return render(request, 'shop/orders/order_cancelled.html', {'order': order})

from django.shortcuts import get_object_or_404, redirect
from .utils import DexPayClient
import logging

logger = logging.getLogger(__name__)

def dexpay_init(request, order_id):

    order = get_object_or_404(Order, id=order_id)
    client = DexPayClient()

    response = client.create_checkout(
        reference=f"ORDER-{order.id}",
        item_name=f"Commande #{order.id}",
        amount=float(order.total_price),
        currency="XOF",
        countryISO="SN",
        webhook_url=f"https://cinderaproduitsnaturels.com/boutique/dexpay_callback/{order.id}/",
        success_url=f"https://cinderaproduitsnaturels.com/boutique/payment/success/{order.id}/",
        failure_url=f"https://cinderaproduitsnaturels.com/boutique/order_cancelled/{order.id}/",
    )

    logger.info(f"DexPay response: {response}")

    payment_url = response.get("data", {}).get("payment_url")

    if payment_url:

        order.gateway = "dexpay"
        order.transaction_id = response.get("data", {}).get("reference")
        order.save()

        return redirect(payment_url)

    logger.error(f"DexPay error: {response}")
    return redirect("products:checkout")



def payment_success(request, order_id):

    order = get_object_or_404(Order, id=order_id)

    if not order.transaction_id:
        return redirect("products:checkout")

    if order.payment_status == Order.PaymentStatus.PAID:
        return render(request, "shop/orders/payment_success.html", {"order": order})

    if order.gateway == "paydunya":
        # vérification PayDunya
        pass

    elif order.gateway == "dexpay":
        # DexPay : le webhook peut ne pas passer, donc on marque ici comme payé
        if order.payment_status != Order.PaymentStatus.PAID:
            order.payment_status = Order.PaymentStatus.PAID
            order.save()

    if not Transaction.objects.filter(external_reference=order.transaction_id).exists():

        Transaction.objects.create(
            order=order,
            external_reference=order.transaction_id,
            description=f"Paiement {order.gateway}",
            type=Transaction.TypeChoices.INCOME,
            amount=order.total_price,
            status="completed",
        )

    send_order_confirmation_email(order)
    send_new_order_admin_email(order)

    return render(request, "shop/orders/payment_success.html", {"order": order})



# ============================================================================
# DASHBOARD VIEWS
# ============================================================================

@login_required
@admin_or_manager_required
def dashboard_overview(request):
    ctx = {
        'orders': Order.objects.count(),
        'revenue': Order.objects.filter(payment_status='paid').aggregate(Sum('total_price'))['total_price__sum'] or 0,
        'products': Product.objects.count(),
        'recent_orders': Order.objects.all().order_by('-created_at')[:5],
    }
    return render(request, 'dashboard/overview.html', ctx)

# Products CRUD
@login_required
@admin_or_manager_required
def dashboard_products(request): 
    return render(request, 'dashboard/products/list.html', {'products': Product.objects.all()})

@login_required
@admin_or_manager_required
def add_product(request):
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)
        formset = ProductImageFormSet(request.POST, request.FILES)
        if form.is_valid() and formset.is_valid():
            product = form.save()
            formset.instance = product
            formset.save()
            messages.success(request, "Produit ajouté.")
            return redirect('dashboard:products')
    else:
        form, formset = ProductForm(), ProductImageFormSet()
    return render(request, 'dashboard/products/form.html', {'form': form, 'formset': formset})

@login_required
@admin_or_manager_required
def edit_product(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, instance=product)
        formset = ProductImageFormSet(request.POST, request.FILES, instance=product)
        if form.is_valid() and formset.is_valid():
            form.save(); formset.save()
            messages.success(request, "Produit mis à jour.")
            return redirect('dashboard:products')
    else:
        form, formset = ProductForm(instance=product), ProductImageFormSet(instance=product)
    return render(request, 'dashboard/products/form.html', {'form': form, 'formset': formset})

@login_required
@admin_or_manager_required
def delete_product(request, pk):
    get_object_or_404(Product, id=pk).delete()
    return redirect('dashboard:products')

# Orders
@login_required
@admin_or_manager_required
def dashboard_orders(request): 
    return render(request, 'dashboard/orders/list.html', {'orders': Order.objects.all()})

@login_required
@admin_or_manager_required
def order_detail(request, order_id): 
    return render(request, 'dashboard/orders/detail.html', {'order': get_object_or_404(Order, id=order_id)})

@login_required
@admin_or_manager_required
@transaction.atomic
def update_order_status(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    if request.method == "POST" and not order.is_shipped:
        order.is_shipped = True
        order.save()
        send_invoice_email(order)
        messages.success(request, "Commande expédiée et facture envoyée.")
    return redirect('dashboard:order_detail', order_id=order.id)

# Settings (Banner, Promo, Shipping, Payment, etc.)

@login_required
def banner_list(request): return render(request, "dashboard/banner_list.html", {"banners": Banner.objects.all()})
@login_required
def banner_create(request):
    if request.method == "POST":
        form = BannerForm(request.POST, request.FILES)
        if form.is_valid(): form.save(); messages.success(request, "Ajouté ✅"); return redirect("dashboard:banner_list")
    else: form = BannerForm()
    return render(request, "dashboard/banner_form.html", {"form": form})


@login_required
def banner_update(request, pk):
    b = get_object_or_404(Banner, pk=pk)
    if request.method == "POST":
        form = BannerForm(request.POST, request.FILES, instance=b)
        if form.is_valid(): form.save(); messages.success(request, "Mis à jour ✅"); return redirect("dashboard:banner_list")
    else: form = BannerForm(instance=b)
    return render(request, "dashboard/banner_form.html", {"form": form})


@login_required
def banner_delete(request, pk):
    get_object_or_404(Banner, pk=pk).delete()
    messages.success(request, "Supprimé ❌"); return redirect("dashboard:banner_list")

@login_required
@admin_or_manager_required
def shop_promo(request):
    i = ShopInfo.get_instance()
    if request.method == 'POST':
        form = PromoSettingsForm(request.POST, request.FILES, instance=i)
        if form.is_valid(): form.save(); messages.success(request, "Mis à jour !"); return redirect('dashboard:shop_promo')
    else: form = PromoSettingsForm(instance=i)
    return render(request, 'dashboard/settings/promo.html', {'form': form})

@login_required
@admin_or_manager_required
def shop_wellness(request):
    i = ShopInfo.get_instance()
    if request.method == 'POST':
        form = WellnessSettingsForm(request.POST, request.FILES, instance=i)
        if form.is_valid(): form.save(); messages.success(request, "Bien-être mis à jour !"); return redirect('dashboard:shop_wellness')
    else: form = WellnessSettingsForm(instance=i)
    return render(request, 'dashboard/settings/wellness.html', {'form': form})

@login_required
@admin_or_manager_required
def wellness_hub(request): return render(request, 'dashboard/wellness_hub.html')

# Shipping
@login_required
@admin_or_manager_required
def shipping_zones(request): return render(request, 'dashboard/settings/shipping_list.html', {'zones': ShippingZone.objects.all()})
@login_required
@admin_or_manager_required
def add_shipping_zone(request):
    if request.method == 'POST':
        form = ShippingZoneForm(request.POST)
        if form.is_valid(): form.save(); messages.success(request, "Zone ajoutée."); return redirect('dashboard:shipping_zones')
    else: form = ShippingZoneForm()
    return render(request, 'dashboard/settings/shipping_form.html', {'form': form})
@login_required
@admin_or_manager_required
def edit_shipping_zone(request, zone_id):
    z = get_object_or_404(ShippingZone, id=zone_id)
    if request.method == 'POST':
        form = ShippingZoneForm(request.POST, instance=z)
        if form.is_valid(): form.save(); messages.success(request, "Zone mise à jour."); return redirect('dashboard:shipping_zones')
    else: form = ShippingZoneForm(instance=z)
    return render(request, 'dashboard/settings/shipping_form.html', {'form': form})
@login_required
@admin_or_manager_required
def delete_shipping_zone(request, pk):
    get_object_or_404(ShippingZone, id=pk).delete()
    messages.success(request, "Zone supprimée."); return redirect('dashboard:shipping_zones')

# Payment Methods
@login_required
@admin_or_manager_required
def payment_methods(request): return render(request, 'dashboard/settings/payment_list.html', {'methods': PaymentMethod.objects.all()})
@login_required
@admin_or_manager_required
def add_payment_method(request):
    if request.method == 'POST':
        form = PaymentMethodForm(request.POST)
        if form.is_valid(): form.save(); messages.success(request, "Ajouté."); return redirect('dashboard:payment_methods')
    else: form = PaymentMethodForm()
    return render(request, 'dashboard/settings/payment_form.html', {'form': form})

@login_required
@admin_or_manager_required
def edit_payment_method(request, method_id):
    m = get_object_or_404(PaymentMethod, id=method_id)
    if request.method == 'POST':
        form = PaymentMethodForm(request.POST, instance=m)
        if form.is_valid(): form.save(); messages.success(request, "Mis à jour."); return redirect('dashboard:payment_methods')
    else: form = PaymentMethodForm(instance=m)
    return render(request, 'dashboard/settings/payment_form.html', {'form': form})

def delete_payment_method(request, pk):
    method = get_object_or_404(PaymentMethod, pk=pk)
    if request.method == "POST":
        method.delete()
        messages.success(request, f"Le moyen de paiement '{method.name}' a été supprimé.")
        return redirect(reverse('dashboard:payment_methods'))
    return redirect(reverse('dashboard:payment_methods'))
# Blog CRUD
@login_required
@admin_or_manager_required
def blog_list_view(request): return render(request, 'dashboard/blog/list.html', {'posts': BlogPost.objects.all()})
@login_required
@admin_or_manager_required
def blog_create_view(request):
    if request.method == 'POST':
        form = BlogPostForm(request.POST, request.FILES)
        if form.is_valid(): form.save(); return redirect('dashboard:blog_posts')
    else: form = BlogPostForm()
    return render(request, 'dashboard/blog/form.html', {'form': form})
@login_required
@admin_or_manager_required
def blog_update_view(request, pk):
    p = get_object_or_404(BlogPost, id=pk)
    if request.method == 'POST':
        form = BlogPostForm(request.POST, request.FILES, instance=p)
        if form.is_valid(): form.save(); return redirect('dashboard:blog_posts')
    else: form = BlogPostForm(instance=p)
    return render(request, 'dashboard/blog/form.html', {'form': form})
@login_required
@admin_or_manager_required
def blog_delete_view(request, pk):
    get_object_or_404(BlogPost, id=pk).delete()
    return redirect('dashboard:blog_posts')

# Video CRUD
@login_required
@admin_or_manager_required
def video_list_view(request):
    videos = Video.objects.filter(Q(video_file__isnull=False) | Q(video_url__isnull=False)).exclude(video_file='').exclude(video_url='').order_by('-created_at')
    return render(request, 'dashboard/videos/list.html', {'videos': videos})
@login_required
@admin_or_manager_required
def video_create_view(request):
    if request.method == 'POST':
        form = VideoForm(request.POST, request.FILES)
        if form.is_valid(): form.save(); messages.success(request, "Vidéo ajoutée."); return redirect('dashboard:video_list')
    else: form = VideoForm()
    return render(request, 'dashboard/videos/form.html', {'form': form})
@login_required
@admin_or_manager_required
def video_update_view(request, pk):
    v = get_object_or_404(Video, pk=pk)
    if request.method == 'POST':
        form = VideoForm(request.POST, request.FILES, instance=v)
        if form.is_valid(): form.save(); messages.success(request, "Vidéo mise à jour."); return redirect('dashboard:video_list')
    else: form = VideoForm(instance=v)
    return render(request, 'dashboard/videos/form.html', {'form': form})

@login_required
@admin_or_manager_required
def video_delete_view(request, pk):
    v = get_object_or_404(Video, pk=pk)
    if request.method == "POST": v.delete(); messages.success(request, "Vidéo supprimée."); return redirect('dashboard:video_list')
    return render(request, 'dashboard/videos/confirm_delete.html', {'video': v})
def video_detail(request, slug):
    video = get_object_or_404(Video, slug=slug, is_active=True)

    return render(request, 'dashboard/videos/video_detail.html', {
        'video': video
    })
# Categories (CBV)
class CategoryListView(ListView): model = Category; template_name = 'dashboard/categories/list.html'; context_object_name = 'categories'
class CategoryCreateView(CreateView): model = Category; form_class = CategoryForm; template_name = 'dashboard/categories/form.html'; success_url = reverse_lazy('dashboard:category_list')
class CategoryUpdateView(UpdateView): model = Category; form_class = CategoryForm; template_name = 'dashboard/categories/form.html'; success_url = reverse_lazy('dashboard:category_list'); slug_url_kwarg = 'slug'; slug_field = 'slug'
class CategoryDeleteView(DeleteView): model = Category; template_name = 'dashboard/categories/confirm_delete.html'; success_url = reverse_lazy('dashboard:category_list'); slug_url_kwarg = 'slug'; slug_field = 'slug'

# Settings Misc
@login_required
@admin_or_manager_required
def dashboard_accounting(request): return render(request, 'dashboard/accounting.html')
@login_required
@admin_or_manager_required
def export_transactions_csv(request): return HttpResponse("Export CSV non implémenté")
@login_required
@admin_or_manager_required
def dashboard_settings(request): return render(request, 'dashboard/settings/settings.html')
@login_required
@admin_or_manager_required
def billing_settings(request): return HttpResponse("Paramètres facturation")

# Site Settings
@login_required
def site_settings_list(request): return render(request, "dashboard/settings/site_settings_list.html", {"settings": SiteSettings.objects.all()})
@login_required
def site_settings_add(request):
    if request.method == "POST":
        form = SiteSettingsForm(request.POST)
        if form.is_valid(): form.save(); messages.success(request, "Ajouté."); return redirect("dashboard:site_settings_list")
    else: form = SiteSettingsForm()
    return render(request, "dashboard/settings/site_settings.html", {"form": form})
@login_required
def site_settings_edit(request, pk):
    s = get_object_or_404(SiteSettings, pk=pk)
    if request.method == "POST":
        form = SiteSettingsForm(request.POST, instance=s)
        if form.is_valid(): form.save(); messages.success(request, "Mis à jour."); return redirect("dashboard:site_settings_list")
    else: form = SiteSettingsForm(instance=s)
    return render(request, "dashboard/settings/site_settings_edit.html", {"form": form})
@login_required
def site_settings_delete(request, pk):
    get_object_or_404(SiteSettings, pk=pk).delete()
    messages.success(request, "Supprimé."); return redirect("dashboard:site_settings_list")

# Features
@login_required
@admin_or_manager_required
def feature_list(request): return render(request, 'dashboard/features/list.html', {'features': Feature.objects.all()})
@login_required
@admin_or_manager_required
def feature_create(request):
    if request.method == 'POST':
        form = FeatureForm(request.POST)
        if form.is_valid(): form.save(); return redirect('dashboard:feature_list')
    else: form = FeatureForm()
    return render(request, 'dashboard/features/form.html', {'form': form})
@login_required
@admin_or_manager_required
def feature_update(request, pk):
    f = get_object_or_404(Feature, pk=pk)
    if request.method == 'POST':
        form = FeatureForm(request.POST, instance=f)
        if form.is_valid(): form.save(); return redirect('dashboard:feature_list')
    else: form = FeatureForm(instance=f)
    return render(request, 'dashboard/features/form.html', {'form': form})
@login_required
@admin_or_manager_required
def feature_delete(request, pk):
    f = get_object_or_404(Feature, pk=pk)
    if request.method == 'POST': f.delete(); return redirect('dashboard:feature_list')
    return render(request, 'dashboard/features/delete.html', {'feature': f})

# Feature 1
@login_required
@admin_or_manager_required
def feature_list1(request): return render(request, 'dashboard/features/liste1.html', {'features1': Feature1.objects.all()})
@login_required
@admin_or_manager_required
def feature_create1(request):
    if request.method == 'POST':
        form = FeatureForm1(request.POST)
        if form.is_valid(): form.save(); return redirect('dashboard:feature_list1')
    else: form = FeatureForm1()
    return render(request, 'dashboard/features/form1.html', {'form': form})
@login_required
@admin_or_manager_required
def feature_update1(request, pk):
    f = get_object_or_404(Feature1, pk=pk)
    if request.method == 'POST':
        form = FeatureForm1(request.POST, instance=f)
        if form.is_valid(): form.save(); return redirect('dashboard:feature_list1')
    else: form = FeatureForm1(instance=f)
    return render(request, 'dashboard/features/form1.html', {'form': form})
@login_required
@admin_or_manager_required
def feature_delete1(request, pk):
    f = get_object_or_404(Feature1, pk=pk)
    if request.method == 'POST': f.delete(); return redirect('dashboard:feature_list1')
    return render(request, 'dashboard/features/delete1.html', {'feature1': f})

# Feature About
@login_required
@admin_or_manager_required
def feature_about_list(request): return render(request, 'dashboard/feat/list.html', {'fea': Feature_about.objects.all()})
@login_required
@admin_or_manager_required
def feature_about_create(request):
    if request.method == 'POST':
        form = FeatureaboutForm(request.POST)
        if form.is_valid(): form.save(); return redirect('dashboard:feature_about_list')
    else: form = FeatureaboutForm()
    return render(request, 'dashboard/feat/form.html', {'form': form})
@login_required
@admin_or_manager_required
def feature_about_update(request, pk):
    f = get_object_or_404(Feature_about, pk=pk)
    if request.method == 'POST':
        form = FeatureaboutForm(request.POST, instance=f)
        if form.is_valid(): form.save(); return redirect('dashboard:feature_about_list')
    else: form = FeatureaboutForm(instance=f)
    return render(request, 'dashboard/feat/form.html', {'form': form})
@login_required
@admin_or_manager_required
def feature_about_delete(request, pk):
    f = get_object_or_404(Feature_about, pk=pk)
    if request.method == 'POST': f.delete(); return redirect('dashboard:feature_about_list')
    return render(request, 'dashboard/feat/delete.html', {'fea': f})

# About / Team
@login_required
@admin_or_manager_required
def a_settings_view(request):
    i = ShopInfo.get_instance()
    if request.method == 'POST':
        form = AboutSettingsForm(request.POST, instance=i)
        if form.is_valid(): form.save(); messages.success(request, "Mis à jour !"); return redirect('dashboard:ab_settings')
    else: form = AboutSettingsForm(instance=i)
    return render(request, 'dashboard/about/settings.html', {'form': form})
@login_required
@admin_or_manager_required
def team_list_view(request): return render(request, 'dashboard/about/team_list.html', {'members': TeamMember.objects.all()})
@login_required
@admin_or_manager_required
def team_add_view(request):
    if request.method == 'POST':
        form = TeamMemberForm(request.POST, request.FILES)
        if form.is_valid(): form.save(); messages.success(request, "Membre ajouté."); return redirect('dashboard:team_list')
    else: form = TeamMemberForm()
    return render(request, 'dashboard/about/team_form.html', {'form': form})
@login_required
@admin_or_manager_required
def team_edit_view(request, pk):
    m = get_object_or_404(TeamMember, pk=pk)
    if request.method == 'POST':
        form = TeamMemberForm(request.POST, request.FILES, instance=m)
        if form.is_valid(): form.save(); messages.success(request, "Mis à jour."); return redirect('dashboard:team_list')
    else: form = TeamMemberForm(instance=m)
    return render(request, 'dashboard/about/team_form.html', {'form': form})
@login_required
@admin_or_manager_required
def team_delete_view(request, pk):
    m = get_object_or_404(TeamMember, pk=pk)
    if request.method == 'POST': m.delete(); messages.success(request, "Supprimé."); return redirect('dashboard:team_list')
    return render(request, 'dashboard/about/team_confirm_delete.html', {'member': m})

# Static Pages Dashboard
@login_required
@admin_or_manager_required
def static_page_list(request): return render(request, 'dashboard/pages/list.html', {'pages': StaticPage.objects.all()})
@login_required
@admin_or_manager_required
def static_page_add(request):
    if request.method == 'POST':
        form = StaticPageForm(request.POST)
        if form.is_valid(): form.save(); messages.success(request, "Page créée."); return redirect('dashboard:static_page_list')
    else: form = StaticPageForm()
    return render(request, 'dashboard/pages/form.html', {'form': form})
@login_required
@admin_or_manager_required
def static_page_edit(request, pk):
    p = get_object_or_404(StaticPage, pk=pk)
    if request.method == 'POST':
        form = StaticPageForm(request.POST, instance=p)
        if form.is_valid(): form.save(); messages.success(request, "Page mise à jour."); return redirect('dashboard:static_page_list')
    else: form = StaticPageForm(instance=p)
    return render(request, 'dashboard/pages/form.html', {'form': form})
@login_required
@admin_or_manager_required
def static_page_delete(request, pk):
    p = get_object_or_404(StaticPage, pk=pk)
    if request.method == 'POST': p.delete(); messages.success(request, "Page supprimée."); return redirect('dashboard:static_page_list')
    return render(request, 'dashboard/pages/confirm_delete.html', {'page': p})

# Newsletter Dashboard
@login_required
@admin_or_manager_required
def newsletter_list(request):
    q = request.GET.get('q')
    subs = NewsletterSubscriber.objects.filter(email__icontains=q) if q else NewsletterSubscriber.objects.all()
    return render(request, 'dashboard/newsletter/list.html', {'subscribers': subs.order_by('-subscribed_at')})

@login_required
@admin_or_manager_required
def shop_newsletter(request):
    instance = ShopInfo.get_instance()
    if request.method == 'POST':
        form = NewsletterSettingsForm(request.POST, request.FILES, instance=instance)
        if form.is_valid():
            form.save()
            messages.success(request, "Section Newsletter mise à jour !")
            return redirect('dashboard:shop_newsletter')
    else:
        form = NewsletterSettingsForm(instance=instance)
    return render(request, 'dashboard/settings/newsletter.html', {'form': form})




from shop.models import NewsletterSubscriber

def newsletter_subscribers_list(request):
    """
    Affiche la liste des abonnés à la newsletter dans le dashboard.
    """
    subscribers = NewsletterSubscriber.objects.all().order_by('-subscribed_at')

    # Optionnel : ajouter une recherche simple via GET
    query = request.GET.get('q')
    if query:
        subscribers = subscribers.filter(email__icontains=query)

    context = {
        'subscribers': subscribers,
        'query': query,
    }
    return render(request, 'dashboard/newsletter_subscribers.html', context)


from django.core.mail import send_mass_mail

def send_newsletter(request):
    """
    Page pour envoyer un email à tous les abonnés newsletter.
    """
    subscribers = NewsletterSubscriber.objects.all()

    if request.method == "POST":
        subject = request.POST.get("subject")
        message = request.POST.get("message")
        from_email = "no-reply@tonsite.com"  # ou settings.DEFAULT_FROM_EMAIL

        if not subject or not message:
            messages.error(request, "Veuillez remplir le sujet et le message.")
            return redirect("dashboard:send_newsletter")

        # Préparer les emails
        emails = [(subject, message, from_email, [sub.email]) for sub in subscribers]

        # Envoi multiple
        send_mass_mail(emails, fail_silently=False)

        messages.success(request, f"Newsletter envoyée à {subscribers.count()} abonnés.")
        return redirect("dashboard:send_newsletter")

    return render(request, "dashboard/send_newsletter.html", {"subscribers": subscribers})
