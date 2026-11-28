from http import HTTPStatus

from django.core.exceptions import ObjectDoesNotExist
from django.core.exceptions import ValidationError as DjangoValidationError
from django.http import Http404
from rest_framework import status
from rest_framework.exceptions import APIException, ValidationError as DRFValidationError
from rest_framework.response import Response
from rest_framework.views import exception_handler

def get_status_title(status_code: int) -> str:
    try:
        return HTTPStatus(status_code).phrase
    except ValueError:
        return "Error"

def problem_detail_exception_handler(exc, context):
    """Normalize DRF and Django ValidationError exceptions into Problem Detail payloads."""
    if isinstance(exc, DjangoValidationError):
        detail_message = (
            exc.messages[0]
            if getattr(exc, "messages", None)
            else str(exc)
        )
        code = getattr(exc, "code", None) or "validation_error"
        payload = {
            "title": get_status_title(status.HTTP_400_BAD_REQUEST),
            "status": status.HTTP_400_BAD_REQUEST,
            "detail": detail_message,
            "code": code,
        }
        if hasattr(exc, "message_dict"):
            payload["errors"] = exc.message_dict
        return Response(payload, status=status.HTTP_400_BAD_REQUEST)

    if isinstance(exc, ObjectDoesNotExist) and not isinstance(exc, Http404):
        exc = Http404(str(exc))

    response = exception_handler(exc, context)
    if response is None:
        return None

    status_code = response.status_code
    payload: dict = {
        "title": get_status_title(status_code),
        "status": status_code,
        "detail": "",
        "code": "error",
    }

    if isinstance(exc, DRFValidationError):
        payload["detail"] = "Request validation failed."
        payload["code"] = "validation_error"
        payload["errors"] = response.data
    elif isinstance(exc, Http404):
        payload["detail"] = str(exc) or "Resource not found."
        payload["code"] = "not_found"
    elif isinstance(exc, APIException):
        detail = response.data.get("detail") if isinstance(response.data, dict) else response.data
        payload["detail"] = str(detail) if detail is not None else exc.default_detail
        payload["code"] = getattr(exc, "default_code", "error")
        if hasattr(detail, "code") and detail.code:
            payload["code"] = str(detail.code)
    else:
        payload["detail"] = str(exc)

    response.data = payload
    return response
