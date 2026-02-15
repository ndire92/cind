from django import forms
from .models import Order,Product,ShopInfo,BlogPost,Category,ProductImage
from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from decimal import Decimal
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.contrib.auth import get_user_model
from django.forms import modelformset_factory







User = get_user_model()

COUNTRY_CHOICES = [
    ('SN', 'Sénégal'),
    ('FR', 'France'),
    ('CI', 'Côte d’Ivoire'),
    ('ML', 'Mali'),
    ('BF', 'Burkina Faso'),
    ('GN', 'Guinée'),
    ('MA', 'Maroc'),
    ('ALL', 'Autres pays'),
]

from django import forms
from .models import Order, ShippingZone

class OrderCreateForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = [
            'first_name',
            'last_name',
            'email',
            'address',
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
            'postal_code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Code postal'}),
            'city': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ville'}),
            'country': forms.Select(attrs={'class': 'form-control'}),
            'payment_method': forms.Select(attrs={'class': 'form-control'}),
        }

    # On récupère les pays dynamiquement
    country = forms.ChoiceField(label="Pays", required=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Récupérer tous les codes pays uniques depuis les zones de livraison
        zones = ShippingZone.objects.all()
        country_choices = []
        for zone in zones:
            codes = [c.strip().upper() for c in zone.countries.split(',')]
            for code in codes:
                if code not in [c[0] for c in country_choices]:
                    country_choices.append((code, code))
        self.fields['country'].choices = country_choices



# --- VALIDATION IMAGE ---
class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        exclude = ['slug']  # slug géré automatiquement

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            if field_name == 'slug':
                field.widget.attrs.update({
                    'readonly': 'readonly',
                    'class': 'form-control bg-light'
                })
            elif isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.update({'class': 'form-check-input'})
            else:
                field.widget.attrs.update({
                    'class': 'form-control',
                    'placeholder': field.label or ''
                })


# --- VALIDATION IMAGE ---
MAX_UPLOAD_SIZE = 5 * 1024 * 1024  # 5 MB
ALLOWED_CONTENT_TYPES = ('image/jpeg', 'image/png', 'image/webp')

def validate_image_file(f):
    if f.size > MAX_UPLOAD_SIZE:
        raise ValidationError(
            _("Le fichier est trop volumineux (max %(size)s)."),
            params={'size': f"{MAX_UPLOAD_SIZE // (1024*1024)} MB"}
        )
    if hasattr(f, 'content_type') and f.content_type not in ALLOWED_CONTENT_TYPES:
        raise ValidationError(_("Type d'image non supporté."))
    return f


# --- FORM IMAGE PRODUIT ---
class ProductImageForm(forms.ModelForm):
    class Meta:
        model = ProductImage
        fields = ["image", "is_main"]

    def clean_image(self):
        image = self.cleaned_data.get("image")
        if image:
            validate_image_file(image)
        return image


# --- FORMSET IMAGE ---
ProductImageFormSet = modelformset_factory(
    ProductImage,
    form=ProductImageForm,
    extra=3,          # nombre de champs vides par défaut
    can_delete=True   # permet de supprimer des images
)




# --- FORM IMAGE PRODUIT ---
class ProductImageForm(forms.ModelForm):
    class Meta:
        model = ProductImage
        fields = ["image", "is_main"]

    def clean_image(self):
        image = self.cleaned_data.get("image")
        if image:
            validate_image_file(image)
        return image


# --- FORMSET IMAGE ---


ProductImageFormSet = modelformset_factory(
    ProductImage,
    form=ProductImageForm,
    extra=3,          # nombre de champs vides par défaut
    can_delete=True   # permet de supprimer des images
)

class ShopInfoForm(forms.ModelForm):
    class Meta:
        model = ShopInfo
        fields = [
            # Slides
            "banner1_image", "banner1_title", "banner1_subtitle",
            "banner2_image", "banner2_title", "banner2_subtitle",
            "banner3_image", "banner3_title", "banner3_subtitle",
            "banner4_image", "banner4_title", "banner4_subtitle",

            # Promo
            "promo_image", "promo_text",

            # À propos
            "about_image", "about_title", "about_description",

            # Newsletter (AJOUTÉ)
            "newsletter_bg_image", "newsletter_title", "newsletter_text",
        ]
        widgets = {
            "banner1_title": forms.TextInput(attrs={"class": "form-control"}),
            "banner1_subtitle": forms.TextInput(attrs={"class": "form-control"}),
            "banner2_title": forms.TextInput(attrs={"class": "form-control"}),
            "banner2_subtitle": forms.TextInput(attrs={"class": "form-control"}),
            "banner3_title": forms.TextInput(attrs={"class": "form-control"}),
            "banner3_subtitle": forms.TextInput(attrs={"class": "form-control"}),
            "banner4_title": forms.TextInput(attrs={"class": "form-control"}),
            "banner4_subtitle": forms.TextInput(attrs={"class": "form-control"}),

            "promo_text": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "about_title": forms.TextInput(attrs={"class": "form-control"}),
            "about_description": forms.Textarea(attrs={"class": "form-control", "rows": 5}),
            
            # Newsletter Widgets (AJOUTÉ)
            "newsletter_title": forms.TextInput(attrs={"class": "form-control"}),
            "newsletter_text": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }

class BlogPostForm(forms.ModelForm):
    class Meta:
        model = BlogPost
        fields = ['title', 'slug', 'category', 'image', 'excerpt', 'content', 'is_active']
        widgets = {
            'title': forms.TextInput(attrs={"class": "form-control", "placeholder": "Titre accrocheur..."}),
            'slug': forms.TextInput(attrs={"class": "form-control", "readonly": "readonly"}), # Lecture seule (géré par JS ou Admin)
            'category': forms.TextInput(attrs={"class": "form-control", "placeholder": "ex: Bien-être, Nutrition..."}),
            'excerpt': forms.Textarea(attrs={"class": "form-control", "rows": 3, "placeholder": "Petit résumé pour la page d'accueil..."}),
            'content': forms.Textarea(attrs={"class": "form-control", "rows": 10, "placeholder": "Écrivez votre article ici..."}),
        }



class CustomUserCreationForm(UserCreationForm):
    class Meta:
        model = User
        fields = ['username', 'email', 'role', 'password1', 'password2']


    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for field in self.fields.values():
            field.widget.attrs.update({
                "class": "form-control",
                "placeholder": field.label
            })

class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ["name", "slug", "description", "image"]
        # Si vous ne voulez pas que l'utilisateur touche au Slug, retirez "slug" ici 
        # et ajoutez une logique dans la View ou un Signal pour le générer auto.

    def __init__(self, *args, **kwargs):
        super(CategoryForm, self).__init__(*args, **kwargs)
        # Ajout automatique des classes CSS pour le style
        for fieldname in ['name', 'slug', 'description']:
            self.fields[fieldname].widget.attrs.update({
                'class': 'form-control',
                'placeholder': '' 
            })