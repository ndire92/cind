from django.db import models
from django.contrib.auth import get_user_model # Standard pour l'utilisateur
from django.urls import reverse
from decimal import Decimal, InvalidOperation
from django.conf import settings
from django.core.validators import MinValueValidator
from django.utils import timezone
from django.contrib.auth.models import User
from decimal import Decimal
from django.utils.text import slugify
from django.contrib.auth.models import AbstractUser
from django.db.models import Q

from decimal import Decimal

class User(AbstractUser):
    ROLE_CHOICES = (
        ('customer', 'Customer'),
        ('gestionnaire', 'Gestionnaire'),
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='customer')
    profile_image = models.ImageField(upload_to='profiles/', null=True, blank=True)

    def save(self, *args, **kwargs):
        if self.role:
            self.role = self.role.lower()  # normaliser les valeurs
        super().save(*args, **kwargs)

# Pour la génération de PDF (WeasyPrint)
try:
    from weasyprint import HTML
    from django.template.loader import render_to_string
    from django.core.files import ContentFile
    from django.conf import settings
    HAS_WEASYPRINT = True
except ImportError:
    HAS_WEASYPRINT = False



class Category(models.Model):
    name = models.CharField(max_length=200, verbose_name="Nom")
    slug = models.SlugField(max_length=200, unique=True, verbose_name="Slug (URL)")
    description = models.TextField(blank=True, verbose_name="Description")
    image = models.ImageField(upload_to='categories/', blank=True, null=True, verbose_name="Image")

    class Meta:
        verbose_name = "Catégorie"
        verbose_name_plural = "Catégories"
        ordering = ['name']

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        # Assurez-vous d'avoir une url nommée 'products:category_list'
        # ou changez par 'shop:category' selon votre fichier urls.py
        return reverse('products:category_list', args=[self.slug])



class Product(models.Model):
    category = models.ForeignKey(
        "Category",
        related_name='products',
        on_delete=models.CASCADE,
        verbose_name="Catégorie"
    )

    name = models.CharField(max_length=200, verbose_name="Nom du produit")
    slug = models.SlugField(unique=True, blank=True)

    image = models.ImageField(upload_to='products/', blank=True, null=True)


    short_description = models.TextField(
        max_length=300,
        blank=True,
        verbose_name="Description courte",
        help_text="Affichée sous le prix"
    )
    description = models.TextField(blank=True, verbose_name="Description complète")

    price_ht = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="Prix HT (€)"
    )

    tax_rate = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=Decimal('20.00'),
        verbose_name="TVA (%)"
    )

    stock = models.PositiveIntegerField(default=0, verbose_name="Stock")
    available = models.BooleanField(default=True, verbose_name="Disponible")

    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created']
        verbose_name = "Produit"
        verbose_name_plural = "Produits"

    def __str__(self):
        return self.name

    @property
    def price_ttc(self):
        if self.price_ht is None or self.tax_rate is None:
            return None
        return Decimal(self.price_ht) * (Decimal('1') + Decimal(self.tax_rate) / Decimal('100'))

    @property
    def is_available(self):
        return self.available and self.stock > 0


    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name)
            slug = base_slug
            counter = 1
            while Product.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)   # <-- bien indenté dans la classe




    def get_absolute_url(self):
        return reverse('products:product_detail', kwargs={'id': self.id, 'slug': self.slug})


class ProductImage(models.Model):
    product = models.ForeignKey(
        "Product",
        related_name='images',
        on_delete=models.CASCADE,
        verbose_name="Produit"
    )

    image = models.ImageField(
        upload_to='products/gallery/',
        verbose_name="Image"
    )

    is_main = models.BooleanField(
        default=False,
        verbose_name="Image Principale"
    )

    class Meta:
        ordering = ['-is_main']
        constraints = [
            models.UniqueConstraint(
                fields=['product'],
                condition=Q(is_main=True),
                name='unique_main_image_per_product'
            )
        ]

    def __str__(self):
        return f"Image de {self.product.name}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        # Si cette image est définie comme principale
        if self.is_main:
            # Désactiver toutes les autres images principales
            self.product.images.exclude(pk=self.pk).update(is_main=False)

        else:
            # Si aucune image principale n'existe, forcer celle-ci
            if not self.product.images.filter(is_main=True).exists():
                self.is_main = True
                super().save(update_fields=['is_main'])


