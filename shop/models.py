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
    image = models.ImageField(
        upload_to='products/',
        blank=True,
        null=True,
        verbose_name="Image principale"
    )

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
        default=Decimal('0.00'),
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
    product = models.ForeignKey(Product, related_name='gallery', on_delete=models.CASCADE)
    image = models.ImageField(upload_to='products/gallery/', verbose_name="Image")

    class Meta:
        ordering = ['id']

    def __str__(self):
        return f"Image de {self.product.name}"



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

    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    extra_fee = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=0
    )

    slug = models.SlugField(unique=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name




# 🇸🇳 Zones de livraison Sénégal

SENEGAL_ZONES = {

    # =======================
    # VILLE DE DAKAR (Centre)
    # =======================
    "DAKAR_PLATEAU": "Dakar-Plateau",
    "MEDINA": "Médina",
    "FANN_POINT_E_AMITIE": "Fann - Point E - Amitié",
    "FASS_COLOBANE": "Gueule Tapée - Fass - Colobane",
    "GRAND_DAKAR": "Grand Dakar",
    "BISCUTERIE": "Biscuiterie",
    "HLM": "HLM",
    "DIEUPPEUL_DERKLE": "Dieuppeul - Derklé",
    "LIBERTE": "Liberté",
    "CAMBERENE": "Cambérène",
    "PARCELLES_ASSAINIES": "Parcelles Assainies",
    "YOFF": "Yoff",
    "OUAKAM": "Ouakam",
    "NGOR": "Ngor",
    "PATTE_D_OIE": "Patte d'Oie",
    "HANN_BEL_AIR": "Hann Bel Air",
    "SICAP_LIBERTE": "Sicap Liberté",
    "GRAND_YOFF": "Grand Yoff",
    "MBAO": "Mbao",

    # =======================
    # PIKINE & GUÉDIAWAYE (Banlieue Ouest)
    # =======================
    "PIKINE_NORD": "Pikine Nord",
    "PIKINE_OUEST": "Pikine Ouest",
    "PIKINE_EST": "Pikine Est",
    "PIKINE_SUD": "Pikine Sud",
    "THIAROYE_SUR_MER": "Thiaroye Sur Mer",
    "THIAROYE_GUEDEYE": "Thiaroye Guédé",
    "DJIDDAH_THIAROYE_KAO": "Djiddah Thiaroye Kao",
    "YEUMBEUL_NORD": "Yeumbeul Nord",
    "YEUMBEUL_SUD": "Yeumbeul Sud",
    "GUEDIAWAYE": "Guédiawaye",
    "MALIKA": "Malika",
    "KEUR_MASSAR": "Keur Massar",

    # =======================
    # RUFISQUE (Banlieue Est)
    # =======================
    "RUFISQUE": "Rufisque",
    "BARGNY": "Bargny",
    "DIAMNIADIO": "Diamniadio",
    "SEBIKHOTANE": "Sébikhotane",
    "YENE": "Yène",
    "BAMBYLOR": "Bambylor",
    "TIVAOUANE_PEULH": "Tivaouane Peulh",
    "SENTOBE": "Sentobe",
    "JAXAAY": "Jaxaay",
    "DIENDER": "Diender",

    # ====== AUTRES RÉGIONS ======
    "THIES": "Thiès",
    "DIOURBEL": "Diourbel",
    "FATICK": "Fatick",
    "KAOLACK": "Kaolack",
    "KOLDA": "Kolda",
    "LOUGA": "Louga",
    "MATAM": "Matam",
    "SAINT_LOUIS": "Saint-Louis",
    "TAMBACOUNDA": "Tambacounda",
    "ZIGUINCHOR": "Ziguinchor",
    "KEDOUGOU": "Kédougou",
    "SEDHIOU": "Sédhiou",
    "KAFFRINE": "Kaffrine",
    "INTERNATIONAL": "International (Hors Sénégal)",
}

class ShippingZone(models.Model):

    name = models.CharField(
        max_length=100,
        verbose_name="Nom de la zone"
    )

    zones = models.CharField(
        max_length=500,
        verbose_name="Zones couvertes",
        help_text="Séparées par des virgules. Exemple : DAKAR_PLATEAU, THIES"
    )

    price = models.DecimalField(
        max_digits=10,
        decimal_places=0,
        validators=[MinValueValidator(Decimal('0'))],
        verbose_name="Frais de livraison (FCFA)"
    )

    free_shipping = models.BooleanField(
        default=False,
        verbose_name="Livraison gratuite"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Zone de livraison"
        verbose_name_plural = "Zones de livraison"
        ordering = ['price']

    def __str__(self):
        if self.free_shipping:
            return f"{self.name} (Gratuit)"
        return f"{self.name} ({self.price} FCFA)"

    # 🔹 Nettoyage automatique
    def save(self, *args, **kwargs):
        self.zones = ",".join(
            z.strip().upper() for z in self.zones.split(",") if z.strip()
        )
        super().save(*args, **kwargs)

    # 🔹 Retourne liste propre
    def get_zone_codes(self):
        return sorted(set(
            z.strip().upper() for z in self.zones.split(",") if z.strip()
        ))

    # 🔹 Validation
    def clean(self):
        codes = [z.strip().upper() for z in self.zones.split(",") if z.strip()]
        for code in codes:
            if code not in SENEGAL_ZONES:
                raise ValidationError(f"Zone invalide : {code}")

    # 🔹 Choix pour formulaire
    @classmethod
    def get_zone_choices(cls):
        choices = [('', '-- Sélectionner votre zone --')]
        for code, name in SENEGAL_ZONES.items():
            choices.append((code, name))
        return choices

    # 🔹 Calcul automatique
    @classmethod
    def get_shipping_for_zone(cls, zone_code):
        for zone in cls.objects.all():
            if zone_code in zone.get_zone_codes():
                if zone.free_shipping:
                    return 0
                return zone.price
        return 0
    

    
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
    zone = models.CharField(max_length=50, verbose_name="Zone de livraison")



    # Relations
    shipping_zone = models.ForeignKey(ShippingZone, on_delete=models.SET_NULL, null=True)
    payment_method = models.ForeignKey(PaymentMethod, on_delete=models.SET_NULL, null=True)
    coupon = models.ForeignKey(Coupon, on_delete=models.SET_NULL, null=True, blank=True)

    # Champs financiers
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    vat_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    vat_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    shipping_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    payment_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    transaction_id = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        db_index=True,
        verbose_name="Transaction PayDunya"
    )
    gateway = models.CharField(
    max_length=50,
    blank=True,
    null=True,
    db_index=True,
    verbose_name="Passerelle de paiement"
    )
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

        # 2. TVA (Mise à 0)
        self.vat_amount = Decimal('0.00')

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

 # RENOMMAGE ET CORRECTION DE LA MÉTHODE
    @staticmethod
    def get_shipping_cost_by_zone(zone_code):
        if not zone_code:
            return Decimal('0.00')

        zones = ShippingZone.objects.all()

        for zone in zones:
            # CORRECTION ICI : on utilise get_zone_codes()
            codes = zone.get_zone_codes()
            if zone_code.upper() in codes:
                if zone.free_shipping:
                    return Decimal('0.00')
                return zone.price

        return Decimal('0.00')



class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name="items", on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, blank=True)
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

    class StatusChoices(models.TextChoices):
        PENDING = "pending", "En attente"
        COMPLETED = "completed", "Complété"
        FAILED = "failed", "Échoué"

    order = models.ForeignKey(
        Order,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='transactions'
    )

    external_reference = models.CharField(
        max_length=150,
        blank=True,
        null=True,
        unique=True,
        db_index=True
    )

    payment_method = models.CharField(max_length=50, blank=True, null=True)

    date = models.DateTimeField(auto_now_add=True)

    description = models.CharField(max_length=255)

    type = models.CharField(max_length=20, choices=TypeChoices.choices)

    amount = models.DecimalField(max_digits=10, decimal_places=2)

    status = models.CharField(
        max_length=20,
        choices=StatusChoices.choices,
        default=StatusChoices.PENDING,
        db_index=True
    )

    def __str__(self):
        return f"{self.get_type_display()} - {self.amount} FCFA"


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



