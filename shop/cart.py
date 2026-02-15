from decimal import Decimal
from shop.models import Product

class Cart:
    def __init__(self, request):
        self.session = request.session
        cart = self.session.get('cart')
        if not cart:
            cart = self.session['cart'] = {}
        self.cart = cart

    def add(self, product, quantity=1, update_quantity=False):
        """
        Ajoute un produit au panier ou met à jour sa quantité.
        """
        product_id = str(product.id)
        
        if product_id not in self.cart:
            self.cart[product_id] = {'quantity': 0, 'price_ht': str(product.price_ht)}
        
        if update_quantity:
            self.cart[product_id]['quantity'] = quantity
        else:
            self.cart[product_id]['quantity'] += quantity
        
        self.save()

    def remove(self, product):
        """
        Supprime un produit du panier.
        """
        product_id = str(product.id)
        if product_id in self.cart:
            del self.cart[product_id]
            self.save()

    def __len__(self):
        """
        Compte le nombre total d'articles.
        """
        return sum(item['quantity'] for item in self.cart.values())

    def get_total_price(self):
        """
        Calcule le prix HT total du panier.
        """
        return sum(Decimal(item['price_ht']) * item['quantity'] for item in self.cart.values())

    # --- MÉTHODES AJOUTÉES POUR LE TEMPLATE HTML (CORRECTION ERREUR MULTIPLY) ---
    def get_total_ttc(self):
        """
        Calcule le prix TTC total du panier (HT * 1.20).
        """
        return self.get_total_price() * Decimal('1.20')

    def get_tva_amount(self):
        """
        Calcule le montant de la TVA (Total TTC - Total HT).
        """
        return self.get_total_ttc() - self.get_total_price()

    # -----------------------------------------------------------------------

    def clear(self):
        # Vide le panier (utile après commande)
        self.session['cart'] = {}
        self.session.modified = True

    def save(self):
        # Marque la session comme modifiée pour s'assurer qu'elle est sauvegardée
        self.session.modified = True

    def __iter__(self):
        """
        Permet d'itérer sur les produits du panier et de récupérer les objets Product.
        """
        product_ids = self.cart.keys()
        # Récupère les objets produits depuis la BDD
        products = Product.objects.filter(id__in=product_ids)
        for product in products:
            self.cart[str(product.id)]['product'] = product
        
        for item in self.cart.values():
            # Convertit le prix en Decimal
            item['price_ht'] = Decimal(item['price_ht'])
            item['total_ht'] = item['price_ht'] * item['quantity']
            
            # CORRECTION DU CALCUL TTC PAR PRODUIT
            item['price_ttc'] = item['price_ht'] * Decimal('1.20') # Prix unitaire TTC
            item['total_ttc'] = item['total_ht'] * Decimal('1.20') # Prix total TTC pour la ligne
            
            yield item



