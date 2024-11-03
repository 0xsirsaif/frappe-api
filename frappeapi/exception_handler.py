from fastapi.utils import is_body_allowed_for_status_code
from werkzeug.wrappers import Request as WerkzeugRequest, Response as WerkzeugResponse

from frappeapi.exceptions import HTTPException, RequestValidationError, ResponseValidationError
from frappeapi.responses import JSONResponse


def request_validation_exception_handler(request: WerkzeugRequest, exc: RequestValidationError) -> WerkzeugResponse:
	return JSONResponse(content={"detail": exc.errors()}, status_code=422)


def http_exception_handler(request: WerkzeugRequest, exc: HTTPException) -> WerkzeugResponse:
	headers = getattr(exc, "headers", None)
	if not is_body_allowed_for_status_code(exc.status_code):
		return JSONResponse(status_code=exc.status_code, headers=headers)

	return JSONResponse(content={"detail": exc.detail}, status_code=exc.status_code, headers=headers)


def response_validation_exception_handler(request: WerkzeugRequest, exc: ResponseValidationError) -> WerkzeugResponse:
	"""
	Return an empty response with a 500 status code to indicate that the response body is invalid.

	> If the data is invalid (e.g. you are missing a field), it means that your app code is broken,
	> not returning what it should, and it will return a server error instead of returning incorrect data.
	> This way you and your clients can be certain that they will receive the data and the data shape expected.
	"""
	return JSONResponse(content={"detail": exc.errors()}, status_code=500)
