from django.core.exceptions import ValidationError
from django.db.models import QuerySet

from api.models import User

VALID_ROLES = {choice[0] for choice in User.ROLE_CHOICES}
ALLOWED_UPDATE_FIELDS = {"email", "first_name", "last_name", "role", "is_active"}

def validate_role(role: str) -> None:
    if role not in VALID_ROLES:
        raise ValidationError(
            f"Invalid role '{role}'. Must be one of: {', '.join(sorted(VALID_ROLES))}.",
            code="invalid_role",
        )

def list_users(
    *,
    role: str | None = None,
    is_active: bool | None = True,
) -> QuerySet[User]:
    """List users filtered by optional role and active status, ordered by username."""
    queryset = User.objects.all()
    if role is not None:
        queryset = queryset.filter(role=role)
    if is_active is not None:
        queryset = queryset.filter(is_active=is_active)
    return queryset.order_by("username")

def get_user_by_id(user_id: int) -> User:
    """Fetch a single user by primary key."""
    return User.objects.get(pk=user_id)

def create_user(
    *,
    username: str,
    password: str,
    email: str = "",
    role: str = "WORKER",
    first_name: str = "",
    last_name: str = "",
) -> User:
    """Validate role and case-insensitive username uniqueness, then create a user."""
    validate_role(role)
    if User.objects.filter(username__iexact=username).exists():
        raise ValidationError(
            f"A user with username '{username}' already exists.",
            code="duplicate_username",
        )
    return User.objects.create_user(
        username=username,
        password=password,
        email=email,
        role=role,
        first_name=first_name,
        last_name=last_name,
    )

def update_user(user: User, **fields) -> User:
    """Update allowed profile fields and re-hash password when supplied."""
    raw_password = fields.pop("password", None)
    if "role" in fields:
        validate_role(fields["role"])

    for field_name, value in fields.items():
        if field_name in ALLOWED_UPDATE_FIELDS:
            setattr(user, field_name, value)

    if raw_password is not None:
        user.set_password(raw_password)

    user.save()
    return user

def deactivate_user(user: User) -> User:
    """Soft-deactivate a user to preserve audit integrity on historical sessions."""
    user.is_active = False
    user.save(update_fields=["is_active"])
    return user
