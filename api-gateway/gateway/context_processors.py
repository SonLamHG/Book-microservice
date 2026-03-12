def flash_messages(request):
    message = request.session.pop('flash_message', None)
    flash_type = request.session.pop('flash_type', None)
    return {'flash_message': message, 'flash_type': flash_type or 'info'}
