from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend


class EmailBackend(ModelBackend):
    """Email login, with username fallback only for legacy users without email."""

    def authenticate(self, request, username=None, password=None, **kwargs):
        identifier = (kwargs.get("email") or username or "").strip()
        if not identifier or password is None:
            return None

        User = get_user_model()
        matches = list(User._default_manager.filter(email__iexact=identifier).exclude(email="")[:2])
        if len(matches) == 1:
            user = matches[0]
        elif len(matches) > 1:
            return None  # Ambiguous email: do not select an arbitrary account.
        else:
            # Existing accounts without an email can still use their original username.
            matches = list(User._default_manager.filter(username=identifier, email="")[:2])
            if len(matches) != 1:
                User().set_password(password)  # Similar hashing cost for unknown accounts.
                return None
            user = matches[0]

        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
