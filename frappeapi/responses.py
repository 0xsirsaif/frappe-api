import json
from http import HTTPStatus
from typing import Any, Optional

from fastapi.encoders import jsonable_encoder
from werkzeug.wrappers import Response


class JSONResponse(Response):
	"""
	A custom Werkzeug Response class for JSON content.
	"""

	media_type = "application/json"
	default_mimetype = "application/json"

	def __init__(
		self,
		content: Any = None,
		status_code: int | str | HTTPStatus | None = 200,
		headers: Optional[dict] = None,
		media_type: str = "application/json",
		**kwargs,
	):
		"""
		Initialize the JSONResponse.

		Args:
			response: The content to be JSON-encoded.
			status_code: HTTP status code.
			headers: Additional headers to include in the response.
			media_type: The media type to use. If not provided, uses the default_mimetype.
			content_type: The content type to use. If provided, overrides media_type.
		"""
		if content is not None:
			content = jsonable_encoder(content)
			content = json.dumps(content)

		super().__init__(
			response=content,
			status=status_code,
			headers=headers,
			mimetype=media_type,
			content_type=media_type,
			**kwargs,
		)

	@property
	def json(self) -> Any:
		"""Get the JSON-decoded data."""
		return json.loads(self.get_data(as_text=True))

	@json.setter
	def json(self, value: Any) -> None:
		"""Set new JSON data."""
		encoded_value = jsonable_encoder(value)
		self.set_data(json.dumps(encoded_value))


class PlainTextResponse(Response):
	"""
	A custom Werkzeug Response class for plain text content.
	"""

	media_type = "text/plain"
	default_mimetype = "text/plain"

	def __init__(
		self,
		content: Any = None,
		status_code: int | str | HTTPStatus | None = 200,
		headers: Optional[dict] = None,
		media_type: str = "text/plain",
		**kwargs,
	):
		"""
		Initialize the PlainTextResponse.

		Args:
			content: The content to be returned as plain text.
			status_code: HTTP status code.
			headers: Additional headers to include in the response.
			media_type: The media type to use. If not provided, uses the default_mimetype.
		"""
		if content is not None and not isinstance(content, str):
			content = str(content)

		super().__init__(
			response=content,
			status=status_code,
			headers=headers,
			mimetype=media_type,
			content_type=media_type,
			**kwargs,
		)

	@property
	def text(self) -> str:
		"""Get the text data."""
		return self.get_data(as_text=True)

	@text.setter
	def text(self, value: Any) -> None:
		"""Set new text data."""
		if not isinstance(value, str):
			value = str(value)
		self.set_data(value)