# Dans models.py

from django.db import models
from django.utils.text import slugify

class Video(models.Model):
    # --- AJOUT : Relation Catégorie ---
    category = models.ForeignKey(
        'Category',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='videos',
        verbose_name="Catégorie"
    )

    title = models.CharField(max_length=200, verbose_name="Titre de la vidéo")
    slug = models.SlugField(unique=True, max_length=255, blank=True)
    description = models.TextField(verbose_name="Description", blank=True)

    # Fichier vidéo uploadé
    video_file = models.FileField(
        upload_to='videos/',
        verbose_name="Fichier Vidéo (MP4)",
        blank=True,
        null=True
    )

    # --- AJOUT : Lien externe (optionnel) ---
    video_url = models.URLField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name="Lien Vidéo (YouTube/Vimeo)"
    )

    # --- AJOUT : Image / Miniature ---
    image = models.ImageField(
        upload_to='videos/thumbnails/',
        blank=True,
        null=True,
        verbose_name="Miniature (Image)"
    )

    is_active = models.BooleanField(default=True, verbose_name="Actif")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Vidéo"
        verbose_name_plural = "Vidéos"

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.title)
            slug = base_slug
            counter = 1
            while Video.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

class Banner(models.Model):
    image = models.ImageField(upload_to='shop_banners/')
    title = models.CharField(max_length=200, blank=True)
    subtitle = models.CharField(max_length=200, blank=True)

    # --- AJOUT : Lien vers le produit ---
    product = models.ForeignKey(
        'Product',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Produit associé",
        help_text="Produit vers lequel le bouton 'Découvrir' redirigera."
    )
    # -------------------------------------

    order = models.PositiveIntegerField(default=0)
    # Optionnel : Ajouter un champ actif si vous voulez filtrer les bannières
    # is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['order']
        verbose_name = "Bannière"
        verbose_name_plural = "Bannières"

    def __str__(self):
        return self.title if self.title else f"Bannière #{self.id}"


