from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect

def admin_or_manager_required(view_func):
    """
    Restreint l'accès aux utilisateurs avec rôle admin ou gestionnaire
    """
    def _wrapped_view(request, *args, **kwargs):
        if request.user.is_authenticated:
            if request.user.is_manager or request.user.is_admin_role:
                return view_func(request, *args, **kwargs)
            else:
                raise PermissionDenied("Vous n'avez pas la permission d'accéder à cette page.")
        else:
            return redirect('products:login')  # redirige si non connecté
    return _wrapped_view
