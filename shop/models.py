import logging
from decimal import Decimal, InvalidOperation
from django.contrib.auth.models import AbstractUser
from django.core.files.base import ContentFile
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError


from django.db import models, transaction
from django.db.models import Q
from django.conf import settings
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _

logger = logging.getLogger(__name__)


# ============================================================================
# UTILISATEURS
# ============================================================================
class User(AbstractUser):
    class Role(models.TextChoices):
        CUSTOMER = "customer", _("Client")
        GESTIONNAIRE = "gestionnaire", _("Gestionnaire")
        ADMIN = "admin", _("Administrateur")

    role = models.CharField(max_length=20, choices=Role.choices, default=Role.CUSTOMER)
    # autres champs ...

    @property
    def is_customer(self):
        return self.role == self.Role.CUSTOMER

    @property
    def is_manager(self):
        return self.role == self.Role.GESTIONNAIRE

    @property
    def is_admin_role(self):
        return self.role == self.Role.ADMIN


# ============================================================================
# CATALOGUE (Catégories, Produits, Images)
# ============================================================================

class Category(models.Model):
    name = models.CharField(max_length=200, unique=True, verbose_name="Nom")
    slug = models.SlugField(max_length=200, unique=True, blank=True)
    description = models.TextField(blank=True, verbose_name="Description")
    image = models.ImageField(upload_to='categories/', blank=True, null=True, verbose_name="Image")

    class Meta:
        verbose_name = "Catégorie"
        verbose_name_plural = "Catégories"
        ordering = ['name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('products:category_list', args=[self.slug])


class Product(models.Model):
    category = models.ForeignKey(
        Category,
        related_name='products',
        on_delete=models.PROTECT,
        verbose_name="Catégorie"
    )
    name = models.CharField(max_length=200, verbose_name="Nom du produit")
    slug = models.SlugField(unique=True, blank=True)
    image = models.ImageField(upload_to='products/', blank=True, null=True, verbose_name="Image principale")
    
    short_description = models.TextField(
        max_length=300, blank=True, verbose_name="Description courte"
    )
    description = models.TextField(blank=True, verbose_name="Description complète")

    price_ht = models.DecimalField(
        max_digits=10, decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name="Prix HT (€)"
    )
    tax_rate = models.DecimalField(
        max_digits=4, decimal_places=2,
        default=Decimal('18.00'),
        verbose_name="TVA (%)"
    )


    video = models.FileField(
        upload_to='products/videos/',
        blank=True,
        null=True,
        verbose_name="Vidéo du produit (courte)"
    )

    stock = models.PositiveIntegerField(default=0, verbose_name="Stock")
    ingredients = models.TextField(blank=True, verbose_name="Liste des ingrédients")
    available = models.BooleanField(default=True, verbose_name="Disponible")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['id', 'slug']),
            models.Index(fields=['-created_at']),
            models.Index(fields=['available']),
        ]
        verbose_name = "Produit"
        verbose_name_plural = "Produits"

    def __str__(self):
        return self.name

    @property
    def price_ttc(self):
        return self.price_ht * (Decimal('1') + self.tax_rate / Decimal('100'))

    @property
    def is_available(self):
        return self.available and self.stock > 0
    
    @property
    def stock_status(self):
        if self.stock == 0: return "Rupture"
        if self.stock < 5: return "Stock faible"
        return "Disponible"

    def save(self, *args, **kwargs):
        # Génération de slug robuste avec compteur
        if not self.slug:
            base_slug = slugify(self.name)
            slug = base_slug
            counter = 1
            while Product.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('products:product_detail', kwargs={'id': self.id, 'slug': self.slug})


