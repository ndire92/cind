from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from .models import Product


class ProductSitemap(Sitemap):
    changefreq = "daily"
    priority = 0.8

    def items(self):
        return Product.objects.all()

    def lastmod(self, obj):
        return obj.updated_at


class StaticViewSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.9

    def items(self):
        return [
            'products:home',
            'products:shop',
            'products:product_list',
            'products:bien_etre',
            'products:about',
            'products:livraison',
            'products:conditions',
            'products:confidentialite',
        ]

    def location(self, item):
        return reverse(item)