# Retirez l'import Decimal si vous ne l'utilisez plus ailleurs
# from decimal import Decimal 

class ShippingZone(models.Model):
    name = models.CharField(
        max_length=100,
        verbose_name="Nom de la zone",
        help_text="Ex: France, International..."
    )
    countries = models.CharField(
        max_length=300,
        verbose_name="Codes pays (ISO)",
        help_text="Séparés par des virgules. Ex: FR,MC. Utilisez 'ALL' pour le reste du monde."
    )
    
    # --- CHANGEMENT ICI ---
    # On remplace DecimalField par FloatField
    price = models.FloatField(
        verbose_name="Frais de port HT (€)"
    )

    class Meta:
        verbose_name = "Zone de livraison"
        verbose_name_plural = "Zones de livraison"
        ordering = ['price']

    def __str__(self):
        return f"{self.name} ({self.price}€)"

    def get_country_codes(self):
        codes = [c.strip().upper() for c in self.countries.split(',')]
        return codes if "ALL" not in codes else ["ALL"]

    def save(self, *args, **kwargs):
        # Normalise les codes pays
        self.countries = ",".join(
            c.strip().upper() for c in self.countries.split(',')
        )

        # --- LOGIQUE SIMPLIFIÉE POUR FLOAT ---
        if isinstance(self.price, str):
            try:
                # Remplace la virgule par un point (12,50 -> 12.5)
                self.price = float(self.price.replace(',', '.'))
            except ValueError:
                # Si ça échoue, on met 0 par défaut pour ne pas planter
                self.price = 0.0

        super().save(*args, **kwargs)

# --- COMMANDES ---from decimal import Decimal, InvalidOperation

