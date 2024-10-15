import json
from http import HTTPStatus
from typing import Any, Optional

from werkzeug.wrappers import Response

from frappeapi.encoders import jsonable_encoder


class JSONResponse(Response):
	"""
	A custom Werkzeug Response class for JSON content.
	"""

	default_mimetype = "application/json"

	def __init__(
		self,
		content: Any = None,
		status: int | str | HTTPStatus | None = None,
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
			response=content, status=status, headers=headers, mimetype=media_type, content_type=media_type, **kwargs
		)

	@property
	def json(self) -> Any:
		"""Get the JSON-decoded data."""
		return json.loads(self.get_data(as_text=True))

	def set_json(self, value: Any) -> None:
		"""Set new JSON data."""
		encoded_value = jsonable_encoder(value)
		self.set_data(json.dumps(encoded_value))

	# Make json a property that can be get and set
	json = property(json.fget, set_json)
