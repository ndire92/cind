from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

# Importation des modèles (ajustez le nom de l'app si nécessaire, ex: from .models import ...)
from .models import (
    User, Category, Product, ProductImage,
    ShippingZone, Coupon, PaymentMethod,
    Order, OrderItem,
    Transaction, Invoice, BillingSettings,Feature1,
     BlogPost,
    Banner, ShopInfo, SiteSettings
)


# ============================================================================
# CONFIGURATION UTILISATEUR
# ============================================================================

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    # --- Champs à afficher dans la liste ---
    list_display = ('username', 'email', 'role_colored', 'is_staff', 'is_active')

    # --- Filtres sur le côté ---
    list_filter = ('role', 'is_staff', 'is_active')

    # --- Recherche ---
    search_fields = ('username', 'email')


    # --- Champs personnalisés ---
    fieldsets = (
        ('Informations personnelles', {'fields': ('username', 'email', 'role')}),
        ('Permissions', {'fields': ('is_staff', 'is_active', 'is_superuser')}),

    )

    # --- Méthode pour colorer le rôle ---
    def role_colored(self, obj):
        color = 'gray'
        if obj.is_admin_role:
            color = 'red'
        elif obj.is_manager:
            color = 'orange'
        elif obj.is_customer:
            color = 'green'
        return format_html(
            '<span style="color:{}; font-weight:bold;">{}</span>',
            color,
            obj.get_role_display()
        )
    role_colored.short_description = 'Rôle'
    role_colored.admin_order_field = 'role'


# ============================================================================
# INLINES (Édition imbriquée)
# ============================================================================

class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1
    fields = ('image', 'is_main', 'image_tag')
    readonly_fields = ('image_tag',)

    def image_tag(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="width: 45px; height: 45px; object-fit: cover; border-radius: 5px;" />', obj.image.url)
        return "-"
    image_tag.short_description = "Aperçu"


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('product_name', 'price', 'quantity', 'total_price')
    fields = ('product_name', 'quantity', 'price', 'total_price')

    def total_price(self, obj):
        return f"{obj.total_price} €"
    total_price.short_description = "Sous-total"

    # Empêcher la modification des items depuis l'admin pour préserver l'intégrité
    # (sauf si vous savez exactement ce que vous faites)
    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


# ============================================================================
# CATALOGUE
# ============================================================================

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'image_preview')
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name',)

    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="width: 40px; height: 40px; object-fit: cover;" />', obj.image.url)
        return "-"
    image_preview.short_description = "Image"


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'price_ht', 'price_ttc', 'stock', 'stock_status', 'available', 'created_at')
    list_filter = ('available', 'category', 'created_at')
    search_fields = ('name', 'description')
    prepopulated_fields = {'slug': ('name',)}
    inlines = [ProductImageInline]
    readonly_fields = ('created_at', 'updated_at', 'stock_status')
    fieldsets = (
        (_('Produit'), {'fields': ('name', 'slug', 'category', 'image')}),
        (_('Description'), {'fields': ('short_description', 'description')}),
        (_('Prix & Taxe'), {'fields': ('price_ht', 'tax_rate', 'price_ttc')}),
        (_('Stock & Disponibilité'), {'fields': ('stock', 'stock_status', 'available')}),
        (_('Dates'), {'fields': ('created_at', 'updated_at')}),
    )

    def price_ttc(self, obj):
        return f"{obj.price_ttc} €"
    price_ttc.short_description = "Prix TTC"

    def stock_status(self, obj):
        color = "green"
        if obj.stock == 0: color = "red"
        elif obj.stock < 5: color = "orange"
        return format_html('<span style="color: {}; font-weight: bold;">{}</span>', color, obj.stock_status)
    stock_status.short_description = "État stock"


# ============================================================================
# VENTE & COMMANDE
# ============================================================================
@admin.register(ShippingZone)
class ShippingZoneAdmin(admin.ModelAdmin):
    list_display = ('name', 'zones', 'price', 'free_shipping')  # <-- zones au lieu de countries
    list_filter = ('free_shipping',)
    search_fields = ('name', 'zones')  # <-- recherche sur zones


@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ('code', 'discount_percent', 'active', 'valid_from', 'valid_to')
    list_filter = ('active',)
    search_fields = ('code',)

@admin.register(PaymentMethod)
class PaymentMethodAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active', 'extra_fee')
    list_filter = ('is_active',)


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'user_link', 'total_price', 'payment_status_colored', 'is_shipped', 'created_at')
    list_filter = ('payment_status', 'is_shipped', 'created_at', 'payment_method')
    search_fields = ('id', 'user__username', 'email', 'first_name', 'last_name')
    inlines = [OrderItemInline]
    readonly_fields = ('subtotal', 'vat_amount', 'shipping_cost', 'discount_amount', 'total_price', 'created_at')
    fieldsets = (
        (_('Client'), {'fields': ('user', 'first_name', 'last_name', 'email', 'phone')}),
        (_('Adresse'), {'fields': ('address', 'city', 'country', 'postal_code')}),
        (_('Options'), {'fields': ('shipping_zone', 'payment_method', 'coupon')}),
        (_('Montants (Calculés)'), {'fields': ('subtotal', 'vat_amount', 'shipping_cost', 'discount_amount', 'total_price')}),
        (_('Statuts'), {'fields': ('payment_status', 'is_shipped')}),
        (_('Dates'), {'fields': ('created_at',)}),
    )

    def user_link(self, obj):
        if obj.user:
            link = reverse("admin:shop_user_change", args=[obj.user.id]) # Remplacez 'shop' par le nom de votre app
            return format_html('<a href="{}">{}</a>', link, obj.user.username)
        return obj.email
    user_link.short_description = "Client"

    def payment_status_colored(self, obj):
        colors = {
            'pending': 'orange',
            'paid': 'green',
            'failed': 'red',
            'refunded': 'grey'
        }
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            colors.get(obj.payment_status, 'black'),
            obj.get_payment_status_display()
        )
    payment_status_colored.short_description = "Statut Paiement"


