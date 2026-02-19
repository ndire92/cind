import logging
from decimal import Decimal
import os
from django.shortcuts import render, redirect, get_object_or_404, reverse
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import login, logout
from django.contrib import messages
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.core.paginator import Paginator,EmptyPage, PageNotAnInteger
import requests
from django.db.models import Min, Max
from django.contrib.auth.views import LoginView
from django.http import JsonResponse, HttpResponse
from django.db import transaction
from django.utils import timezone
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.db.models import Sum, Count
from django.contrib.auth.decorators import login_required
from .decorators import admin_or_manager_required
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from reportlab.platypus import Table
from reportlab.lib.units import inch
from reportlab.platypus import TableStyle
from reportlab.platypus import ListFlowable, ListItem
from reportlab.platypus import Image
from reportlab.platypus import KeepTogether
from reportlab.platypus import PageBreak
from reportlab.platypus import Frame
from reportlab.platypus import PageTemplate
from reportlab.platypus import BaseDocTemplate
from reportlab.platypus import Flowable
from reportlab.platypus import HRFlowable
from reportlab.platypus import Paragraph
from reportlab.platypus import Spacer
from reportlab.platypus import SimpleDocTemplate
from reportlab.platypus import Table
from reportlab.platypus import TableStyle

import os
from django.conf import settings
from config import settings

# Imports de vos modèles et formulaires (assurez-vous que les noms correspondent)
from .models import (
    Banner, Product, Category, Order, OrderItem, ProductImage, ShippingZone, 
    PaymentMethod, Coupon, ShopInfo, BlogPost,
    User, Transaction, Invoice
)
from .forms import (
    AboutSettingsForm, BannerForm, NewsletterSettingsForm, PaymentMethodForm, ProductForm, ProductImageFormSet, OrderCreateForm, PromoSettingsForm, ShippingZoneForm, 
    UserRegistrationForm, ShopInfoForm, BlogPostForm, CategoryForm
)

logger = logging.getLogger(__name__)

# ============================================================================
# HELPERS & MIXINS
# ============================================================================

def is_manager(user):
    return user.is_authenticated and (user.is_manager() or user.is_admin_role())

# ============================================================================
# VUES PUBLIQUES (Frontend)
# ============================================================================


def index(request):
    """Page d'accueil"""

    category_id = request.GET.get('category')

    shop_info = ShopInfo.get_instance()
    banners = Banner.objects.all()
    categories = Category.objects.all()

    # Base queryset
    products = Product.objects.filter(available=True)

    # Filtrage par catégorie
    if category_id:
        category = get_object_or_404(Category, id=category_id)
        products = products.filter(category=category)
        active_category = category
    else:
        active_category = None

    # Produits affichés (limite 4)
    featured_products = products[:4]

    posts = BlogPost.objects.filter(is_active=True)[:3]
    featured_post = posts.first()

    context = {
        'shop_info': shop_info,
        'products': featured_products,
        'posts': posts,
        'featured_post': featured_post,
        'banners': banners,
        'categories': categories,
        'current_category': active_category,
    }

    return render(request, 'shop/index.html', context)

def shop(request):
    """Page boutique avec filtres catégorie et prix"""
    
    # Récupérer toutes les catégories pour la sidebar
    categories = Category.objects.all()
    
    # Catégorie sélectionnée
    category_id = request.GET.get('category')
    current_category = None
    products = Product.objects.filter(available=True)
    
    if category_id:
        current_category = get_object_or_404(Category, id=category_id)
        products = products.filter(category=current_category)
    
    # Filtre par prix depuis GET
    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')
    if min_price:
        products = products.filter(price_ht__gte=min_price)
    if max_price:
        products = products.filter(price_ht__lte=max_price)
    
    # Calculer plage de prix pour slider / inputs
    price_range = products.aggregate(
        min_price=Min('price_ht'),
        max_price=Max('price_ht')
    )
    
    context = {
        'categories': categories,
        'products': products,
        'current_category': current_category,
        'price_range': price_range,
        'selected_min_price': min_price,
        'selected_max_price': max_price,
    }
    
    return render(request, 'shop/shop.html', context)

def product_list(request):
    """Alias pour la vue shop"""
    return shop(request)

def category_list(request, slug):
    """Filtrer par catégorie"""
    category = get_object_or_404(Category, slug=slug)
    products = category.products.filter(available=True)
    return render(request, 'shop/category.html', {'category': category, 'products': products})

