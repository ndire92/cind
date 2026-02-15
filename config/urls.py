from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.urls import path, include
from shop import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.index, name='home'),
    path('boutique/', include('shop.urls', namespace='products')),
    path('dashboard/', include('shop.dashboard.urls')),  # ✅ préfixe correct



]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
