import http
from typing import Any, Sequence


class FrappeAPIError(Exception):
	pass


class ErrorWrapper(Exception):
	pass


class HTTPException(Exception):
	def __init__(
		self,
		status: int,
		detail: str | None = None,
		headers: dict[str, str] | None = None,
	) -> None:
		if detail is None:
			detail = http.HTTPStatus(status).phrase
		self.status = status
		self.detail = detail
		self.headers = headers

	def __str__(self) -> str:
		return f"{self.status}: {self.detail}"

	def __repr__(self) -> str:
		class_name = self.__class__.__name__
		return f"{class_name}(status_code={self.status!r}, detail={self.detail!r})"


class ValidationException(Exception):
	def __init__(self, errors: Sequence[Any]) -> None:
		self._errors = errors

	def errors(self) -> Sequence[Any]:
		return self._errors


class RequestValidationError(ValidationException):
	def __init__(self, errors: Sequence[Any], *, body: Any = None) -> None:
		super().__init__(errors)
		self.body = body


class ResponseValidationError(ValidationException):
	def __init__(self, errors: Sequence[Any], *, body: Any = None) -> None:
		super().__init__(errors)
		self.body = body

	def __str__(self) -> str:
		message = f"{len(self._errors)} validation errors:\n"
		for err in self._errors:
			message += f"  {err}\n"
		return message
