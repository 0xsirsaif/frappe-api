import json

from werkzeug.wrappers import Request as WerkzeugRequest, Response as WerkzeugResponse

from frappeapi.exceptions import HTTPException, RequestValidationError
from frappeapi.utils import is_body_allowed_for_status_code


def request_validation_exception_handler(request: WerkzeugRequest, exc: RequestValidationError) -> WerkzeugResponse:
	return WerkzeugResponse(response=json.dumps({"detail": exc.errors()}), status=422, content_type="application/json")


def http_exception_handler(request: WerkzeugRequest, exc: HTTPException) -> WerkzeugResponse:
	headers = getattr(exc, "headers", None)
	if not is_body_allowed_for_status_code(exc.status_code):
		return WerkzeugResponse(status=exc.status_code, headers=headers)

	return WerkzeugResponse({"detail": exc.detail}, status=exc.status_code, headers=headers)