class Order(models.Model):

    PAYMENT_CHOICES = (
        ('PAYDUNYA', 'Paiement en ligne (PayDunya)'),
        ('COD', 'Paiement à la livraison'),
    )

    PAYMENT_STATUS_CHOICES = (
        ('PENDING', 'En attente'),
        ('PAID', 'Payé'),
        ('FAILED', 'Échoué'),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='orders'
    )

    first_name = models.CharField(max_length=50, verbose_name="Prénom")
    last_name = models.CharField(max_length=50, verbose_name="Nom")
    email = models.EmailField(verbose_name="Email")
    address = models.CharField(max_length=250, verbose_name="Adresse")
    postal_code = models.CharField(max_length=20, verbose_name="Code Postal")
    city = models.CharField(max_length=100, verbose_name="Ville")

    shipping_zone = models.ForeignKey(
        'shop.ShippingZone',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='orders',
        verbose_name="Zone de livraison"
    )

    country = models.CharField(
        max_length=100,
        default="France",
        verbose_name="Pays (ISO)"
    )

    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_CHOICES,
        default='PAYDUNYA',
        verbose_name="Mode de paiement"
    )

    payment_status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS_CHOICES,
        default='PENDING',
        verbose_name="Statut de paiement"
    )

    shipping_cost = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=Decimal('0.00'),
        null=False,
        blank=False
    )

    total_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        null=False,
        blank=False
    )

    created = models.DateTimeField(auto_now_add=True, verbose_name="Créée le")
    updated = models.DateTimeField(auto_now=True, verbose_name="Mise à jour")

    paid = models.BooleanField(default=False, verbose_name="Payée")
    is_shipped = models.BooleanField(default=False, verbose_name="Expédiée")

    class Meta:
        ordering = ['-created']
        verbose_name = "Commande"
        verbose_name_plural = "Commandes"

    def __str__(self):
        return f'Commande {self.id} - {self.first_name} {self.last_name}'

    # --------------------------------------------------
    # SHIPPING
    # --------------------------------------------------

    @staticmethod
    def get_shipping_cost_by_country(country_code):
        """
        Retourne le prix de port en fonction du pays.
        Toujours renvoyer un Decimal.
        """
        if not country_code:
            return Decimal('0.00')

        # Exemple de logique
        if country_code == "France":
            return Decimal('10.00')

        return Decimal('20.00')

    # --------------------------------------------------
    # SAVE
    # --------------------------------------------------

    def save(self, *args, **kwargs):
        """
        Sécurise le shipping_cost avant sauvegarde.
        """
        if self.shipping_cost is None:
            self.shipping_cost = Decimal('0.00')

        super().save(*args, **kwargs)

    # --------------------------------------------------
    # CALCULS
    # --------------------------------------------------

    def get_total_products(self):
        """
        Somme sécurisée des produits.
        """
        from decimal import Decimal

        total = sum(
            (item.get_cost() for item in self.items.all()),
            Decimal('0.00')  # IMPORTANT : éviter sum() avec int
        )

        return total

    def get_total_cost(self):
        """
        Total HT = Produits + Frais de port
        """
        products = self.get_total_products()
        shipping = self.shipping_cost or Decimal('0.00')

        return products + shipping

    def get_total_ttc(self, tva_rate=Decimal('0.18')):
        """
        Total TTC = HT + TVA
        """
        try:
            tva_rate = Decimal(str(tva_rate))
        except (InvalidOperation, TypeError):
            tva_rate = Decimal('0.00')

        total_ht = self.get_total_cost()
        multiplier = Decimal('1.00') + tva_rate
        total_ttc = total_ht * multiplier

        return total_ttc.quantize(Decimal('0.01'))

    # --------------------------------------------------
    # SNAPSHOT (optionnel mais recommandé)
    # --------------------------------------------------

    def update_total_snapshot(self):
        """
        Met à jour le total_price sauvegardé en base.
        À appeler après ajout/suppression d'items.
        """
        self.total_price = self.get_total_cost()
        self.save(update_fields=['total_price'])


# --- LIGNES DE COMMANDE ---
class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey('Product', related_name='order_items', on_delete=models.CASCADE)
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Prix HT unitaire",default=Decimal("0.00"))
    quantity = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])

    class Meta:
        verbose_name = "Ligne de commande"
        verbose_name_plural = "Lignes de commande"

    def __str__(self):
        return f"{self.quantity}x {self.product.name}"

    def get_cost(self):
        """Retourne le prix de CETTE ligne uniquement"""
        if self.price is None:
            return Decimal("0.00")
        return self.price * self.quantity

class Invoice(models.Model):
    order = models.OneToOneField(Order, on_delete=models.PROTECT, related_name='invoice')
    
    number = models.CharField(max_length=50, unique=True, verbose_name="Numéro de facture")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Date de facturation")
    
    pdf_file = models.FileField(upload_to='invoices/%Y/%m/', blank=True, null=True, verbose_name="Fichier PDF")
    
    total_ht = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Total HT")
    total_tva = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Total TVA")
    total_ttc = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Total TTC")
    
    is_sent = models.BooleanField(default=False, verbose_name="Envoyée au client")

    class Meta:
        verbose_name = "Facture"
        verbose_name_plural = "Factures"
        ordering = ['-created_at']

    def __str__(self):
        return f"Facture {self.number}"

    def generate_number(self):
        # Utilise timezone.now pour être sûr d'avoir la bonne date
        now = timezone.now()
        year = now.year
            
        # Simple compteur annuel
        count = Invoice.objects.filter(created_at__year=year).count() + 1
        return f"FAC-{year}-{str(count).zfill(3)}"
    
    def save(self, *args, **kwargs):
        if not self.number:
            self.number = self.generate_number()
        super().save(*args, **kwargs)

    def generate_pdf(self):
        if not HAS_WEASYPRINT:
            print(f"Impossible de générer le PDF pour {self.number} : librairie indisponible.")
            return

        # Assurez-vous que le template existe (accounting/invoice_detail.html)
        try:
            html_string = render_to_string('accounting/invoice_detail.html', {'invoice': self})
            
            html = HTML(string=html_string, base_url=settings.MEDIA_ROOT)
            result = html.write_pdf()
            
            filename = f"Facture_{self.number}.pdf"
            self.pdf_file.save(filename, ContentFile(result), save=True)
        except Exception as e:
            print(f"Erreur génération PDF: {e}")



