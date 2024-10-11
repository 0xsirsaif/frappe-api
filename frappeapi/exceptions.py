import http
from typing import Any, Sequence


class FrappeAPIError(Exception):
	pass


class ErrorWrapper(Exception):
	pass


class HTTPException(Exception):
	def __init__(
		self,
		status_code: int,
		detail: str | None = None,
		headers: dict[str, str] | None = None,
	) -> None:
		if detail is None:
			detail = http.HTTPStatus(status_code).phrase
		self.status_code = status_code
		self.detail = detail
		self.headers = headers

	def __str__(self) -> str:
		return f"{self.status_code}: {self.detail}"

	def __repr__(self) -> str:
		class_name = self.__class__.__name__
		return f"{class_name}(status_code={self.status_code!r}, detail={self.detail!r})"


class ValidationException(Exception):
	def __init__(self, errors: Sequence[Any]) -> None:
		self._errors = errors

	def errors(self) -> Sequence[Any]:
		return self._errors


class RequestValidationError(ValidationException):
	def __init__(self, errors: Sequence[Any], *, body: Any = None) -> None:
		super().__init__(errors)
		self.body = body
