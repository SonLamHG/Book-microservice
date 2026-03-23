import logging

logger = logging.getLogger(__name__)


def handle_user_created(data):
    """Auto-create staff profile when a STAFF user registers via auth-service."""
    from app.models import Staff

    auth_user_id = data.get('user_id')
    if not auth_user_id:
        return
    if Staff.objects.filter(auth_user_id=auth_user_id).exists():
        logger.info("Staff profile for auth_user_id=%s already exists", auth_user_id)
        return
    Staff.objects.create(
        name=data.get('username', ''),
        email=data.get('email', ''),
        auth_user_id=auth_user_id,
    )
    logger.info("Created staff profile for auth_user_id=%s", auth_user_id)


BINDINGS = [
    ('user.created.staff', handle_user_created),
]
