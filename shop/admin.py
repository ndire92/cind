from django.contrib import admin
from .models import Category, Product, Order, OrderItem, ShippingZone,ShopInfo,ProductImage




class ProductImageInline(admin.TabularInline):  # ou admin.StackedInline
    model = ProductImage
    extra = 1  # nombre de formulaires vides affichés par défaut

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "price_ht", "price_ttc", "stock", "available", "created")
    list_filter = ("category", "available", "created", "updated")
    search_fields = ("name", "description", "short_description")
    prepopulated_fields = {"slug": ("name",)}
    readonly_fields = ("price_ttc", "created", "updated")

    fieldsets = (
        ("Infos produit", {"fields": ("name", "slug", "category", "image")}),
        ("Descriptions", {"fields": ("short_description", "description")}),
        ("Prix et stock", {"fields": ("price_ht", "tax_rate", "stock", "available", "price_ttc")}),
        ("Dates", {"fields": ("created", "updated")}),
    )

    inlines = [ProductImageInline]

class ProductImageInline(admin.TabularInline):  # ou admin.StackedInline
    model = ProductImage
    extra = 1

    
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    # CORRECTION : 
    # - 'status' a été retiré du modèle, on affiche 'paid' (Payé ou non) à la place.
    # - 'total_price' n'est plus un champ direct, on affiche 'country' ou 'shipping_cost'.
    # - 'created_at' est maintenant nommé 'created'.
    list_display = ('id', 'user', 'paid', 'created', 'country') 
    list_filter = ('paid', 'created') # On filtre par statut de paiement ou date
    search_fields = ('first_name', 'email')
    
    readonly_fields = ('created', 'updated') # Empêche de changer la date de création

@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ('order', 'product', 'quantity', 'price')


# ICI : NOUVEL ADMIN POUR ZONES

@admin.register(ShippingZone)
class ShippingZoneAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'formatted_countries',
        'price',
    )

    list_editable = ('price',)
    search_fields = ('name', 'countries')
    ordering = ('price',)

    fieldsets = (
        ("Informations générales", {
            'fields': ('name', 'price')
        }),
        ("Pays couverts", {
            'fields': ('countries',),
            'description': (
                "Codes ISO séparés par des virgules.<br>"
                "<strong>Ex :</strong> SN,CI,ML<br>"
                "<strong>ALL</strong> = reste du monde"
            )
        }),
    )

    def formatted_countries(self, obj):
        return obj.countries.upper()

    formatted_countries.short_description = "Pays (ISO)"



@admin.register(ShopInfo)
class ShopInfoAdmin(admin.ModelAdmin):
    list_display = (
        "updated_at",
        "banner1_title", "banner2_title", "banner3_title", "banner4_title",
        "promo_text", "about_title","newsletter_bg_image",
    )
    readonly_fields = ("updated_at",)

    fieldsets = (
        ("Slides Accueil", {
            "fields": (
                ("banner1_image", "banner1_title", "banner1_subtitle"),
                ("banner2_image", "banner2_title", "banner2_subtitle"),
                ("banner3_image", "banner3_title", "banner3_subtitle"),
                ("banner4_image", "banner4_title", "banner4_subtitle"),
            )
        }),
        ("Section Promotion", {
            "fields": ("promo_image", "promo_text")
        }),
        ("À propos", {
            "fields": ("about_image", "about_title", "about_description")
        }),
        ("Newsletter", {  # <--- Correction : Utilisation des bons champs
            "fields": ("newsletter_bg_image", "newsletter_title", "newsletter_text")
        }),

        ("Infos système", {
            "fields": ("updated_at",)
        }),
    )

from .models import BlogPost

@admin.register(BlogPost)
class BlogPostAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'created_at', 'is_active')
    list_filter = ('category', 'is_active')
    search_fields = ('title', 'excerpt')
    prepopulated_fields = {'slug': ('title',)} # Remplit le slug automatiquement


from django.contrib.auth.admin import UserAdmin
from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    # Champs affichés dans la liste des utilisateurs
    list_display = ("username", "email", "role", "is_staff", "is_active")
    
    # Champs affichés dans la page de détail d’un utilisateur
    fieldsets = UserAdmin.fieldsets + (
        ("Rôle utilisateur", {"fields": ("role",)}),
    )

    # Champs affichés lors de la création d’un utilisateur depuis l’admin
    add_fieldsets = UserAdmin.add_fieldsets + (
        ("Rôle utilisateur", {"fields": ("role",)}),    )