class ShopInfo(models.Model):
    # ==============================
    # CATÉGORIES
    # ==============================
    categories_title = models.CharField(max_length=200, blank=True)
    categories_subtitle = models.CharField(max_length=200, blank=True)

    # ==============================
    # FEATURES
    # ==============================
    features_title = models.CharField(max_length=200, blank=True)
    features_subtitle = models.CharField(max_length=200, blank=True)

    # ==============================
    # PRODUITS
    # ==============================
    products_title = models.CharField(max_length=200, blank=True)
    products_subtitle = models.CharField(max_length=200, blank=True)

    # ==============================
    # PROMO
    # ==============================
    promo_title = models.CharField(max_length=200, blank=True)
    promo_subtitle = models.CharField(max_length=200, blank=True)
    promo_image = models.ImageField(upload_to='shop_info/', blank=True, null=True)
    promo_text = models.TextField(blank=True)

    # ==============================
    # TRUST
    # ==============================
    trust_title = models.CharField(max_length=200, blank=True)
    trust_subtitle = models.CharField(max_length=200, blank=True)

    # ==============================
    # ABOUT
    # ==============================
    about_image = models.ImageField(upload_to='shop_info/', blank=True, null=True)
    about_title = models.CharField(max_length=200, blank=True)
    about_description = models.TextField(blank=True)
    signature = models.CharField(max_length=100, blank=True)

    # ==============================
    # NEWSLETTER
    # ==============================
    newsletter_bg_image = models.ImageField(upload_to='newsletter/', blank=True, null=True)
    newsletter_title = models.CharField(max_length=200, default="Rejoignez la communauté")
    newsletter_text = models.CharField(max_length=255, default="Recevez nos conseils...")

    # ==============================
    # BIEN-ÊTRE (WELLNESS PAGE)
    # ==============================
    wellness_hero_title = models.CharField(max_length=255, default="Sérénité & Équilibre", blank=True, verbose_name="Titre Hero Bien-être")
    wellness_hero_subtitle = models.CharField(max_length=255, default="Retrouvez votre harmonie naturelle...", blank=True, verbose_name="Sous-titre Hero")
