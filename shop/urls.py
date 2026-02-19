from django.urls import path
from . import views

app_name = 'products'

urlpatterns = [
    # Accueil & Boutique
    path('', views.shop, name='shop'),
    path('liste/', views.product_list, name='product_list'),
    
    # Catégories (Aligné sur le modèle get_absolute_url)
    path('category/<slug:slug>/', views.category_list, name='category_list'),
    
    # Produits (Aligné sur le modèle get_absolute_url)
    path('produit/<int:id>/<slug:slug>/', views.product_detail, name='product_detail'),

    # Authentification
    path("register/", views.register_view, name="register"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("profile/", views.profile, name="profile"),

    # Panier
    path('cart/', views.cart_detail, name='cart_detail'),
    path('cart/add/<int:product_id>/', views.cart_add, name='cart_add'),
    path('cart/remove/<int:product_id>/', views.cart_remove, name='cart_remove'),
    path("cart/update/<int:product_id>/", views.cart_update, name="cart_update"),

    # Commande & Paiement
    path('checkout/', views.order_create, name='checkout'),
    path('checkout/shipping-cost/', views.shipping_cost_ajax, name='shipping_cost_ajax'),
    path('order/confirmation/<int:order_id>/', views.order_confirmation, name='order_confirmation'),


    


    path('order/invoice/<int:order_id>/', views.invoice_download, name='invoice_download'),
    path('paydunya/<int:order_id>/', views.paydunya_init, name='paydunya_init'),
    path('payment/success/', views.payment_success, name='payment_success'),

    # Blog
    path('bien-etre/', views.bien_etre, name='bien_etre'),
    path('bien-etre/<slug:slug>/', views.post_detail, name='post_detail'),

    # Pages Statiques
    path('apropos/', views.about_page, name='about'),

   # Banner Dashboard
    path("dashboard/banners/", views.banner_list, name="banner_list"),
    path("dashboard/banners/add/", views.banner_create, name="banner_create"),
    path("dashboard/banners/<int:pk>/edit/", views.banner_update, name="banner_update"),
    path("dashboard/banners/<int:pk>/delete/", views.banner_delete, name="banner_delete"),
]