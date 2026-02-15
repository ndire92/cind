
from decimal import Decimal
from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse
from django.db.models import Sum, F, ExpressionWrapper, DecimalField, Value
from django.db.models.functions import Coalesce
import csv
from django.db import transaction


from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from shop.models import Order, OrderItem, Product, Category, ShippingZone,ProductImage,BlogPost,BlogPost,Transaction,ShopInfo
from shop.forms import ProductForm,ShopInfoForm,BlogPostForm,CategoryForm,ProductImageFormSet
from django.forms import inlineformset_factory
from shop.cart import Cart
from datetime import datetime, timedelta
from shop.models import Transaction
from shop.decorators import gestionnaire_required



from decimal import Decimal

def get_total_ttc(self, tva_rate=Decimal("0.18")):
    """
    Retourne le total TTC : produits + frais de port + TVA
    """
    total_ht = sum(item.get_cost() for item in self.items.all()) + (self.shipping_cost or Decimal("0.00"))
    total_ttc = total_ht * (Decimal("1.00") + tva_rate)
    return total_ttc.quantize(Decimal("0.01"))  # arrondi à 2 décimales


def dashboard_overview(request):

    total_revenue = OrderItem.objects.filter(order__paid=True).aggregate(
    total=Coalesce(
        Sum(F('price') * F('quantity'), output_field=DecimalField(max_digits=10, decimal_places=2)),
        Value(Decimal("0.00"), output_field=DecimalField(max_digits=10, decimal_places=2))
    ))['total']



    total_orders = Order.objects.count()
    new_customers = Order.objects.values('user').distinct().count()
    pending_delivery = Order.objects.filter(paid=False).count()

    context = {
        'total_revenue': total_revenue,
        'total_orders': total_orders,
        'new_customers': new_customers,
        'pending_delivery': pending_delivery
    }
    return render(request, 'admin_dashboard/overview.html', context)

# --------------------------
# COMMANDES
# --------------------------
@gestionnaire_required
def dashboard_orders(request):
    # Toutes les commandes, les plus récentes d'abord
    order_list = Order.objects.order_by('-created')

    # Pagination : 10 commandes par page
    paginator = Paginator(order_list, 10)

    # Numéro de page (?page=2)
    page_number = request.GET.get('page')
    orders = paginator.get_page(page_number)

    return render(request, 'admin_dashboard/orders.html', {
        'orders': orders
    })
@gestionnaire_required
def update_order_status(request, order_id):
    """
    Met à jour le statut d'expédition d'une commande.
    Ici on fait un toggle simple : False -> True
    """
    order = get_object_or_404(Order, id=order_id)

    # Toggle du statut expédié
    order.is_shipped = not order.is_shipped
    order.save()

    return redirect('dashboard:orders')



def order_detail(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    return render(request, 'admin_dashboard/order_detail.html', {'order': order})



# --------------------------
# PRODUITS
# --------------------------
@gestionnaire_required
def dashboard_products(request):
    products = Product.objects.all()
    return render(request, 'admin_dashboard/products.html', {'products': products})

@gestionnaire_required
@transaction.atomic
def add_product(request):
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)
        formset = ProductImageFormSet(request.POST, request.FILES)

        if form.is_valid() and formset.is_valid():

            # 1️⃣ Sauvegarde du produit
            product = form.save()

            images_to_save = []

            # 2️⃣ Traitement sécurisé du formset
            for image_form in formset:

                # Ignore formulaire totalement vide
                if not image_form.cleaned_data:
                    continue

                # Suppression
                if image_form.cleaned_data.get('DELETE'):
                    if image_form.instance.pk:
                        image_form.instance.delete()
                    continue

                # Ignore si aucune image uploadée
                if not image_form.cleaned_data.get('image'):
                    continue

                img = image_form.save(commit=False)
                img.product = product
                images_to_save.append(img)

            # 3️⃣ Gestion image principale
            if images_to_save:

                # Vérifier combien sont marquées principales
                main_images = [img for img in images_to_save if img.is_main]

                if len(main_images) == 0:
                    # Aucune principale → on force la première
                    images_to_save[0].is_main = True

                elif len(main_images) > 1:
                    # Plusieurs principales → on garde seulement la première
                    first_main = main_images[0]
                    for img in images_to_save:
                        img.is_main = (img == first_main)

                # 4️⃣ Sauvegarde finale
                for img in images_to_save:
                    img.save()

            return redirect('dashboard:products')

    else:
        form = ProductForm()
        formset = ProductImageFormSet(queryset=ProductImage.objects.none())

    return render(request, 'admin_dashboard/add_product.html', {
        'form': form,
        'formset': formset
    })


