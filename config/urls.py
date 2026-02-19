from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.urls import path, include
from shop import views

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
]

# Servir les fichiers médias (images, pdf) en mode développement
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)