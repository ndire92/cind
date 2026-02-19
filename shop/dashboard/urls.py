from django.urls import path
from .. import views

app_name = 'dashboard'

urlpatterns = [
    path('overview/', views.dashboard_overview, name='overview'),

    # Commandes
    path('orders/', views.dashboard_orders, name='orders'),
    path('orders/<int:order_id>/', views.order_detail, name="order_detail"),
    path('orders/<int:order_id>/update-status/', views.update_order_status, name='update_order_status'),

    # Produits (CRUD)
    path('products/', views.dashboard_products, name='products'),
    path('products/add/', views.add_product, name='add_product'), # Doit utiliser ProductForm
    path('products/<int:product_id>/edit/', views.edit_product, name='edit_product'),
    path('products/delete/<int:pk>/', views.delete_product, name='product_delete'),

    # Catégories (CBV)
    path('categories/', views.CategoryListView.as_view(), name='category_list'),
    path('category/add/', views.CategoryCreateView.as_view(), name='category_add'),
    path('category/<slug:slug>/edit/', views.CategoryUpdateView.as_view(), name='category_edit'),
    path('category/<slug:slug>/delete/', views.CategoryDeleteView.as_view(), name='category_delete'),

    # Blog
    path('blog/', views.blog_list_view, name='blog_posts'),
    path('blog/add/', views.blog_create_view, name='blog_add'), # Doit utiliser BlogPostForm
    path('blog/edit/<int:pk>/', views.blog_update_view, name='blog_edit'),
    path('blog/delete/<int:pk>/', views.blog_delete_view, name='blog_delete'),

    # Configuration (Singletons)
    path('accounting/', views.dashboard_accounting, name='accounting'),
    path('export-transactions/', views.export_transactions_csv, name='export_transactions_csv'),
    
    path('settings/', views.dashboard_settings, name='settings'),
    path('settings/billing/', views.billing_settings, name='billing_settings'),


# Dans shop/dashboard/urls.py

    # ... autres urls ...

    # Configuration Boutique (Séparée)
   
    path('settings/promo/', views.shop_promo, name='shop_promo'),
    path('settings/about/', views.shop_about, name='shop_about'),
    path('settings/newsletter/', views.shop_newsletter, name='shop_newsletter'),

    # Zones de livraison
    path('settings/shipping-zones/', views.shipping_zones, name='shipping_zones'),
    path('settings/shipping-zones/add/', views.add_shipping_zone, name='add_shipping_zone'),
    path('shipping/edit/<int:zone_id>/', views.edit_shipping_zone, name='edit_shipping_zone'),
    path('shipping/delete/<int:pk>/', views.delete_shipping_zone, name='delete_shipping_zone'),

    # Méthodes de paiement
    path('settings/payment-methods/', views.payment_methods, name='payment_methods'),
    path('settings/payment-methods/add/', views.add_payment_method, name='add_payment_method'),
    path('settings/payment-methods/edit/<int:method_id>/', views.edit_payment_method, name='edit_payment_method'),
]