# ============================================================================
# COMPTABILITÉ
# ============================================================================

@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('id', 'type', 'amount', 'status', 'date', 'order_link')
    list_filter = ('type', 'status', 'date')
    search_fields = ('order__id', 'description')

    def order_link(self, obj):
        if obj.order:
            link = reverse("admin:shop_order_change", args=[obj.order.id]) # Ajustez nom app
            return format_html('<a href="{}">Commande #{}</a>', link, obj.order.id)
        return "-"
    order_link.short_description = "Commande liée"


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ('number', 'order_link', 'total_ttc', 'is_sent', 'created_at')
    list_filter = ('is_sent', 'created_at')
    search_fields = ('number', 'order__id')
    readonly_fields = ('number', 'order', 'total_ht', 'total_tva', 'total_ttc', 'pdf_file')

    def order_link(self, obj):
        link = reverse("admin:shop_order_change", args=[obj.order.id]) # Ajustez nom app
        return format_html('<a href="{}">Commande #{}</a>', link, obj.order.id)
    order_link.short_description = "Commande"


# ============================================================================
# CONFIGURATION & SINGLETONS
# ============================================================================

class SingletonModelAdmin(admin.ModelAdmin):
    """Empêche la création de plusieurs instances pour les modèles de config."""
    def has_add_permission(self, request):
        if self.model.objects.count() >= 1:
            return False
        return super().has_add_permission(request)

    def has_delete_permission(self, request, obj=None):
        return False

@admin.register(ShopInfo)
class ShopInfoAdmin(admin.ModelAdmin):
    list_display = (
        "categories_title",
        "features_title",
        "products_title",
        "promo_title",
        "trust_title",
        "about_title",
        "newsletter_title",
        "updated_at",
    )
    readonly_fields = ("updated_at",)

    fieldsets = (
        ("Catégories", {
            "fields": ("categories_title", "categories_subtitle")
        }),
        ("Rituels / Features", {
            "fields": ("features_title", "features_subtitle")
        }),
        ("Produits", {
            "fields": ("products_title", "products_subtitle")
        }),
        ("Promo", {
            "fields": ("promo_title", "promo_subtitle", "promo_image", "promo_text")
        }),
        ("Confiance / Trust", {
            "fields": ("trust_title", "trust_subtitle")
        }),
        ("À propos", {
            "fields": ("about_image", "about_title", "about_description", "signature")
        }),
        ("Newsletter", {
            "fields": ("newsletter_bg_image", "newsletter_title", "newsletter_text")
        }),
        ("Bien-être (Wellness)", {
            "fields": (
                "wellness_hero_title",
                "wellness_hero_subtitle",
                "wellness_philosophy_title",
                "wellness_philosophy_text",
                "wellness_image_break",
                "wellness_cta_title",
                "wellness_cta_text",
            )
        }),
        ("Méta", {
            "fields": ("updated_at",)
        }),
    )

    def has_add_permission(self, request):
        # Empêche la création de plusieurs instances
        return not ShopInfo.objects.exists()

    def has_delete_permission(self, request, obj=None):
        # Empêche la suppression
        return False



@admin.register(SiteSettings)
class SiteSettingsAdmin(SingletonModelAdmin):
    fieldsets = (
        ("Général", {'fields': ('site_name', 'contact_email', 'contact_phone','addresse' )}),

    )

@admin.register(BillingSettings)
class BillingSettingsAdmin(SingletonModelAdmin):
    fieldsets = (
        ("Entreprise", {'fields': ('company_name', 'company_address', 'company_phone', 'company_email', 'logo')}),
        ("Légal", {'fields': ('rccm', 'ninea')}),
        ("Facturation", {'fields': ('currency',)}),
    )


# ============================================================================
# MARKETING & BLOG
# ============================================================================


@admin.register(BlogPost)
class BlogPostAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'is_active', 'created_at')
    list_filter = ('is_active', 'category', 'created_at')
    search_fields = ('title', 'content')
    prepopulated_fields = {'slug': ('title',)}


@admin.register(Banner)
class BannerAdmin(admin.ModelAdmin):
    # On ajoute 'product' pour voir le lien vers le produit
    list_display = ('title', 'product', 'order', 'image_preview')

    # On garde 'order' éditable directement dans la liste
    list_editable = ('order',)

    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="width: 100px; height: auto; border-radius: 5px;" />', obj.image.url)
        return "-"

    image_preview.short_description = "Aperçu"

@admin.register(Feature1)
class Feature1Admin(admin.ModelAdmin):
    list_display = ("title", "icon_class", "order", "is_active")
    ordering = ("order",)

from .models import StaticPage

@admin.register(StaticPage)
class StaticPageAdmin(admin.ModelAdmin):
    list_display = ('title', 'slug', 'updated_at')
    prepopulated_fields = {'slug': ('title',)} # Remplit le slug automatiquement




from .models import NewsletterSubscriber

@admin.register(NewsletterSubscriber)
class NewsletterSubscriberAdmin(admin.ModelAdmin):
    list_display = ('email', 'subscribed_at')
    search_fields = ('email',)