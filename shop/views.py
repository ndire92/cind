from decimal import Decimal
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator,EmptyPage, PageNotAnInteger
from .models import Order, OrderItem, Product, Category, ShippingZone,ShopInfo,BlogPost
from .cart import Cart  # Importez la classe créée juste avant
import csv 
from .forms import OrderCreateForm,CustomUserCreationForm
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.views import LoginView
from django.urls import reverse, reverse_lazy
from django.contrib.auth import login
from .dashboard import views
from django.contrib.auth import authenticate, login, logout

from .models import User

# FONCTIONS D'AUTHENTIFICATION
# ==================================================

def redirect_by_role(user):
    if user.role == "gestionnaire":
        return redirect("dashboard:overview")
    elif user.role == "customer":
        return redirect("products:profile")
    return redirect("home")
    

def register_view(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect_by_role(user)
    else:
        form = CustomUserCreationForm()
    return render(request, 'registration/register.html', {'form': form})

from django.contrib.auth.forms import AuthenticationForm

def login_view(request):
    if request.method == "POST":
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect_by_role(user)
        else:
            return render(request, "registration/login.html", {"form": form})
    else:
        form = AuthenticationForm()
    return render(request, "registration/login.html", {"form": form})

def logout_view(request):
    logout(request)
    return redirect(reverse("products:login"))



def some_view(request):
    if request.user.is_authenticated:
        if request.user.role == "gestionnaire":
            redirect_url = reverse("dashboard:overview")
        elif request.user.role == "customer":
            redirect_url = reverse("products:profile")
        else:
            redirect_url = reverse("home")
    else:
        redirect_url = reverse("products:login")

    return render(request, "template.html", {"redirect_url": redirect_url})

# --- PROFILE ---
def profile(request):
    if not request.user.is_authenticated:
        return redirect("products:login")
    return render(request, 'registration/profile.html')



def index(request):
    """
    Page d'accueil : Affiche tous les produits ou les 6 derniers.
    """
    cart = Cart(request)
    categories = Category.objects.all() # Récupère toutes les catégories
    config = ShopInfo.get_instance()
    featured_post = BlogPost.objects.filter(is_active=True).order_by('-created_at').first()
    products = Product.objects.filter(available=True)[:4] # Les 6 derniers produits

    return render(request, 'shop/index.html', {
        'products': products,
        'categories':categories,
         'config': config,
         'cart':cart,
         'featured_post': featured_post,


        })

def shop(request):
    """
    Page Boutique : Affiche la liste avec pagination et filtrage par catégorie.
    """
    cart = Cart(request)
    # Récupérer le filtre de catégorie depuis l'URL (ex: ?category=visage)
    category_slug = request.GET.get('category')
    
    # Base de requête : produits disponibles
    products = Product.objects.filter(available=True)
    
    # Filtrer si une catégorie est demandée
    category = None
    if category_slug:
        category = get_object_or_404(Category, slug=category_slug)
        products = products.filter(category=category)

    # Pagination : 12 produits par page
    paginator = Paginator(products, 12)
    page_number = request.GET.get('page', 1)
    products_page = paginator.get_page(page_number)

    # Envoyer aussi la liste des catégories pour le menu de filtres
    categories = Category.objects.all()

    context = {
        'products_page': products_page,
        'category': category,
        'categories': categories,
        'cart':cart
    }
    return render(request, 'shop/shop.html', context)

def product_detail(request, id, slug):
    """
    Page Produit : Affiche un produit spécifique.
    """
    # On cherche le produit par son ID et son slug (double vérification)
    product = get_object_or_404(Product, id=id, slug=slug, available=True)
    
    return render(request, 'shop/product.html', {'product': product})


def category_list(request, category_slug):
    """
    Vue pour afficher les produits d'une catégorie spécifique.
    (Similaire à la page boutique mais le slug est dans l'URL)
    """
    category = get_object_or_404(Category, slug=category_slug)
    products = Product.objects.filter(category=category, available=True)
    
    # Pagination
    paginator = Paginator(products, 12)
    page_number = request.GET.get('page', 1)
    products_page = paginator.get_page(page_number)

    categories = Category.objects.all()

    context = {
        'products_page': products_page,
        'category': category,
        'categories': categories
    }
    return render(request, 'shop/shop.html', context)




# ... vos fonctions existantes (index, shop, product_detail) ...

def cart_detail(request):
    """
    Affiche la page du panier.
    """
    cart = Cart(request)
    return render(request, 'shop/cart.html', {'cart': cart})

def cart_add(request, product_id):
    """
    Vue pour ajouter un produit au panier.
    """
    cart = Cart(request)
    product = get_object_or_404(Product, id=product_id)
    
    # Ajoute 1 produit
    cart.add(product=product)
    
    # CORRECTION ICI : On utilise 'products:cart_detail'
    return redirect('products:cart_detail')

def cart_remove(request, product_id):
    cart = Cart(request)
    product = get_object_or_404(Product, id=product_id)
    cart.remove(product)
    return redirect('products:cart_detail')  # Correction ici aussi


def order_create(request):
    cart = Cart(request)

    if len(cart) == 0:
        return redirect('products:cart_detail')

    if request.method == 'POST':
        form = OrderCreateForm(request.POST)

        if form.is_valid():
            order = form.save(commit=False)

            if request.user.is_authenticated:
                order.user = request.user

            # Livraison
            order.shipping_cost = Order.get_shipping_cost_by_country(order.country)

            # Paiement
            order.payment_status = "PENDING"
            order.save()

            # Produits
            for item in cart:
                OrderItem.objects.create(
                    order=order,
                    product=item['product'],
                    price=item['price_ht'],
                    quantity=item['quantity']
                )

            cart.clear()

            # 🔥 REDIRECTION PAYDUNYA
            if order.payment_method == 'PAYDUNYA':
                return redirect('products:paydunya_init', order_id=order.id)

            # Autre paiement → confirmation
            return redirect('products:order_confirmation', order_id=order.id)

    else:
        form = OrderCreateForm()

    return render(request, 'shop/checkout.html', {
        'cart': cart,
        'form': form,
    })


def shipping_cost_ajax(request):
    """
    Retourne le prix de livraison pour un pays donné via AJAX.
    """
    country = request.GET.get('country', '').strip().upper()

    if not country:
        return JsonResponse({'price': 0})

    # Recherche de la zone correspondant au pays
    zones = ShippingZone.objects.all()
    price = 0

    for zone in zones:
        codes = zone.get_country_codes()
        if 'ALL' in codes or country in codes:
            price = float(zone.price)
            break

    return JsonResponse({'price': price})


import requests
from django.conf import settings

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
            "total_amount": float(order.get_total_cost()),
            "description": f"Commande #{order.id}"
        },
        "store": {
            "name": "Terra & Pure",
            "website_url": "http://127.0.0.1:8000",
        },
        "actions": {
            "callback_url": "http://127.0.0.1:8000/paydunya/callback/",
            "return_url": "http://127.0.0.1:8000/boutique/",
            "cancel_url": "http://127.0.0.1:8000/boutique/checkout/",
        }
    }

    response = requests.post(url, json=data, headers=headers)
    result = response.json()

    if result.get("response_code") == "00":
        return redirect(result["response_text"])
    
    return redirect('products:checkout')