# Dans models.py -> class ShopInfo

# Ajoutez ce champ avec les autres champs "wellness"
    wellness_hero_bg = models.ImageField(
        upload_to='shop_info/',
        blank=True,
        null=True,
        verbose_name="Image de fond Hero"
    )
    wellness_philosophy_title = models.CharField(max_length=255, default="Notre Philosophie", blank=True, verbose_name="Titre Philosophie")
    wellness_philosophy_text = models.TextField(default="Chez Terra & Pure...", blank=True, verbose_name="Texte Philosophie")

    wellness_image_break = models.ImageField(upload_to='shop_info/', blank=True, null=True, verbose_name="Image de séparation")

    wellness_cta_title = models.CharField(max_length=255, default="Prêt à commencer votre transformation ?", blank=True, verbose_name="Titre Appel à l'action")
    wellness_cta_text = models.CharField(max_length=255, default="Rejoignez notre communauté bien-être.", blank=True, verbose_name="Texte Appel à l'action")
    about_hero_title = models.CharField(max_length=200, blank=True, default="Retour aux sources")
    about_hero_subtitle = models.CharField(max_length=255, blank=True, default="Une aventure...")
    process_title = models.CharField(max_length=200, blank=True, default="De la plante au pot")
    process_subtitle = models.TextField(blank=True, default="Un processus lent...")
    step1_text = models.CharField(max_length=100, blank=True, default="Cueillette à la main")
    step2_text = models.CharField(max_length=100, blank=True, default="Macération à froid")
    step3_text = models.CharField(max_length=100, blank=True, default="Conditionnement artisanal")
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
    addresse = models.CharField(max_length=200, blank=True)

    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return "Paramètres du site"


class Feature(models.Model):
    title = models.CharField(max_length=150)
    description = models.TextField()
    icon_class = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return self.title


class Feature1(models.Model):
    title = models.CharField(max_length=150)
    description = models.TextField()
    icon_class = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return self.title

class Feature_about(models.Model):
    title = models.CharField(max_length=150)
    description = models.TextField()
    icon_class = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return self.title

class TeamMember(models.Model):
    name = models.CharField(max_length=100, verbose_name="Nom")
    role = models.CharField(max_length=100, verbose_name="Rôle")
    bio = models.TextField(verbose_name="Biographie courte")
    photo = models.ImageField(upload_to='team/', blank=True, null=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']
        verbose_name = "Membre de l'équipe"

    def __str__(self):
        return self.name


class StaticPage(models.Model):
    title = models.CharField(max_length=200, verbose_name="Titre")
    slug = models.SlugField(unique=True, max_length=255, blank=True)
    content = models.TextField(verbose_name="Contenu")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Page Statique"
        verbose_name_plural = "Pages Statiques"

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)


class NewsletterSubscriber(models.Model):
    email = models.EmailField(unique=True, verbose_name="Email")
    # CORRECTION ICI : auto_now_add au lieu de auto_now_now
    subscribed_at = models.DateTimeField(auto_now_add=True, verbose_name="Date d'inscription")

    class Meta:
        verbose_name = "Abonné Newsletter"
        verbose_name_plural = "Abonnés Newsletter"

    def __str__(self):
        return self.email