@gestionnaire_required
def edit_product(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            form.save()
            return redirect('dashboard:products')
    else:
        form = ProductForm(instance=product)
    return render(request, 'admin_dashboard/edit_product.html', {'form': form})

@gestionnaire_required
def delete_product(request, pk):
    # On récupère le produit
    product = get_object_or_404(Product, pk=pk)
    
    # On vérifie que c'est bien une requête POST (sécurité)
    if request.method == 'POST':
        product.delete()
        
    # Dans tous les cas, on redirige vers la liste
    return redirect('dashboard:products')

# --- LISTE DES CATÉGORIES ---
class CategoryListView(LoginRequiredMixin, ListView):
    model = Category
    template_name = 'admin_dashboard/category_list.html'
    context_object_name = 'categories'
    ordering = ['name']

# --- AJOUTER UNE CATÉGORIE ---

class CategoryCreateView(LoginRequiredMixin, CreateView):
    model = Category
    form_class = CategoryForm
    template_name = 'admin_dashboard/category_form.html'
    success_url = reverse_lazy('dashboard:category_list')

# --- MODIFIER UNE CATÉGORIE ---

class CategoryUpdateView(LoginRequiredMixin, UpdateView):
    model = Category
    form_class = CategoryForm
    template_name = 'admin_dashboard/category_form.html'
    success_url = reverse_lazy('dashboard:category_list')

# --- SUPPRIMER UNE CATÉGORIE ---s

class CategoryDeleteView(LoginRequiredMixin, DeleteView):
    model = Category
    template_name = 'admin_dashboard/category_confirm_delete.html'
    success_url = reverse_lazy('dashboard:category_list')
    # Redirection vers la liste après suppression
# --------------------------
# COMPTABILITÉ
# --------------------------

def export_transactions_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="transactions.csv"'

    writer = csv.writer(response)
    writer.writerow(['Date', 'Description', 'Type', 'Montant', 'Statut'])

    transactions = Transaction.objects.all()
    for t in transactions:
        writer.writerow([t.date, t.description, t.type, t.amount, t.status])

    return response

@gestionnaire_required
def dashboard_accounting(request):
    # Dernières transactions
    transactions = Transaction.objects.order_by('-date')[:10]

    # Calcul du mois courant
    today = datetime.today()
    start_month = today.replace(day=1)

    ventes = Transaction.objects.filter(
        type='income',
        status='paid',
        date__gte=start_month
    ).aggregate(total=Sum('amount'))['total'] or 0

    depenses = Transaction.objects.filter(
        type='expense',
        status='paid',
        date__gte=start_month
    ).aggregate(total=Sum('amount'))['total'] or 0

    profit_net = ventes - depenses

    # Pour graphique (ex: ventes journalières)
    jours = [(start_month + timedelta(days=i)).date() for i in range(today.day)]
    ventes_journalières = []
    for j in jours:
        total = Transaction.objects.filter(
            type='income',
            status='paid',
            date__date=j
        ).aggregate(total=Sum('amount'))['total'] or 0
        ventes_journalières.append(float(total))

    context = {
        'transactions': transactions,
        'ventes': ventes,
        'depenses': depenses,
        'profit_net': profit_net,
        'jours': [j.strftime("%d/%m") for j in jours],
        'ventes_journalières': ventes_journalières,
    }
    return render(request, 'admin_dashboard/accounting.html', context)

@gestionnaire_required
def dashboard_settings(request):


    return render(request, 'admin_dashboard/settings.html')


# shop/views.py

@gestionnaire_required
def shipping_zones(request):
    zones = ShippingZone.objects.all()
    error = None

    if request.method == "POST":
        name = request.POST.get("name")
        countries = request.POST.get("countries")
        price_input = request.POST.get("price")

        if name and countries and price_input:
            try:
                # On utilise float au lieu de Decimal
                clean_price = price_input.replace(',', '.')
                price = float(clean_price)
                
                ShippingZone.objects.create(
                    name=name,
                    countries=countries,
                    price=price
                )
                return redirect('dashboard:shipping_zones')
            
            except ValueError: # On catche simplement ValueError
                error = "Le prix doit être un nombre valide (ex: 12.50)."
        else:
            error = "Tous les champs sont obligatoires."

    return render(request, 'admin_dashboard/shipping_zones.html', {'zones': zones, 'error': error})
    
# --- Ajouter une zone de livraison ---
@gestionnaire_required
def add_shipping_zone(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        countries = request.POST.get('countries')
        price = request.POST.get('price')
        ShippingZone.objects.create(name=name, countries=countries, price=price)
        return redirect('dashboard:shipping_zones')
    return render(request, 'admin_dashboard/add_shipping_zone.html')

# --- Modifier une zone de livraison ---
@gestionnaire_required
def edit_shipping_zone(request, zone_id):
    zone = get_object_or_404(ShippingZone, id=zone_id)
    if request.method == 'POST':
        zone.name = request.POST.get('name')
        zone.countries = request.POST.get('countries')
        zone.price = request.POST.get('price')
        zone.save()
        return redirect('dashboard:shipping_zones')
    return render(request, 'admin_dashboard/edit_shipping_zone.html', {
        'zone': zone
    })

def delete_shipping_zone(request, pk):
    zone = get_object_or_404(ShippingZone, pk=pk)

    if request.method == 'POST':
        zone.delete()

    return redirect('dashboard:shipping_zones')


def payment_methods(request):
    return render(request, 'admin_dashboard/payment_methods.html')
@gestionnaire_required
def billing_settings(request):
    return render(request, 'admin_dashboard/billing_settings.html')


@gestionnaire_required
def shop_info(request):
    # 1. On récupère l'instance unique (Singleton)
    shop_info = ShopInfo.get_instance()
    
    if request.method == "POST":
        # 2. On lie les données POST et FILES à l'instance
        form = ShopInfoForm(request.POST, request.FILES, instance=shop_info)
        
        # 3. On valide (UNE SEULE FOIS)
        if form.is_valid():
            form.save()
            # 4. Redirection
            # Note : Si vous voulez rester sur la page après sauvegarde, mettez 'dashboard:shop_info' ici
            return redirect('dashboard:settings') 
    else:
        # 5. En mode GET, on pré-remplit le formulaire
        form = ShopInfoForm(instance=shop_info)
    
    # 6. On envoie le formulaire et la config au template
    return render(
        request, 
        "admin_dashboard/shop_info.html", 
        {
            "form": form, 
            "config": shop_info
        }
    )
  
def blog_list_view(request):
    from shop.models import BlogPost # Assurez-vous d'importer le modèle
    blog_posts = BlogPost.objects.all().order_by('-created_at')
    return render(request, 'admin_dashboard/blog_list.html', {'blog_posts': blog_posts})


@gestionnaire_required
def blog_create_view(request):
    if request.method == 'POST':
        form = BlogPostForm(request.POST, request.FILES)
        if form.is_valid():
            post = form.save(commit=False)
            # Générer le slug automatiquement à partir du titre si vide
            if not post.slug:
                from django.utils.text import slugify
                post.slug = slugify(post.title)
            post.save()
            return redirect('dashboard:blog_posts') # Rediriger vers la liste après sauvegarde
    else:
        form = BlogPostForm()
    
    return render(request, 'admin_dashboard/blog_form.html', {'form': form})

def blog_update_view(request, pk):
    # On récupère l'article, ou on renvoie une erreur 404 s'il n'existe pas
    post = get_object_or_404(BlogPost, pk=pk)
    
    if request.method == 'POST':
        # On passe 'instance=post' pour dire au formulaire de modifier cet objet précis
        form = BlogPostForm(request.POST, request.FILES, instance=post)
        if form.is_valid():
            form.save()
            return redirect('dashboard:blog_posts')
    else:
        # On affiche le formulaire rempli avec les données de l'article
        form = BlogPostForm(instance=post)
    
    return render(request, 'admin_dashboard/blog_form.html', {'form': form})

def blog_delete_view(request, pk):
    post = get_object_or_404(BlogPost, pk=pk)
    
    if request.method == 'POST':
        # Si l'utilisateur clique sur "Oui, supprimer"
        post.delete()
        return redirect('dashboard:blog_posts')
    
    # Si c'est un GET, on affiche la page de confirmation
    return render(request, 'admin_dashboard/blog_delete.html', {'post': post})

