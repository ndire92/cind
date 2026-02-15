from django.shortcuts import redirect

def gestionnaire_required(view_func):
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated or request.user.role != "gestionnaire":
            return redirect("home")
        return view_func(request, *args, **kwargs)
    return wrapper
