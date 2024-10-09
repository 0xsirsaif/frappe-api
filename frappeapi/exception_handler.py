import json
from typing import Union

from werkzeug.wrappers import Request as WerkzeugRequest, Response as WerkzeugResponse

from frappeapi.exceptions import HTTPException, RequestValidationError


def is_body_allowed_for_status_code(status_code: Union[int, str, None]) -> bool:
	if status_code is None:
		return True

	# Ref: https://github.com/OAI/OpenAPI-Specification/blob/main/versions/3.1.0.md#patterned-fields-1
	if status_code in {
		"default",
		"1XX",
		"2XX",
		"3XX",
		"4XX",
		"5XX",
	}:
		return True

	current_status_code = int(status_code)
	return not (current_status_code < 200 or current_status_code in {204, 205, 304})


def request_validation_exception_handler(
	request: WerkzeugRequest, exc: RequestValidationError
) -> WerkzeugResponse:
	return WerkzeugResponse(
		response=json.dumps({"detail": exc.errors()}), status=422, content_type="application/json"
	)


def http_exception_handler(request: WerkzeugRequest, exc: HTTPException) -> WerkzeugResponse:
	headers = getattr(exc, "headers", None)
	if not is_body_allowed_for_status_code(exc.status_code):
		return WerkzeugResponse(status=exc.status_code, headers=headers)

	return WerkzeugResponse({"detail": exc.detail}, status=exc.status_code, headers=headers)
