from django.contrib import admin
from django.conf import settings
from django.http import FileResponse
from django.conf.urls.static import static
from django.urls import path, include
from shop import views
from django.contrib.sitemaps.views import sitemap
from shop.sitemaps import ProductSitemap  # ton sitemap de produits

sitemaps = {
    'products': ProductSitemap,
}
def robots_txt(request):
    return FileResponse(open(os.path.join(settings.BASE_DIR, 'static/robots.txt'), 'rb'), content_type='text/plain')
urlpatterns = [
    # Administration Django
    path('admin/', admin.site.urls),

    # Page d'accueil (Root)
    path('', views.index, name='home'),

    # URLs de la Boutique (Partie Publique)
    # Tout ce qui commence par 'boutique/' ira dans shop/urls.py
    path('boutique/', include('shop.urls', namespace='products')),

    # URLs du Dashboard (Partie Gestion)
    # Tout ce qui commence par 'dashboard/' ira dans shop/dashboard/urls.py
    path('dashboard/', include('shop.dashboard.urls')),
    path('sitemap.xml', sitemap, {'sitemaps': sitemaps}, name='sitemap'),
    path('robots.txt', robots_txt),
]

# Servir les fichiers médias (images, pdf) en mode développement
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