def payment_success(request):
    return render(request, 'shop/payment_success.html')



def product_detail(request, id, slug):
    product = get_object_or_404(Product, id=id, slug=slug, available=True)

    related_products = Product.objects.filter(
        category=product.category,
        available=True
    ).exclude(id=product.id)[:4]

    return render(request, 'shop/produits.html', {
        'product': product,
        'related_products': related_products
    })


def product_list(request):
    products = Product.objects.filter(available=True)
    categories = Category.objects.all()

    # --- Filtres ---
    category_id = request.GET.get("category")
    min_price = request.GET.get("min_price")
    max_price = request.GET.get("max_price")

    if category_id:
        products = products.filter(category_id=category_id)

    if min_price:
        products = products.filter(price_ht__gte=Decimal(min_price))

    if max_price:
        products = products.filter(price_ht__lte=Decimal(max_price))

    context = {
        "products": products,
        "categories": categories,
        "selected_category": category_id,
        "min_price": min_price,
        "max_price": max_price,
    }
    return render(request, "shop/shop.html", context)


def checkout(request):
    cart = Cart(request)

    if request.method == "GET" and len(cart) == 0:
        return redirect('products:cart_detail')

    if request.method == "POST":
        form = CheckoutForm(request.POST)  # ton formulaire
        if form.is_valid():
            order = Order.objects.create(
                user=request.user if request.user.is_authenticated else None,
                paid=True,
                total_price=cart.get_total_ttc(),
                shipping_address=form.cleaned_data["address"],
                first_name=form.cleaned_data["first_name"],
                last_name=form.cleaned_data["last_name"],
                email=form.cleaned_data["email"],
                city=form.cleaned_data["city"],
                postal_code=form.cleaned_data["postal_code"],
                country=form.cleaned_data["country"],
                payment_method=form.cleaned_data["payment_method"],
            )

            for item in cart:
                OrderItem.objects.create(
                    order=order,
                    product=item['product'],
                    quantity=item['quantity'],
                    price=item['price_ttc']
                )

            cart.clear()
            
            return redirect('products:order_confirmation', order_id=order.id)
        else:
            # Réaffiche le formulaire avec erreurs
            return render(request, 'shop/checkout.html', {
                'cart': cart,
                'form': form
            })

    else:
        form = CheckoutForm()
        return render(request, 'shop/checkout.html', {
            'cart': cart,
            'form': form
        })

