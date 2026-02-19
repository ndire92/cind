from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.forms import modelformset_factory
from django.utils.translation import gettext_lazy as _

from shop import admin
from .models import (
    PaymentMethod, User, Product, ProductImage, Category, BlogPost,
    Order, ShippingZone, ShopInfo
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

    country = forms.ChoiceField(
        label="Pays",
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
            'country',
            'payment_method',
        ]
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Prénom'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nom'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'exemple@email.com'}),
            'address': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Adresse complète'}),
           
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Numéro de téléphone'}),
            'city': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ville'}),
            'payment_method': forms.Select(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        # ===== Pays dynamiques =====
        zones = ShippingZone.objects.all()
        country_choices = []

        for zone in zones:
            codes = [c.strip().upper() for c in zone.countries.split(',') if c.strip()]
            for code in codes:
                if code not in [c[0] for c in country_choices]:
                    country_choices.append((code, code))

        country_choices.insert(0, ('', '-- Sélectionner un pays --'))
        self.fields['country'].choices = country_choices

        # ===== Pré-remplissage utilisateur =====
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
        exclude = ['slug', 'created_at', 'updated_at'] # Slug auto
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
            # Ajoutez les autres champs selon vos besoins
        }

class ProductImageForm(forms.ModelForm):
    class Meta:
        model = ProductImage
        fields = ["image", "is_main"]
        widgets = {
            'image': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'is_main': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def clean_image(self):
        image = self.cleaned_data.get("image")
        if image:
            validate_image_file(image)
        return image

ProductImageFormSet = modelformset_factory(
    ProductImage, form=ProductImageForm, extra=3, can_delete=True
)

from .models import Banner

class BannerForm(forms.ModelForm):
    class Meta:
        model = Banner
        fields = ["image", "title", "subtitle", "order"]
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control", "placeholder": "Titre"}),
            "subtitle": forms.TextInput(attrs={"class": "form-control", "placeholder": "Sous-titre"}),
            "order": forms.NumberInput(attrs={"class": "form-control"}),
        }
# ============================================================================
# CONFIGURATION & BLOG
# ============================================================================

# Dans shop/forms.py

class ShippingZoneForm(forms.ModelForm):
    class Meta:
        model = ShippingZone
        fields = ['name', 'countries', 'price', 'free_shipping']  # 👈 ajouté
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex: Zone Afrique'
            }),
            'countries': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Ex: SN,CI,ML (codes ISO)'
            }),
            'price': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01'
            }),
            'free_shipping': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }


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

# 3. Formulaire À Propos
class AboutSettingsForm(forms.ModelForm):
    class Meta:
        model = ShopInfo
        fields = ['about_image', 'about_title', 'about_description']
        widgets = {
            'about_description': forms.Textarea(attrs={'rows': 5, 'class': 'form-control'}),
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
        fields = ['title', 'slug', 'category', 'image', 'excerpt', 'content', 'is_active']
        widgets = {
            'title': forms.TextInput(attrs={"class": "form-control"}),
            'slug': forms.TextInput(attrs={"class": "form-control", "readonly": "readonly"}),
            'category': forms.Select(attrs={"class": "form-select"}),
            'excerpt': forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            'content': forms.Textarea(attrs={"class": "form-control", "rows": 10}),
            'is_active': forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # SOLUTION : On dit au formulaire que le slug n'est pas obligatoire ici.
        # C'est le modèle qui va le générer automatiquement si vide.
        self.fields['slug'].required = False