def product_detail(request, id, slug):
    product = get_object_or_404(Product, id=id, slug=slug, available=True)
    # Récupérer 4 produits de la même catégorie, exclure le produit actuel
    related_products = Product.objects.filter(category=product.category).exclude(id=product.id)[:4]
    
    return render(request, 'shop/product_detail.html', {
        'product': product,
        'related_products': related_products
    })

# --- Authentification ---

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
    # Utilisez la vue login de Django ou une vue personnalisée simple
   
    return LoginView.as_view(template_name='shop/auth/login.html')(request)

def logout_view(request):
    logout(request)
    return redirect('products:shop')

@login_required
def profile(request):
    orders = request.user.orders.all()
    return render(request, 'shop/auth/profile.html', {'orders': orders})

# --- Pages Statiques ---

def about_page(request):
    shop_info = ShopInfo.get_instance()
    return render(request, 'shop/about.html', {'shop_info': shop_info})

# --- Blog ---


def bien_etre(request):
    """
    Page dédiée au Bien-être avec pagination.
    """
    config = ShopInfo.get_instance()
    
    # Récupération de tous les articles actifs
    posts = BlogPost.objects.filter(is_active=True).order_by('-created_at')
    
    # Pagination : 3 articles par page
    paginator = Paginator(posts, 3)
    page_number = request.GET.get('page', 1)
    
    try:
        blog_posts = paginator.page(page_number)
    except PageNotAnInteger:
        blog_posts = paginator.page(1)
    except EmptyPage:
        blog_posts = paginator.page(paginator.num_pages)
    
    return render(request, 'shop/bien_etre.html', {
        'config': config,
        'blog_posts': blog_posts,  # <-- c’est ça qu’il faut passer
    })

def post_detail(request, slug):
    """
    Page de détail d'un article de blog.
    """
    config = ShopInfo.get_instance()
    
    # Récupérer l'article correspondant au slug
    post = get_object_or_404(BlogPost, slug=slug, is_active=True)
    
    return render(request, 'shop/blog_detail.html', {
        'config': config,
        'post': post,
    })


# ============================================================================
# PANIER (Cart - Basé sur les sessions)
# ============================================================================

def get_cart(request):
    """Récupère le panier depuis la session"""
    cart = request.session.get('cart', {})
    # Structure: {product_id: {'quantity': 1, 'price': '10.00'}}
    return cart

def cart_detail(request):
    cart = get_cart(request)
    items = []
    total = Decimal('0.00')
    
    for product_id, item_data in cart.items():
        product = get_object_or_404(Product, id=product_id)
        price = Decimal(item_data.get('price', product.price_ht))
        quantity = int(item_data.get('quantity', 0))
        item_total = price * quantity
        items.append({
            'product': product,
            'quantity': quantity,
            'price': price,
            'total': item_total
        })
        total += item_total
    
    return render(request, 'shop/cart/detail.html', {'items': items, 'total': total})

