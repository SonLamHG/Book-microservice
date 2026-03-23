import logging

logger = logging.getLogger(__name__)


def handle_user_created(data):
    """Auto-create manager profile when a MANAGER user registers via auth-service."""
    from app.models import Manager

    auth_user_id = data.get('user_id')
    if not auth_user_id:
        return
    if Manager.objects.filter(auth_user_id=auth_user_id).exists():
        logger.info("Manager profile for auth_user_id=%s already exists", auth_user_id)
        return
    Manager.objects.create(
        name=data.get('username', ''),
        email=data.get('email', ''),
        auth_user_id=auth_user_id,
    )
    logger.info("Created manager profile for auth_user_id=%s", auth_user_id)


BINDINGS = [
    ('user.created.manager', handle_user_created),
]