class ProductImage(models.Model):
    product = models.ForeignKey(
        Product, related_name='images', on_delete=models.CASCADE
    )
    image = models.ImageField(upload_to='products/gallery/', verbose_name="Image")
    is_main = models.BooleanField(default=False, verbose_name="Image Principale")

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
        with transaction.atomic():
            super().save(*args, **kwargs)
            if self.is_main:
                # S'assurer qu'il n'y a qu'une seule image principale
                self.product.images.exclude(pk=self.pk).update(is_main=False)
            else:
                # Si aucune image principale n'existe, forcer celle-ci
                if not self.product.images.filter(is_main=True).exists():
                    self.is_main = True
                    super().save(update_fields=['is_main'])


# ============================================================================
# VENTE (Commandes, Coupons, Livraison, Paiement)
# ============================================================================




class Coupon(models.Model):
    code = models.CharField(max_length=50, unique=True)
    discount_percent = models.DecimalField(max_digits=5, decimal_places=2)
    active = models.BooleanField(default=True)
    valid_from = models.DateTimeField()
    valid_to = models.DateTimeField()

    def __str__(self):
        return self.code


class PaymentMethod(models.Model):
    name = models.CharField(max_length=100, verbose_name="Nom")
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    extra_fee = models.DecimalField(max_digits=8, decimal_places=2, default=0, verbose_name="Frais supplémentaires")
    slug = models.SlugField(blank=True, null=True)  # temporairement nullable et non unique

    def save(self, *args, **kwargs):
        if not self.slug and self.name:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

class ShippingZone(models.Model):
    name = models.CharField(
        max_length=100,
        verbose_name="Nom de la zone"
    )
    countries = models.CharField(
        max_length=300,
        verbose_name="Codes pays (ISO)",
        help_text="Séparés par des virgules. Ex: FR, SN. Utilisez 'ALL' pour le reste du monde."
    )
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name="Frais de port HT (€)"
    )
    free_shipping = models.BooleanField(default=False, verbose_name="Livraison gratuite")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Zone de livraison"
        verbose_name_plural = "Zones de livraison"
        ordering = ['price']

    def __str__(self):
        return f"{self.name} ({self.price} €)"

    def get_country_codes(self):
        """
        Retourne la liste des codes pays normalisés.
        Si 'ALL' est présent, on retourne uniquement ['ALL'].
        """
        codes = [c.strip().upper() for c in self.countries.split(',') if c.strip()]
        if "ALL" in codes:
            return ["ALL"]
        return sorted(set(codes))

    def save(self, *args, **kwargs):
        """
        Normalise les codes pays avant sauvegarde (majuscules, suppression espaces).
        """
        self.countries = ",".join(
            c.strip().upper() for c in self.countries.split(',') if c.strip()
        )
        super().save(*args, **kwargs)

    def clean(self):
        """
        Validation des codes pays : doivent être ISO alpha-2 (2 lettres),
        sauf le cas spécial 'ALL'.
        """
        codes = [c.strip().upper() for c in self.countries.split(',') if c.strip()]
        for code in codes:
            if code != "ALL" and len(code) != 2:
                raise ValidationError(f"Code pays invalide: {code}")

    @classmethod
    def get_country_choices(cls):
        zones = cls.objects.all()
        country_choices = set()
        for zone in zones:
            for code in zone.get_country_codes():
                if code == "ALL":
                    country_choices.add(('ALL', 'Autres pays (Reste du monde)'))
                else:
                    country_choices.add((code, code))
        final_choices = [('', '-- Sélectionner un pays --')]
        final_choices.extend(sorted(list(country_choices), key=lambda x: x[1]))
        return final_choices


class Order(models.Model):
    class PaymentStatus(models.TextChoices):
        PENDING = 'pending', 'En attente'
        PAID = 'paid', 'Payé'
        FAILED = 'failed', 'Échoué'
        REFUNDED = 'refunded', 'Remboursé'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL, null=True, blank=True, related_name='orders'
    )
    
    # Infos client (snapshot)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField()
    address = models.TextField()
    # --- AJOUTEZ CETTE LIGNE ---
    postal_code = models.CharField(max_length=20, verbose_name="Code postal")
    # ----------------------------