def cart_add(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    cart = get_cart(request)
    quantity = int(request.POST.get('quantity', 1))
    
    if str(product_id) in cart:
        cart[str(product_id)]['quantity'] += quantity
    else:
        cart[str(product_id)] = {'quantity': quantity, 'price': str(product.price_ht)}
    
    request.session['cart'] = cart
    messages.success(request, "Produit ajouté au panier.")
    return redirect('products:cart_detail')

def cart_remove(request, product_id):
    cart = get_cart(request)
    if str(product_id) in cart:
        del cart[str(product_id)]
        request.session['cart'] = cart
    return redirect('products:cart_detail')

def cart_update(request, product_id):
    cart = get_cart(request)
    quantity = int(request.POST.get('quantity', 0))
    
    if quantity > 0 and str(product_id) in cart:
        cart[str(product_id)]['quantity'] = quantity
    elif quantity <= 0:
        del cart[str(product_id)]
    
    request.session['cart'] = cart
    return redirect('products:cart_detail')


# ============================================================================
# COMMANDE & PAIEMENT
# ============================================================================

def order_create(request):
    cart = get_cart(request)
    if not cart:
        return redirect('products:shop')

    # Calcul du total pour l'affichage dans le résumé (à passer au contexte)
    cart_total = Decimal('0.00')
    for item_data in cart.values():
        cart_total += Decimal(item_data['price']) * int(item_data['quantity'])

    if request.method == 'POST':
        # On passe les données POST et l'utilisateur
        form = OrderCreateForm(request.POST, user=request.user)
        if form.is_valid():
            with transaction.atomic():
                order = form.save(commit=False)

                # Assigner l'utilisateur si connecté
                if request.user.is_authenticated:
                    order.user = request.user

                # Mode de paiement
                payment_method = form.cleaned_data.get('payment_method')
                if payment_method:
                    order.payment_method = payment_method
                    order.payment_fee = payment_method.extra_fee
                else:
                    order.payment_fee = Decimal('0.00')

                # Calcul du sous-total et préparation des items
                subtotal = Decimal('0.00')
                items_to_create = []
                for product_id, item_data in cart.items():
                    product = get_object_or_404(Product, id=product_id)
                    price = Decimal(item_data['price'])
                    quantity = int(item_data['quantity'])
                    subtotal += price * quantity
                    items_to_create.append(OrderItem(
                        product=product,
                        product_name=product.name,
                        price=price,
                        quantity=quantity
                    ))

                order.subtotal = subtotal
                order.vat_rate = Decimal('18.00')
                order.vat_amount = (subtotal * order.vat_rate) / Decimal('100')

                # Livraison
                shipping_cost = Order.get_shipping_cost_by_country(form.cleaned_data.get('country'))
                order.shipping_cost = shipping_cost

                # Coupon / remise
                coupon = form.cleaned_data.get('coupon')
                if coupon and coupon.active:
                    now = timezone.now()
                    if coupon.valid_from <= now <= coupon.valid_to:
                        order.discount_amount = (subtotal * coupon.discount_percent) / Decimal('100')
                    else:
                        order.discount_amount = Decimal('0.00')
                else:
                    order.discount_amount = Decimal('0.00')

                # Total final = sous-total + TVA + livraison + frais paiement - remise
                order.total_price = (
                    order.subtotal
                    + order.vat_amount
                    + order.shipping_cost
                    + order.payment_fee
                    - order.discount_amount
                )

                order.payment_status = Order.PaymentStatus.PENDING
                order.save()

                # Lier les items à la commande
                for item in items_to_create:
                    item.order = order
                OrderItem.objects.bulk_create(items_to_create)

                # Vider le panier
                request.session['cart'] = {}

                return redirect('products:order_confirmation', order_id=order.id)

    else:
        # CORRECTION ICI : On ne passe pas request.POST pour un affichage vierge
        form = OrderCreateForm(user=request.user)
    
    return render(request, 'shop/orders/create.html', {
        'form': form,
        'total': cart_total # Utile pour le résumé sidebar
    })

def order_confirmation(request, order_id):
    order = get_object_or_404(Order, id=order_id)

    # Si paiement à la livraison, on considère payé
    if order.payment_method and order.payment_method.slug == "cod":  # cod = cash on delivery
        order.payment_status = Order.PaymentStatus.PAID
        order.save()

    return render(request, 'shop/orders/confirmation.html', {
        'order': order
    })



def payment_success(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    
    # Marquer la commande comme payée si ce n'est pas déjà fait
    if order.payment_status != Order.PaymentStatus.PAID:
        order.payment_status = Order.PaymentStatus.PAID
        order.save()
    
    return render(request, 'shop/orders/payment_success.html', {'order': order})

def shipping_cost_ajax(request):
    country_code = request.GET.get('country')
    cost = Order.get_shipping_cost_by_country(country_code)
    return JsonResponse({'cost': str(cost)})

def invoice_download(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    # Logique de génération PDF (comme défini dans le modèle Invoice)
    # Pour simplifier, on retourne une réponse simple ici
    return HttpResponse(f"Facture pour commande #{order.id} - Bientôt en PDF")


# ============================================================================
# DASHBOARD (Gestionnaire)
# ============================================================================


@login_required
@admin_or_manager_required
def dashboard_overview(request):
    # Stats globales
    total_orders = Order.objects.count()
    total_revenue = Order.objects.filter(payment_status='paid').aggregate(Sum('total_price'))['total_price__sum'] or 0
    total_products = Product.objects.count()
    
    # Dernières commandes (5 dernières)
    recent_orders = Order.objects.all().order_by('-created_at')[:5]
    
    context = {
        'orders': total_orders,
        'revenue': total_revenue,
        'products': total_products,
        'recent_orders': recent_orders,
    }
    return render(request, 'dashboard/overview.html', context)

# --- Gestion Produits ---

@login_required
@admin_or_manager_required
def dashboard_products(request):
    products = Product.objects.all()
    return render(request, 'dashboard/products/list.html', {'products': products})

@login_required
@admin_or_manager_required
def add_product(request):
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)
        formset = ProductImageFormSet(request.POST, request.FILES, queryset=ProductImage.objects.none())
        
        if form.is_valid() and formset.is_valid():
            product = form.save()
            # Sauvegarder les images
            for image_form in formset:
                if image_form.cleaned_data.get('image'):
                    image = image_form.save(commit=False)
                    image.product = product
                    image.save()
            messages.success(request, "Produit ajouté.")
            return redirect('dashboard:products')
    else:
        form = ProductForm()
        formset = ProductImageFormSet(queryset=ProductImage.objects.none())
    
    return render(request, 'dashboard/products/form.html', {'form': form, 'formset': formset})


@login_required
@admin_or_manager_required
def edit_product(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, instance=product)
        formset = ProductImageFormSet(request.POST, request.FILES, queryset=product.images.all())
        
        if form.is_valid() and formset.is_valid():
            form.save()
            formset.save() # Gère l'ajout, modif et suppression
            messages.success(request, "Produit mis à jour.")
            return redirect('dashboard:products')
    else:
        form = ProductForm(instance=product)
        formset = ProductImageFormSet(queryset=product.images.all())
    
    return render(request, 'dashboard/products/form.html', {'form': form, 'formset': formset})

@login_required
@admin_or_manager_required
def delete_product(request, pk):
    product = get_object_or_404(Product, id=pk)
    product.delete()
    return redirect('dashboard:products')

# --- Gestion Commandes ---

@login_required
@admin_or_manager_required
def dashboard_orders(request):
    orders = Order.objects.all()
    return render(request, 'dashboard/orders/list.html', {'orders': orders})

@login_required
@admin_or_manager_required
def order_detail(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    return render(request, 'dashboard/orders/detail.html', {'order': order})

@login_required
@admin_or_manager_required
@transaction.atomic
def update_order_status(request, order_id):
    order = get_object_or_404(Order, id=order_id)

    if request.method == "POST":

        # Éviter d'envoyer plusieurs fois
        if order.is_shipped:
            messages.warning(request, "Commande déjà marquée comme envoyée.")
            return redirect('dashboard:order_detail', order_id=order.id)

        order.is_shipped = True
        order.save()

        # Email
        send_invoice_email(order)

        # WhatsApp (optionnel si configuré)
        try:
            send_invoice_whatsapp(order)
        except Exception as e:
            print("Erreur WhatsApp:", e)

        messages.success(request, "Commande marquée comme envoyée et notification envoyée.")

    return redirect('dashboard:order_detail', order_id=order.id)

def send_invoice_email(order):
    subject = f"Votre commande #{order.id} a été expédiée 🚚"

    html_content = render_to_string("emails/invoice_email.html", {
        "order": order
    })

    email = EmailMessage(
        subject,
        html_content,
        settings.DEFAULT_FROM_EMAIL,
        [order.email],
    )

    email.content_subtype = "html"

    # Générer facture PDF
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
        data.append([
            item.product.name,
            str(item.quantity),
            f"{item.price} FCFA"
        ])

    table = Table(data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.grey),
        ('GRID', (0,0), (-1,-1), 1, colors.black),
    ]))

    elements.append(table)

    doc.build(elements)

    return file_path

