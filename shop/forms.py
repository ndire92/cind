from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.forms import modelformset_factory
from django.utils.translation import gettext_lazy as _
from django.forms import inlineformset_factory
from .models import SENEGAL_ZONES, SiteSettings



from shop import admin
from .models import (
    PaymentMethod, User, Product, ProductImage, Category, BlogPost,StaticPage,
    Order, ShippingZone, ShopInfo,Feature,Feature1,Video,TeamMember, Feature_about,
)

User = get_user_model()

# ============================================================================
# VALIDATEURS
# ============================================================================

MAX_UPLOAD_SIZE = 5 * 1024 * 1024  # 5 MB
ALLOWED_CONTENT_TYPES = ('image/jpeg', 'image/png', 'image/webp')

def validate_image_file(f):
    if f.size > MAX_UPLOAD_SIZE:
        raise ValidationError(_("Le fichier est trop volumineux (max 5MB)."))
    if hasattr(f, 'content_type') and f.content_type not in ALLOWED_CONTENT_TYPES:
        raise ValidationError(_("Type d'image non supporté."))
    return f

# ============================================================================
# AUTHENTIFICATION
# ============================================================================

class UserRegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-control', 'placeholder': field.label})


# ============================================================================
# COMMANDE
# ============================================================================


class OrderCreateForm(forms.ModelForm):

    zone = forms.ChoiceField(
        label="Zone de livraison",
        required=True,
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    class Meta:
        model = Order
        fields = [
            'first_name',
            'last_name',
            'email',
            'address',
            'phone',
            'postal_code',
            'city',
            'zone',
            'payment_method',
        ]

        widgets = {
            'first_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Prénom'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nom'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'exemple@email.com'
            }),
            'address': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Adresse complète'
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Numéro de téléphone'
            }),
            'postal_code': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Code postal'
            }),
            'city': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ville'
            }),
            'payment_method': forms.Select(attrs={
                'class': 'form-control'
            }),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        # Mise à jour dynamique des zones
        # On charge les zones définies dans ShippingZone
        self.fields['zone'].choices = ShippingZone.get_zone_choices()


        # Pré-remplissage utilisateur connecté
        if user and user.is_authenticated:
            self.fields['first_name'].initial = user.first_name
            self.fields['last_name'].initial = user.last_name
            self.fields['email'].initial = user.email
# ============================================================================
# GESTION PRODUITS
# ============================================================================

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        exclude = ['slug', 'created_at', 'updated_at']  # Slug auto
        widgets = {
            'category': forms.Select(attrs={'class': 'form-select'}),
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'price_ht': forms.NumberInput(attrs={'class': 'form-control'}),
            'tax_rate': forms.NumberInput(attrs={'class': 'form-control'}),
            'stock': forms.NumberInput(attrs={'class': 'form-control'}),
            'short_description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 5}),
            'video': forms.FileInput(attrs={'class': 'form-control'}),
            'ingredients': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'available': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'image': forms.ClearableFileInput(attrs={'class': 'form-control'}),  # image principale
        }


class ProductImageForm(forms.ModelForm):
    class Meta:
        model = ProductImage
        fields = ["image"]
        widgets = {
            'image': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }

    def clean_image(self):
        image = self.cleaned_data.get("image")
        if image:
            validate_image_file(image)
        return image

ProductImageFormSet = inlineformset_factory(
    Product,
    ProductImage,
    form=ProductImageForm,
    extra=2,          # nombre de champs vides par défaut
    can_delete=True   # permet suppression
)


from .models import Banner



class BannerForm(forms.ModelForm):
    class Meta:
        model = Banner
        # On ajoute 'product' à la liste des champs
        fields = ["image", "title", "subtitle", "product", "order"]

        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control", "placeholder": "Titre"}),
            "subtitle": forms.TextInput(attrs={"class": "form-control", "placeholder": "Sous-titre"}),

            # Widget pour le champ produit (liste déroulante Bootstrap)
            "product": forms.Select(attrs={"class": "form-select"}),

            "order": forms.NumberInput(attrs={"class": "form-control"}),
        }
# ============================================================================
# CONFIGURATION & BLOG
# ============================================================================