# Dans models.py -> class Order

    phone = models.CharField(max_length=20, blank=True, verbose_name="Téléphone")
    city = models.CharField(max_length=100)
    country = models.CharField(max_length=50)  # <-- ajoute ce champ

    
    # Relations
    shipping_zone = models.ForeignKey(ShippingZone, on_delete=models.SET_NULL, null=True)
    payment_method = models.ForeignKey(PaymentMethod, on_delete=models.SET_NULL, null=True)
    coupon = models.ForeignKey(Coupon, on_delete=models.SET_NULL, null=True, blank=True)

    # Champs financiers
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    vat_rate = models.DecimalField(max_digits=5, decimal_places=2, default=18)
    vat_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    shipping_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    payment_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    payment_status = models.CharField(max_length=20, choices=PaymentStatus.choices, default=PaymentStatus.PENDING)
    is_shipped = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Commande #{self.id}"

    def calculate_totals(self):
        """Recalcule tous les montants de la commande."""
        items = self.items.all()
        
        # 1. Sous-total HT
        self.subtotal = sum(item.price * item.quantity for item in items)

        # 2. TVA
        self.vat_amount = (self.subtotal * self.vat_rate) / Decimal('100')

        # 3. Réduction
        if self.coupon and self.coupon.active:
            now = timezone.now()
            if self.coupon.valid_from <= now <= self.coupon.valid_to:
                self.discount_amount = (self.subtotal * self.coupon.discount_percent) / Decimal('100')
            else:
                self.discount_amount = Decimal('0.00')
        else:
            self.discount_amount = Decimal('0.00')

        # 4. Livraison
        # 4. Livraison
        if self.shipping_zone:
            if self.shipping_zone.free_shipping:
                self.shipping_cost = Decimal('0.00')
            else:
                self.shipping_cost = self.shipping_zone.price
        else:
            self.shipping_cost = Decimal('0.00')


        # 5. Frais de paiement
        self.payment_fee = self.payment_method.extra_fee if self.payment_method else Decimal('0.00')

        # 6. Total Final
        self.total_price = (
            self.subtotal 
            + self.vat_amount 
            + self.shipping_cost 
            + self.payment_fee 
            - self.discount_amount
        )
        self.save()

    @staticmethod
    def get_shipping_cost_by_country(country_code):
        if not country_code:
            return Decimal('0.00')

        zones = ShippingZone.objects.all()

        for zone in zones:
            codes = zone.get_country_codes()
            if country_code.upper() in codes or "ALL" in codes:
                if zone.free_shipping:
                    return Decimal('0.00')
                return zone.price

        return Decimal('0.00')

        


class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name="items", on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    
    # Snapshot pour historique
    product_name = models.CharField(max_length=200)
    price = models.DecimalField(max_digits=10, decimal_places=2) # Prix HT au moment de l'achat
    quantity = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f"{self.product_name} ({self.quantity})"

    @property
    def total_price(self):
        return self.price * self.quantity

    def calculate_shipping(self):
        if self.shipping_zone:
            if self.shipping_zone.free_shipping:
                return Decimal('0.00')
            return self.shipping_zone.price
        return Decimal('0.00')


# ============================================================================
# COMPTABILITÉ & FACTURATION
# ============================================================================

class Transaction(models.Model):
    class TypeChoices(models.TextChoices):
        INCOME = 'income', 'Encaissement'
        EXPENSE = 'expense', 'Dépense'
        REFUND = 'refund', 'Remboursement'
        FEE = 'fee', 'Frais plateforme'

    order = models.ForeignKey(Order, on_delete=models.SET_NULL, null=True, blank=True, related_name='transactions')
    external_reference = models.CharField(max_length=150, blank=True, null=True)
    date = models.DateTimeField(auto_now_add=True)
    description = models.CharField(max_length=255)
    type = models.CharField(max_length=20, choices=TypeChoices.choices)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, default='pending')

    def __str__(self):
        return f"{self.get_type_display()} - {self.amount} €"


