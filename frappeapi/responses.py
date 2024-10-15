import json
from typing import Any, Mapping, Optional

from werkzeug.wrappers import Response


class JSONResponse(Response):
	"""
	A custom Werkzeug Response class for JSON content.
	"""

	default_mimetype = "application/json"

	def __init__(
		self,
		content: Any,
		status: int = 200,
		headers: Optional[Mapping[str, str]] = None,
		mimetype: Optional[str] = None,
		content_type: Optional[str] = None,
	) -> None:
		"""
		Initialize the JSONResponse.

		Args:
			content: The content to be JSON-encoded.
			status: HTTP status code.
			headers: Additional headers to include in the response.
			mimetype: The mimetype to use. If not provided, uses the default_mimetype.
			content_type: The content type to use. If provided, overrides mimetype.
		"""
		if content_type is None:
			content_type = mimetype or self.default_mimetype

		# JSON-encode the content
		json_content = json.dumps(
			content,
			ensure_ascii=False,
			allow_nan=False,
			indent=None,
			separators=(",", ":"),
		)

		super().__init__(json_content, status=status, headers=headers, content_type=content_type)

	def get_data(self, as_text: bool = False) -> bytes:
		"""
		Get the response body as bytes or text.

		Args:
			as_text: If True, return the body as a string instead of bytes.

		Returns:
			The response body as bytes or string.
		"""
		return self.response[0] if as_text else self.response[0].encode("utf-8")