class Transaction(models.Model):
    TYPE_CHOICES = (
        ('income', 'Encaissement'),
        ('expense', 'Dépense'),
    )
    STATUS_CHOICES = (
        ('paid', 'Payé'),
        ('pending', 'En attente'),
    )

    date = models.DateTimeField(auto_now_add=True)
    description = models.CharField(max_length=255)
    type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='paid')

    def __str__(self):
        return f"{self.type} - {self.amount} €"

class ShopInfo(models.Model):
    # Slide 1
    banner1_image = models.ImageField(upload_to='shop_info/', blank=True, null=True)
    banner1_title = models.CharField(max_length=200, blank=True)
    banner1_subtitle = models.CharField(max_length=200, blank=True)

    # Slide 2
    banner2_image = models.ImageField(upload_to='shop_info/', blank=True, null=True)
    banner2_title = models.CharField(max_length=200, blank=True)
    banner2_subtitle = models.CharField(max_length=200, blank=True)

    # Slide 3
    banner3_image = models.ImageField(upload_to='shop_info/', blank=True, null=True)
    banner3_title = models.CharField(max_length=200, blank=True)
    banner3_subtitle = models.CharField(max_length=200, blank=True)

    # Slide 4
    banner4_image = models.ImageField(upload_to='shop_info/', blank=True, null=True)
    banner4_title = models.CharField(max_length=200, blank=True)
    banner4_subtitle = models.CharField(max_length=200, blank=True)

    # Promo et À propos (comme tu as déjà)
    promo_image = models.ImageField(upload_to='shop_info/', blank=True, null=True)
    promo_text = models.TextField(blank=True)
    about_image = models.ImageField(upload_to='shop_info/', blank=True, null=True)
    about_title = models.CharField(max_length=200, blank=True)
    about_description = models.TextField(blank=True)
    # ... vos champs existants ...

    newsletter_bg_image = models.ImageField(
        upload_to='newsletter/', 
        verbose_name="Image de fond Newsletter", 
        blank=True, 
        null=True
    )
    
    # AJOUTEZ CES DEUX LIGNES MANQUANTES :
    newsletter_title = models.CharField(max_length=200, verbose_name="Titre Newsletter", default="Rejoignez la communauté")
    newsletter_text = models.CharField(max_length=255, verbose_name="Texte Newsletter", default="Recevez nos conseils...")

    updated_at = models.DateTimeField(auto_now=True)
    # ... fin de la classe ...

    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def get_instance(cls):
        obj, created = cls.objects.get_or_create(pk=1)
        return obj

        


class BlogPost(models.Model):
    category = models.CharField(max_length=50, verbose_name="Catégorie", default="Bien-être")
    title = models.CharField(max_length=200, verbose_name="Titre de l'article")
    slug = models.SlugField(unique=True, max_length=255, verbose_name="Slug (URL)")
    excerpt = models.TextField(verbose_name="Extrait (Résumé)", help_text="Texte court affiché sur la carte")
    content = models.TextField(verbose_name="Contenu complet", blank=True)
    image = models.ImageField(upload_to='blog/', verbose_name="Image de l'article")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Date de création")
    is_active = models.BooleanField(default=True, verbose_name="Publié")

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Article de Blog"
        verbose_name_plural = "Articles de Blog"

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)
