# shop/emails.py
from django.core.mail import send_mail
from django.conf import settings

def send_order_confirmation_email(order):
    send_mail(
        subject=f"Confirmation commande #{order.id}",
        message=f"Merci pour votre commande. Total: {order.total_price}",
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[order.email],
    )

def send_new_order_admin_email(order):
    send_mail(
        subject=f"Nouvelle commande #{order.id}",
        message=f"Une nouvelle commande a été passée. Total: {order.total_price}",
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[settings.ADMIN_EMAIL],
    )