class BillingSettings(models.Model):
    company_name = models.CharField(max_length=255)
    company_address = models.TextField()
    company_phone = models.CharField(max_length=50, blank=True)
    company_email = models.EmailField(blank=True)
    rccm = models.CharField(max_length=100, blank=True)
    ninea = models.CharField(max_length=100, blank=True)
    logo = models.ImageField(upload_to='billing/', blank=True, null=True)
    currency = models.CharField(max_length=10, default="XOF")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Paramètres de facturation"

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def get_instance(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def __str__(self):
        return "Configuration Facturation"


class Invoice(models.Model):
    order = models.OneToOneField(Order, on_delete=models.PROTECT, related_name='invoice')
    number = models.CharField(max_length=50, unique=True, verbose_name="Numéro de facture")
    created_at = models.DateTimeField(auto_now_add=True)
    pdf_file = models.FileField(upload_to='invoices/%Y/%m/', blank=True, null=True)
    total_ht = models.DecimalField(max_digits=10, decimal_places=2)
    total_tva = models.DecimalField(max_digits=10, decimal_places=2)
    total_ttc = models.DecimalField(max_digits=10, decimal_places=2)
    is_sent = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Facture {self.number}"

    def generate_number(self):
        now = timezone.now()
        year = now.year
        with transaction.atomic():
            count = Invoice.objects.select_for_update().filter(created_at__year=year).count() + 1
            return f"FAC-{year}-{str(count).zfill(4)}"

    def save(self, *args, **kwargs):
        if not self.number:
            self.number = self.generate_number()
        super().save(*args, **kwargs)

    def generate_pdf(self):
        # Nécessite WeasyPrint installé
        try:
            html_string = render_to_string('accounting/invoice_detail.html', {'invoice': self})
            html = HTML(string=html_string, base_url=settings.MEDIA_ROOT)
            pdf_content = html.write_pdf()
            filename = f"Facture_{self.number}.pdf"
            self.pdf_file.save(filename, ContentFile(pdf_content), save=True)
            logger.info(f"PDF généré pour {self.number}")
        except Exception as e:
            logger.error(f"Erreur génération PDF {self.number}: {e}")


# ============================================================================
# MARKETING & CONTENU
# ============================================================================




class BlogPost(models.Model):
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name='posts')
    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, max_length=255)
    excerpt = models.TextField(help_text="Texte court affiché sur la carte")
    content = models.TextField(blank=True)
    image = models.ImageField(upload_to='blog/')
    meta_title = models.CharField(max_length=255, blank=True)
    meta_description = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.title)
            slug = base_slug
            counter = 1
            while BlogPost.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)


class Banner(models.Model):
    image = models.ImageField(upload_to='shop_banners/')
    title = models.CharField(max_length=200, blank=True)
    subtitle = models.CharField(max_length=200, blank=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']
        verbose_name = "Bannière"
        verbose_name_plural = "Bannières"

    def __str__(self):
        return self.title if self.title else f"Bannière #{self.id}"


class ShopInfo(models.Model):
    promo_image = models.ImageField(upload_to='shop_info/', blank=True, null=True)
    promo_text = models.TextField(blank=True)

    about_image = models.ImageField(upload_to='shop_info/', blank=True, null=True)
    about_title = models.CharField(max_length=200, blank=True)
    about_description = models.TextField(blank=True)

    newsletter_bg_image = models.ImageField(upload_to='newsletter/', blank=True, null=True)
    newsletter_title = models.CharField(max_length=200, default="Rejoignez la communauté")
    newsletter_text = models.CharField(max_length=255, default="Recevez nos conseils...")

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Informations Boutique"

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def get_instance(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def __str__(self):
        return "Configuration Boutique"


class SiteSettings(models.Model):
    site_name = models.CharField(max_length=200, default="Ma Boutique")
    contact_email = models.EmailField()
    contact_phone = models.CharField(max_length=50, blank=True)
    vat_rate = models.DecimalField(max_digits=5, decimal_places=2, default=18)
    currency = models.CharField(max_length=10, default="FCFA")
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return "Paramètres du site"