def order_confirmation(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    return render(request, 'shop/order_confirmation.html', {
        'order': order
    })



def cart_update(request, product_id):
    cart = Cart(request)
    product = get_object_or_404(Product, id=product_id)

    if request.method == "POST":
        quantity = int(request.POST.get("quantity", 1))

        cart.add(
            product=product,
            quantity=quantity,
            update_quantity=True  # ✅ NOM CORRECT
        )

    return redirect('products:cart_detail')


def invoice_download(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    
    # Exemple basique : créer un fichier texte avec les infos
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="facture_{order.id}.pdf"'

    # Ici tu peux générer du PDF avec reportlab / weasyprint
    response.write(f"Facture pour la commande #{order.id}\n")
    response.write(f"Total: {order.total_price} €\n")
    # Ajouter produits, quantités, TTC etc. si besoin

    return response

def bien_etre(request):
    """
    Page dédiée au Bien-être avec pagination.
    """
    config = ShopInfo.get_instance()
    
    # Récupération de tous les articles actifs
    blog_posts_list = BlogPost.objects.filter(is_active=True).order_by('-created_at')
    
    # Pagination : 3 articles par page (comme dans votre version initiale)
    paginator = Paginator(blog_posts_list, 3) 
    page_number = request.GET.get('page', 1)
    
    try:
        blog_posts = paginator.page(page_number)
    except PageNotAnInteger:
        blog_posts = paginator.page(1)
    except EmptyPage:
        blog_posts = paginator.page(paginator.num_pages)
    
    return render(request, 'shop/bien_etre.html', {
        'config': config,
        'blog_posts': blog_posts,
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

def about_page(request):
    """
    Page À propos indépendante
    """
    # Récupère les infos configurées dans l'admin (ShopInfo)
    config = ShopInfo.get_instance()
    
    return render(request, 'shop/about.html', {
        'config': config,
    })


def cart_add(request, product_id):
    cart = Cart(request)
    product = get_object_or_404(Product, id=product_id)

    quantity = int(request.POST.get('quantity', 1))

    cart.add(product=product, quantity=quantity)

    return redirect('products:cart_detail')

from decimal import Decimal

def get_total_cost(self):
    return sum(item.get_cost() for item in self.items.all()) or Decimal("0.00")