from django.urls import path
from . import views
# Le namespace 'products' est défini ici
app_name = 'products'

urlpatterns = [
    # Authentification
    path("register/", views.register_view, name="register"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("profile/", views.profile, name="profile"),
   # path("profile/edit/", views.edit_profile_view, name="edit_profile"),
   # path("profile/delete/", views.delete_account_view, name="delete_account"),
   path("some-view/", views.some_view, name="some_view"),
    # Page liste boutique (ex: /boutique/)
    path('', views.shop, name='shop'),
    
    # Filtrage par catégorie (ex: /boutique/category/visage/)
    path('category/<slug:category_slug>/', views.category_list, name='category_list'),
    
    # Détail produit (ex: /boutique/produit/1/creme-peau-neuve/)
    path('produit/<int:id>/<slug:slug>/', views.product_detail, name='product_detail'),
    # --- ROUTES PANIER ---
    path('cart/', views.cart_detail, name='cart_detail'),
    path('cart/add/<int:product_id>/', views.cart_add, name='cart_add'),
    path('cart/remove/<int:product_id>/', views.cart_remove, name='cart_remove'),
    path("cart/update/<int:product_id>/", views.cart_update, name="cart_update"),
    path('checkout/', views.order_create, name='checkout'),
   path('order/confirmation/<int:order_id>/', views.order_confirmation, name='order_confirmation'),
    path('produit/<int:id>/<slug:slug>/', views.product_detail, name='product_detail'),

# products/urls.py
    path("boutique/", views.product_list, name="product_list"),

    path('checkout/shipping-cost/', views.shipping_cost_ajax, name='shipping_cost_ajax'),
    path('paydunya/<int:order_id>/', views.paydunya_init, name='paydunya_init'),
    path('payment/success/', views.payment_success, name='payment_success'),
 
    path('order/invoice/<int:order_id>/', views.invoice_download, name='invoice_download'),
    path('bien-etre/', views.bien_etre, name='bien_etre'),
        # Page de détail d'un article
    path('bien-etre/<slug:slug>/', views.post_detail, name='post_detail'),

    # Ajoutez ceci dans urlpatterns
path('apropos/', views.about_page, name='about'),

  

]



