from django.urls import path
from . import views

app_name = 'products'

urlpatterns = [
    # --- Accueil & Boutique ---
    path('', views.index, name='home'), # Ajout de la home
    path('boutique/', views.shop, name='shop'),
    path('liste/', views.product_list, name='product_list'),

    # --- Catégories & Produits ---
    path('category/<slug:slug>/', views.category_list, name='category_list'),
    path('produit/<int:id>/<slug:slug>/', views.product_detail, name='product_detail'),

    # --- Authentification ---
    path("register/", views.register_view, name="register"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("profile/", views.profile, name="profile"),

    # --- Panier ---
    path('cart/', views.cart_detail, name='cart_detail'),
    path('cart/add/<int:product_id>/', views.cart_add, name='cart_add'),
    path('cart/remove/<int:product_id>/', views.cart_remove, name='cart_remove'),
    path("cart/update/<int:product_id>/", views.cart_update, name="cart_update"),

    # --- Commande & Paiement ---
    path('checkout/', views.order_create, name='checkout'),
    path('checkout/shipping-cost/', views.shipping_cost_ajax, name='shipping_cost_ajax'),
    path('order/confirmation/<int:order_id>/', views.order_confirmation, name='order_confirmation'),
    path('order/invoice/<int:order_id>/', views.invoice_download, name='invoice_download'),
    
# Passerelles de paiement
   path('paydunya/<int:order_id>/', views.paydunya_init, name='paydunya_init'),

    path('boutique/paydunya_callback/<int:order_id>/', views.paydunya_callback, name='paydunya_callback'),

    path('boutique/order_cancelled/<int:order_id>/', views.order_cancelled, name='order_cancelled'),

    path('dexpay/<int:order_id>/', views.dexpay_init, name='dexpay_init'),

    path('boutique/dexpay_callback/<int:order_id>/', views.dexpay_callback, name='dexpay_callback'),

    path('boutique/payment/success/<int:order_id>/', views.payment_success, name='payment_success'),


    # --- Blog & Pages ---
    path('bien-etre/', views.bien_etre, name='bien_etre'),
    path('bien-etre/<slug:slug>/', views.post_detail, name='post_detail'),
    path('apropos/', views.about_page, name='about'),
    
    # --- Pages Statiques (Légales) ---
    path('page/<slug:slug>/', views.static_page_view, name='static_page'),
    path('livraison-retours/', views.livraison_view, name='livraison'),
    path('conditions-generales/', views.conditions_view, name='conditions'),
    path('politique-confidentialite/', views.confidentialite_view, name='confidentialite'),
    
    # --- Newsletter ---
    path('newsletter/subscribe/', views.newsletter_subscribe, name='newsletter_subscribe'),


]
