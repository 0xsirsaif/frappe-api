from fastapi.utils import is_body_allowed_for_status_code
from werkzeug.wrappers import Request as WerkzeugRequest, Response as WerkzeugResponse

from frappeapi.exceptions import HTTPException, RequestValidationError, ResponseValidationError
from frappeapi.responses import JSONResponse
import traceback

try:
	import frappe  # type: ignore[import-not-found]
	from frappe import whitelist  # type: ignore[import-not-found]
except ImportError:
	from unittest.mock import MagicMock

	frappe = MagicMock()
	whitelist = MagicMock()


def request_validation_exception_handler(request: WerkzeugRequest, exc: RequestValidationError) -> WerkzeugResponse:
	return JSONResponse(content={"detail": exc.errors()}, status_code=422)


def http_exception_handler(request: WerkzeugRequest, exc: HTTPException) -> WerkzeugResponse:
	traceback.print_exc()

	headers = getattr(exc, "headers", None)
	if not is_body_allowed_for_status_code(exc.status_code):
		return JSONResponse(status_code=exc.status_code, headers=headers)

	frappe.log_error(traceback.format_exc(), "HTTP Exception")
	return JSONResponse(content={"detail": exc.detail}, status_code=exc.status_code, headers=headers)


def response_validation_exception_handler(request: WerkzeugRequest, exc: ResponseValidationError) -> WerkzeugResponse:
	"""
	Return an empty response with a 500 status code to indicate that the response body is invalid.

	> If the data is invalid (e.g. you are missing a field), it means that your app code is broken,
	> not returning what it should, and it will return a server error instead of returning incorrect data.
	> This way you and your clients can be certain that they will receive the data and the data shape expected.
	"""
	traceback.print_exc()
	frappe.log_error(traceback.format_exc(), "Response Validation Exception")
	return JSONResponse(content={"detail": exc.errors()}, status_code=500)