# --- Configuration ---

@login_required
@admin_or_manager_required

@login_required
def banner_list(request):
    banners = Banner.objects.all()
    return render(request, "dashboard/banner_list.html", {
        "banners": banners
    })


@login_required
def banner_create(request):
    if request.method == "POST":
        form = BannerForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, "Bannière ajoutée ✅")
            return redirect("products:banner_list")
    else:
        form = BannerForm()

    return render(request, "dashboard/banner_form.html", {
        "form": form
    })


@login_required
def banner_update(request, pk):
    banner = get_object_or_404(Banner, pk=pk)

    if request.method == "POST":
        form = BannerForm(request.POST, request.FILES, instance=banner)
        if form.is_valid():
            form.save()
            messages.success(request, "Bannière mise à jour ✅")
            return redirect("products:banner_list")
    else:
        form = BannerForm(instance=banner)

    return render(request, "dashboard/banner_form.html", {
        "form": form
    })


@login_required
def banner_delete(request, pk):
    banner = get_object_or_404(Banner, pk=pk)

    if request.method == "POST":
        banner.delete()
        messages.success(request, "Bannière supprimée ❌")
        return redirect("products:banner_list")

    return render(request, "dashboard/banner_confirm_delete.html", {
        "banner": banner
    })





@login_required
@admin_or_manager_required
def shop_promo(request):
    instance = ShopInfo.get_instance()
    if request.method == 'POST':
        form = PromoSettingsForm(request.POST, request.FILES, instance=instance)
        if form.is_valid():
            form.save()
            messages.success(request, "Section Promotion mise à jour !")
            return redirect('dashboard:shop_promo')
    else:
        form = PromoSettingsForm(instance=instance)
    return render(request, 'dashboard/settings/promo.html', {'form': form})

