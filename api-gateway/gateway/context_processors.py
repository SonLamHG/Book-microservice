def flash_messages(request):
    message = request.session.pop('flash_message', None)
    flash_type = request.session.pop('flash_type', None)
    user_data = request.session.get('user_data', {})
    return {
        'flash_message': message,
        'flash_type': flash_type or 'info',
        'user_data': user_data,
        'user_role': user_data.get('role', ''),
        'customer_id': request.session.get('customer_id'),
    }