class ShippingZoneForm(forms.ModelForm):
    # On déclare le champ explicitement comme liste (MultipleChoiceField)
    zones = forms.MultipleChoiceField(
        choices=SENEGAL_ZONES.items(),
        widget=forms.SelectMultiple(attrs={
            'class': 'form-select',
            'size': '10',  # Hauteur de la liste
            'style': 'height: auto;'  # Pour s'assurer qu'elle s'affiche bien
        }),
        required=False
    )

    class Meta:
        model = ShippingZone
        # On enlève 'zones' de ici car on le gère manuellement au-dessus
        fields = ['name', 'zones', 'price', 'free_shipping']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Dakar Centre'}),
            'price': forms.NumberInput(attrs={'class': 'form-control', 'step': '1'}),
            'free_shipping': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Pré-remplissage si modification
        if self.instance and self.instance.pk:
            # Convertit "DAKAR,MEDINA" -> ['DAKAR', 'MEDINA']
            self.initial['zones'] = self.instance.get_zone_codes()

    def clean_zones(self):
        # Ici, data est bien une liste Python : ['DAKAR_PLATEAU', 'MEDINA']
        data = self.cleaned_data['zones']
        
        if not data:
            raise forms.ValidationError("Veuillez sélectionner au moins une zone.")

        # Validation (sécurité supplémentaire)
        for code in data:
            if code not in SENEGAL_ZONES:
                raise forms.ValidationError(f"Zone invalide : {code}")

        # Convertit la liste en chaîne pour la base de données
        return ",".join(data)

class PaymentMethodForm(forms.ModelForm):
    class Meta:
        model = PaymentMethod
        fields = ['name', 'description', 'is_active', 'extra_fee']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'extra_fee': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
        }

class ShopInfoForm(forms.ModelForm):
    class Meta:
        model = ShopInfo
        fields = [
            "promo_image", "promo_text",
            "about_image", "about_title", "about_description",
            "newsletter_bg_image", "newsletter_title", "newsletter_text",
        ]
        widgets = {
            "promo_text": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "about_title": forms.TextInput(attrs={"class": "form-control"}),
            "about_description": forms.Textarea(attrs={"class": "form-control", "rows": 5}),
            "newsletter_title": forms.TextInput(attrs={"class": "form-control"}),
            "newsletter_text": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }

# 2. Formulaire Promotion
class PromoSettingsForm(forms.ModelForm):
    class Meta:
        model = ShopInfo
        fields = ['promo_image', 'promo_text']
        widgets = {
            'promo_text': forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
        }


# 4. Formulaire Newsletter
class NewsletterSettingsForm(forms.ModelForm):
    class Meta:
        model = ShopInfo
        fields = ['newsletter_bg_image', 'newsletter_title', 'newsletter_text']
        widgets = {
            'newsletter_text': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
        }

class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ["name", "slug", "description", "image"]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'slug': forms.TextInput(attrs={'class': 'form-control', 'readonly': 'readonly'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

class BlogPostForm(forms.ModelForm):
    class Meta:
        model = BlogPost
        fields = ['title', 'slug', 'category', 'image', 'excerpt','content', 'is_active']
        widgets = {
            'title': forms.TextInput(attrs={"class": "form-control"}),
            'slug': forms.TextInput(attrs={"class": "form-control", "readonly": "readonly"}),
            'category': forms.Select(attrs={"class": "form-select"}),
            'excerpt': forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            'content': forms.Textarea(attrs={"class": "form-control", "rows": 10}),
            'is_active': forms.CheckboxInput(attrs={"class": "form-check-input"}),

        }


class VideoForm(forms.ModelForm):
    class Meta:
        model = Video
        # Liste de tous les champs du modèle Video
        fields = [
            'title', 'slug', 'category', 'description',
            'video_file', 'video_url', 'image', 'is_active'
        ]
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Titre de la vidéo'
            }),
            'slug': forms.TextInput(attrs={
                'class': 'form-control',
                'readonly': 'readonly',
                'placeholder': 'Généré automatiquement'
            }),
            'category': forms.Select(attrs={
                'class': 'form-select'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Description de la vidéo...'
            }),
            'video_file': forms.ClearableFileInput(attrs={
                'class': 'form-control'
            }),
            'video_url': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'https://www.youtube.com/watch?v=...'
            }),
            'image': forms.ClearableFileInput(attrs={
                'class': 'form-control'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Le slug est généré automatiquement, on le rend non obligatoire dans le formulaire
        self.fields['slug'].required = False
        # La catégorie et la description sont optionnelles
        self.fields['category'].required = False
        self.fields['description'].required = False

class SiteSettingsForm(forms.ModelForm):
    class Meta:
        model = SiteSettings
        fields = ["site_name", "contact_email", "contact_phone", "addresse"]
        widgets = {
            "site_name": forms.TextInput(attrs={"class": "form-control"}),
            "contact_email": forms.EmailInput(attrs={"class": "form-control"}),
            "contact_phone": forms.TextInput(attrs={"class": "form-control"}),
            "addresse": forms.TextInput(attrs={"class": "form-control"}),
        }

class FeatureForm(forms.ModelForm):
    class Meta:
        model = Feature
        fields = ['title', 'description', 'icon_class', 'is_active', 'order']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }

class FeatureForm1(forms.ModelForm):
    class Meta:
        model = Feature1
        fields = ['title', 'description', 'icon_class', 'is_active', 'order']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }

class WellnessSettingsForm(forms.ModelForm):
    class Meta:
        model = ShopInfo
        fields = [
            'wellness_hero_title',
            'wellness_hero_subtitle',
            'wellness_philosophy_title',
            'wellness_hero_bg',
            'wellness_philosophy_text',
            'wellness_image_break',
            'wellness_cta_title',
            'wellness_cta_text'
        ]
        widgets = {
            'wellness_hero_title': forms.TextInput(attrs={'class': 'form-control'}),
            'wellness_hero_subtitle': forms.TextInput(attrs={'class': 'form-control'}),
            'wellness_philosophy_title': forms.TextInput(attrs={'class': 'form-control'}),
            'wellness_philosophy_text': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'wellness_cta_title': forms.TextInput(attrs={'class': 'form-control'}),
            'wellness_cta_text': forms.TextInput(attrs={'class': 'form-control'}),
        }

class AboutSettingsForm(forms.ModelForm):
    """Gère les textes de la section Hero, Histoire et Processus"""
    class Meta:
        model = ShopInfo
        fields = [
            # Hero Section
            'about_hero_title',
            'about_hero_subtitle',

            # Story Section (Notre Histoire)
            'about_image',
            'about_title',
            'about_description',
            'signature',

            # Process Section
            'process_title',
            'process_subtitle',
            'step1_text',
            'step2_text',
            'step3_text'
        ]
        widgets = {
            # Hero
            'about_hero_title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Titre principal (ex: Retour aux sources)'}),
            'about_hero_subtitle': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Sous-titre'}),

            # Story
            'about_image': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'about_title': forms.TextInput(attrs={'class': 'form-control'}),
            'about_description': forms.Textarea(attrs={'class': 'form-control', 'rows': 5}),
            'signature': forms.TextInput(attrs={'class': 'form-control'}),

            # Process
            'process_title': forms.TextInput(attrs={'class': 'form-control'}),
            'process_subtitle': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'step1_text': forms.TextInput(attrs={'class': 'form-control'}),
            'step2_text': forms.TextInput(attrs={'class': 'form-control'}),
            'step3_text': forms.TextInput(attrs={'class': 'form-control'}),
        }

class TeamMemberForm(forms.ModelForm):
    """Gère l'ajout et modification des membres de l'équipe"""
    class Meta:
        model = TeamMember
        fields = ['name', 'role', 'bio', 'photo', 'order']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nom complet'}),
            'role': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Fondatrice'}),
            'bio': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Biographie courte'}),
            'photo': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'order': forms.NumberInput(attrs={'class': 'form-control'}),
        }


class FeatureaboutForm(forms.ModelForm):
    class Meta:
        model = Feature_about
        fields = ['title', 'description', 'icon_class', 'is_active', 'order']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }

# Dans forms.py

class StaticPageForm(forms.ModelForm):
    class Meta:
        model = StaticPage
        fields = ['title', 'slug', 'content']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Conditions Générales de Vente'}),
            'slug': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: cgv (pour l\'URL)'}),
            'content': forms.Textarea(attrs={'class': 'form-control', 'rows': 10}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['slug'].required = False
        self.fields['slug'].help_text = "Laissez vide pour une génération automatique."