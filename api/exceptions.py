from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status
from loguru import logger

def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    view_name = context.get('view').__class__.__name__ if context and context.get('view') else 'UnknownView'
    request = context.get('request') if context else None
    method = request.method if request else 'UNKNOWN'
    path = request.path if request else 'UNKNOWN'

    if response is not None:
        if response.status_code >= 400:
            logger.error(
                f"HTTP {response.status_code} on {method} {path} in {view_name}: {response.data} (Exception: {exc})"
            )
    else:
        logger.error(
            f"Unhandled exception on {method} {path} in {view_name}: {exc}",
            exc_info=exc,
        )
        response = Response(
            {"detail": "Internal server error."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

    return response
