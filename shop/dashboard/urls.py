from django.urls import path
from . import views
app_name = 'dashboard'

urlpatterns = [
    path('overview/', views.dashboard_overview, name='overview'),

    path('orders/', views.dashboard_orders, name='orders'),
    path('orders/<int:order_id>/update-status/', views.update_order_status, name='update_order_status'),
    path("orders/<int:order_id>/", views.order_detail, name="order_detail"),


    path('products/', views.dashboard_products, name='products'),
    path('products/<int:product_id>/edit/', views.edit_product, name='edit_product'),
path('products/add/', views.add_product, name='add_product'),
    path('products/delete/<int:pk>/', views.delete_product, name='product_delete'),

path('accounting/', views.dashboard_accounting, name='accounting'),


    path('export-transactions/', views.export_transactions_csv, name='export_transactions_csv'),
    path('settings/', views.dashboard_settings, name='settings'),
    path('settings/shipping-zones/', views.shipping_zones, name='shipping_zones'),

        # Edition : L'URL utilise <int:zone_id>, la vue doit avoir (request, zone_id)
    path('shipping/edit/<int:zone_id>/', views.edit_shipping_zone, name='edit_shipping_zone'),
    
    path('shipping/delete/<int:pk>/', views.delete_shipping_zone, name='delete_shipping_zone'),

    path('settings/payment-methods/', views.payment_methods, name='payment_methods'),
    path('settings/shop-info/', views.shop_info, name='shop_info'),
    path('settings/billing/', views.billing_settings, name='billing_settings'),
    path('blog/', views.blog_list_view, name='blog_posts'),
    path('blog/add/', views.blog_create_view, name='blog_add'),
    path('blog/edit/<int:pk>/', views.blog_update_view, name='blog_edit'),
    path('blog/delete/<int:pk>/', views.blog_delete_view, name='blog_delete'),
   # Gestion des Catégories (Admin)
    path('categories/', views.CategoryListView.as_view(), name='category_list'),
    path('category/add/', views.CategoryCreateView.as_view(), name='category_add'),
    path('category/<slug>/edit/', views.CategoryUpdateView.as_view(), name='category_edit'),
    path('category/<slug>/delete/', views.CategoryDeleteView.as_view(), name='category_delete'),
]