@login_required
@admin_or_manager_required
def shop_about(request):
    instance = ShopInfo.get_instance()
    if request.method == 'POST':
        form = AboutSettingsForm(request.POST, request.FILES, instance=instance)
        if form.is_valid():
            form.save()
            messages.success(request, "Section À Propos mise à jour !")
            return redirect('dashboard:shop_about')
    else:
        form = AboutSettingsForm(instance=instance)
    return render(request, 'dashboard/settings/about.html', {'form': form})

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

# --- Blog Dashboard ---

@login_required
@admin_or_manager_required
def blog_list_view(request):
    posts = BlogPost.objects.all()
    return render(request, 'dashboard/blog/list.html', {'posts': posts})

@login_required
@admin_or_manager_required
def blog_create_view(request):
    if request.method == 'POST':
        form = BlogPostForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect('dashboard:blog_posts')
    else:
        form = BlogPostForm()
    return render(request, 'dashboard/blog/form.html', {'form': form})

@login_required
@admin_or_manager_required
def blog_update_view(request, pk):
    post = get_object_or_404(BlogPost, id=pk)
    if request.method == 'POST':
        form = BlogPostForm(request.POST, request.FILES, instance=post)
        if form.is_valid():
            form.save()
            return redirect('dashboard:blog_posts')
    else:
        form = BlogPostForm(instance=post)
    return render(request, 'dashboard/blog/form.html', {'form': form})

@login_required
@admin_or_manager_required
def blog_delete_view(request, pk):
    post = get_object_or_404(BlogPost, id=pk)
    post.delete()
    return redirect('dashboard:blog_posts')

# --- Catégories (Class Based Views) ---

class CategoryListView(ListView):
    model = Category
    template_name = 'dashboard/categories/list.html'
    context_object_name = 'categories'

class CategoryCreateView(CreateView):
    model = Category
    form_class = CategoryForm
    template_name = 'dashboard/categories/form.html'
    success_url = reverse_lazy('dashboard:category_list')

class CategoryUpdateView(UpdateView):
    model = Category
    form_class = CategoryForm
    template_name = 'dashboard/categories/form.html'
    success_url = reverse_lazy('dashboard:category_list')
    slug_url_kwarg = 'slug'
    slug_field = 'slug'

class CategoryDeleteView(DeleteView):
    model = Category
    template_name = 'dashboard/categories/confirm_delete.html'
    success_url = reverse_lazy('dashboard:category_list')
    slug_url_kwarg = 'slug'
    slug_field = 'slug'

# --- Vues manquantes (stubs pour compatibilité URLs) ---
@login_required
@admin_or_manager_required
def dashboard_accounting(request):
    return render(request, 'dashboard/accounting.html')

@login_required
@admin_or_manager_required
def export_transactions_csv(request):
    return HttpResponse("Export CSV non implémenté")

@login_required
@admin_or_manager_required
def dashboard_settings(request):
    return render(request, 'dashboard/settings/settings.html')


@login_required
@admin_or_manager_required
def shipping_zones(request):
    zones = ShippingZone.objects.all()
    return render(request, 'dashboard/settings/shipping_list.html', {'zones': zones})

