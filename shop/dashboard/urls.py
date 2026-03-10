from django.urls import path
from .. import views

app_name = 'dashboard'

urlpatterns = [
    # --- Tableau de bord ---
    path('overview/', views.dashboard_overview, name='overview'),

    # --- Commandes ---
    path('orders/', views.dashboard_orders, name='orders'),
    path('orders/<int:order_id>/', views.order_detail, name="order_detail"),
    path('orders/<int:order_id>/update-status/', views.update_order_status, name='update_order_status'),

    # --- Produits ---
    path('products/', views.dashboard_products, name='products'),
    path('products/add/', views.add_product, name='add_product'),
    path('products/<int:product_id>/edit/', views.edit_product, name='edit_product'),
    path('products/delete/<int:pk>/', views.delete_product, name='product_delete'),

    # --- Catégories (CBV) ---
    path('categories/', views.CategoryListView.as_view(), name='category_list'),
    path('category/add/', views.CategoryCreateView.as_view(), name='category_add'),
    path('category/<slug:slug>/edit/', views.CategoryUpdateView.as_view(), name='category_edit'),
    path('category/<slug:slug>/delete/', views.CategoryDeleteView.as_view(), name='category_delete'),

    # --- Blog ---
    path('blog/', views.blog_list_view, name='blog_posts'),
    path('blog/add/', views.blog_create_view, name='blog_add'),
    path('blog/edit/<int:pk>/', views.blog_update_view, name='blog_edit'),
    path('blog/delete/<int:pk>/', views.blog_delete_view, name='blog_delete'),

    # --- Vidéos ---
    path('videos/', views.video_list_view, name='video_list'),
    path('videos/add/', views.video_create_view, name='video_add'),
    path('videos/edit/<int:pk>/', views.video_update_view, name='video_edit'),
    path('videos/delete/<int:pk>/', views.video_delete_view, name='video_delete'),
    path('videos/<slug:slug>/', views.video_detail, name='video_detail'), # Optionnel

    # --- Configuration Boutique ---
    path('settings/promo/', views.shop_promo, name='shop_promo'),
    
    # CORRECTION : 'se/' corrigé en 'settings/about/'
    path('settings/about/', views.a_settings_view, name='ab_settings'),
    
    path('settings/wellness/', views.shop_wellness, name='shop_wellness'),
    path('settings/newsletter/', views.shop_newsletter, name='shop_newsletter'),

    # --- Zones de livraison ---
    path('settings/shipping-zones/', views.shipping_zones, name='shipping_zones'),
    path('settings/shipping-zones/add/', views.add_shipping_zone, name='add_shipping_zone'),
    path('shipping/edit/<int:zone_id>/', views.edit_shipping_zone, name='edit_shipping_zone'),
    path('shipping/delete/<int:pk>/', views.delete_shipping_zone, name='delete_shipping_zone'),

    # --- Moyens de paiement ---
    path('settings/payment-methods/', views.payment_methods, name='payment_methods'),
    path('settings/payment-methods/add/', views.add_payment_method, name='add_payment_method'),
    path('settings/payment-methods/edit/<int:method_id>/', views.edit_payment_method, name='edit_payment_method'),

    # --- Site Settings (Contact) ---
    path("site-settings/add/", views.site_settings_add, name="site_settings_add"),
    path("site-settings/list/", views.site_settings_list, name="site_settings_list"),
    path("site-settings/edit/<int:pk>/", views.site_settings_edit, name="site_settings_edit"),
    path("site-settings/delete/<int:pk>/", views.site_settings_delete, name="site_settings_delete"),

    # --- Features (Accueil) ---
    path('features/', views.feature_list, name='feature_list'),
    path('features/add/', views.feature_create, name='feature_create'),
    path('features/<int:pk>/edit/', views.feature_update, name='feature_update'),
    path('features/<int:pk>/delete/', views.feature_delete, name='feature_delete'),

    # --- Features 1 (Bien-être) ---
    path('features-wellness/', views.feature_list1, name='feature_list1'),
    path('features-wellness/add/', views.feature_create1, name='feature_create1'),
    path('features-wellness/<int:pk>/edit/', views.feature_update1, name='feature_update1'),
    path('features-wellness/<int:pk>/delete/', views.feature_delete1, name='feature_delete1'),

    # --- Features About ---
    # CORRECTION : 'feate/' corrigé en 'features-about/'
    path('features-about/', views.feature_about_list, name='featabout_list'),
    path('features-about/add/', views.feature_about_create, name='featabout_create'),
    path('features-about/<int:pk>/edit/', views.feature_about_update, name='featabout_update'),
    path('features-about/<int:pk>/delete/', views.feature_about_delete, name='featabout_delete'),

    # --- Équipe ---
    path('team/', views.team_list_view, name='team_list'),
    path('team/add/', views.team_add_view, name='team_add'),
    path('team/edit/<int:pk>/', views.team_edit_view, name='team_edit'),
    path('team/delete/<int:pk>/', views.team_delete_view, name='team_delete'),

    # --- Pages Légales (Dashboard) ---
    path('pages/', views.static_page_list, name='static_page_list'),
    path('pages/add/', views.static_page_add, name='static_page_add'),
    path('pages/edit/<int:pk>/', views.static_page_edit, name='static_page_edit'),
    path('pages/delete/<int:pk>/', views.static_page_delete, name='static_page_delete'),
    
    # --- Hub Bien-être ---
    path('bien-etre/', views.wellness_hub, name='wellness_hub'),

    # --- Divers ---
    path('accounting/', views.dashboard_accounting, name='accounting'),
    path('export-transactions/', views.export_transactions_csv, name='export_transactions_csv'),
    path('settings/', views.dashboard_settings, name='settings'),
    path('settings/billing/', views.billing_settings, name='billing_settings'),
    
    # --- Bannières (Dashboard) ---
    path("banners/", views.banner_list, name="banner_list"),
    path("banners/add/", views.banner_create, name="banner_create"),
    path("banners/<int:pk>/edit/", views.banner_update, name="banner_update"),
    path("banners/<int:pk>/delete/", views.banner_delete, name="banner_delete"),
]