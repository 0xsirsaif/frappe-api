from typing import Any, Callable, Enum, List, Optional, Type, Union

from werkzeug.wrappers import Response as WerkzeugResponse

from .utils import (
	extract_endpoint_relative_path,
)


class APIRoute:
	def __init__(
		self,
		path: str,
		func: Callable,
		*,
		methods: List[str],
		response_model: Any = None,
		status_code: Optional[int] = None,
		description: Optional[str] = None,
		tags: Optional[List[Union[str, Enum]]] = None,
		summary: Optional[str] = None,
		include_in_schema: bool = True,
	):
		self.path = path
		self.func = func
		self.methods = methods
		self.response_model = response_model
		self.status_code = status_code
		self.description = description
		self.tags = tags
		self.summary = summary
		self.include_in_schema = include_in_schema


class APIRouter:
	def __init__(
		self,
		prefix: str,
		default_response_class: Type[WerkzeugResponse] = WerkzeugResponse,
	):
		if prefix:
			assert prefix.startswith("/"), "A path prefix must start with '/'"  # noqa: S101
			assert not prefix.endswith(  # noqa: S101
				"/"
			), "A path prefix must not end with '/', as the routes will start with '/'"
		else:
			prefix = "/api/method"

		self.prefix = prefix
		self.default_response_class = default_response_class
		self.routes: List[APIRoute] = []

	def add_api_route(
		self,
		func: Callable,
		*,
		response_model: Any = None,
		status_code: Optional[int] = None,
		description: Optional[str] = None,
		tags: Optional[List[Union[str, Enum]]] = None,
		summary: Optional[str] = None,
		include_in_schema: bool = True,
		methods: Optional[List[str]] = None,
	):
		path = self.prefix + extract_endpoint_relative_path(func) + "." + func.__name__
		route = APIRoute(
			path,
			func,
			methods,
			response_model,
			status_code,
			description,
			tags,
			summary,
			include_in_schema,
		)
		self.routes.append(route)

	def api_route(
		self,
		*,
		response_model: Any = None,
		status_code: Optional[int] = None,
		description: Optional[str] = None,
		tags: Optional[List[Union[str, Enum]]] = None,
		summary: Optional[str] = None,
		include_in_schema: bool = True,
		methods: Optional[List[str]] = None,
	):
		def decorator(func):
			self.add_api_route(
				func,
				response_model=response_model,
				status_code=status_code,
				description=description,
				tags=tags,
				summary=summary,
				include_in_schema=include_in_schema,
				methods=methods,
			)

		return decorator

	def get(
		self,
		*,
		response_model: Any = None,
		status_code: Optional[int] = None,
		description: Optional[str] = None,
		tags: Optional[List[Union[str, Enum]]] = None,
		summary: Optional[str] = None,
		include_in_schema: bool = True,
	):
		return self.api_route(
			methods=["GET"],
			response_model=response_model,
			status_code=status_code,
			description=description,
			tags=tags,
			summary=summary,
			include_in_schema=include_in_schema,
		)

	def post(self):
		pass

	def put(self):
		pass

	def delete(self):
		pass

	def patch(self):
		pass

	def options(self):
		pass

	def head(self):
		pass