@login_required
@admin_or_manager_required
def add_shipping_zone(request):
    if request.method == 'POST':
        form = ShippingZoneForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Zone de livraison ajoutée.")
            return redirect('dashboard:shipping_zones')
    else:
        form = ShippingZoneForm()
    return render(request, 'dashboard/settings/shipping_form.html', {'form': form})

@login_required
@admin_or_manager_required
def edit_shipping_zone(request, zone_id):
    zone = get_object_or_404(ShippingZone, id=zone_id)
    if request.method == 'POST':
        form = ShippingZoneForm(request.POST, instance=zone)
        if form.is_valid():
            form.save()
            messages.success(request, "Zone mise à jour.")
            return redirect('dashboard:shipping_zones')
    else:
        form = ShippingZoneForm(instance=zone)
    return render(request, 'dashboard/settings/shipping_form.html', {'form': form})

@login_required
@admin_or_manager_required
def delete_shipping_zone(request, pk):
    zone = get_object_or_404(ShippingZone, id=pk)
    zone.delete()
    messages.success(request, "Zone supprimée.")
    return redirect('dashboard:shipping_zones')





@login_required
@admin_or_manager_required
def edit_shipping_zone(request, zone_id):
    # Logique similaire à edit_product
    return HttpResponse(f"Form edit zone {zone_id}")

@login_required
@admin_or_manager_required
def delete_shipping_zone(request, pk):
    return HttpResponse(f"Delete zone {pk}")

@login_required
@admin_or_manager_required
def payment_methods(request):
    return HttpResponse("Liste méthodes paiement")





# --- GESTION DES MOYENS DE PAIEMENT ---

@login_required
@admin_or_manager_required
def payment_methods(request):
    methods = PaymentMethod.objects.all()
    return render(request, 'dashboard/settings/payment_list.html', {'methods': methods})

@login_required
@admin_or_manager_required
def add_payment_method(request):
    if request.method == 'POST':
        form = PaymentMethodForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Moyen de paiement ajouté.")
            return redirect('dashboard:payment_methods')
    else:
        form = PaymentMethodForm()
    return render(request, 'dashboard/settings/payment_form.html', {'form': form})

@login_required
@admin_or_manager_required
def edit_payment_method(request, method_id):
    method = get_object_or_404(PaymentMethod, id=method_id)
    if request.method == 'POST':
        form = PaymentMethodForm(request.POST, instance=method)
        if form.is_valid():
            form.save()
            messages.success(request, "Moyen de paiement mis à jour.")
            return redirect('dashboard:payment_methods')
    else:
        form = PaymentMethodForm(instance=method)
    return render(request, 'dashboard/settings/payment_form.html', {'form': form})

    
@login_required
@admin_or_manager_required
def billing_settings(request):
    return HttpResponse("Paramètres facturation")

def some_view(request):
    return HttpResponse("Some view placeholder")


# Ajoutez ces imports s'ils ne sont pas déjà présents en haut du fichier


# ... (le reste de votre fichier views.py) ...

# --- PAIEMENT (À implémenter avec le SDK réel plus tard) ---


def paydunya_init(request, order_id):
    order = get_object_or_404(Order, id=order_id)

    url = "https://app.paydunya.com/sandbox-api/v1/checkout-invoice/create"

    headers = {
        "Content-Type": "application/json",
        "PAYDUNYA-MASTER-KEY": settings.PAYDUNYA_MASTER_KEY,
        "PAYDUNYA-PRIVATE-KEY": settings.PAYDUNYA_PRIVATE_KEY,
        "PAYDUNYA-TOKEN": settings.PAYDUNYA_TOKEN,
    }

    data = {
        "invoice": {
            "total_amount": float(order.total_price),
            "description": f"Commande #{order.id}"
        },
        "store": {
            "name": "Terra & Pure",
            "website_url": "http://127.0.0.1:8888",
        },
        "actions": {
            "callback_url": f"http://127.0.0.1:8888/shop/paydunya_callback/{order.id}/",
            "return_url": f"http://127.0.0.1:8888/shop/payment_success/{order.id}/",
            "cancel_url": f"http://127.0.0.1:8888/shop/order_cancelled/{order.id}/",
        }
    }

    response = requests.post(url, json=data, headers=headers)
    result = response.json()

    if result.get("response_code") == "00":
        # Redirection vers l’URL de paiement PayDunya
        return redirect(result["response_text"])
    
    # Sinon retour au checkout
    return redirect('products:checkout')
