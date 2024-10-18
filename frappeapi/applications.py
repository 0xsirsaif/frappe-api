from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Sequence, Type, Union

from fastapi.datastructures import Default
from fastapi.params import Depends
from werkzeug.wrappers import Request as WerkzeugRequest, Response as WerkzeugResponse

from frappeapi.responses import JSONResponse
from frappeapi.routing import APIRouter


class FrappeAPI:
	def __init__(
		self,
		title: Optional[str] = None,
		summary: Optional[str] = None,
		description: Optional[str] = None,
		version: Optional[str] = None,
		servers: Optional[List[Dict[str, Union[str, Any]]]] = None,
		dependencies: Optional[Sequence[Depends]] = None,
		default_response_class: Type[WerkzeugResponse] = Default(JSONResponse),
		middleware: Optional[Sequence] = None,
		exception_handlers: Optional[
			Dict[
				Union[int, Type[Exception]],
				Callable[[WerkzeugResponse, Any], WerkzeugResponse],
			]
		] = None,
	):
		self.title = title
		self.summary = summary
		self.description = description
		self.version = version
		self.servers = servers

		self.exception_handlers: Dict[Type[Exception], Callable] = (
			{} if exception_handlers is None else exception_handlers
		)
		self.router = APIRouter(
			exception_handlers=self.exception_handlers, default_response_class=default_response_class
		)

	def get(
		self,
		*,
		response_model: Any = Default(None),
		status_code: Optional[int] = None,
		description: Optional[str] = None,
		tags: Optional[List[Union[str, Enum]]] = None,
		summary: Optional[str] = None,
		include_in_schema: bool = True,
		response_class: Type[WerkzeugResponse] = Default(JSONResponse),
	):
		return self.router.get(
			response_model=response_model,
			status_code=status_code,
			description=description,
			tags=tags,
			summary=summary,
			include_in_schema=include_in_schema,
			response_class=response_class,
		)

	def post(
		self,
		*,
		response_model: Any = Default(None),
		status_code: Optional[int] = None,
		description: Optional[str] = None,
		tags: Optional[List[Union[str, Enum]]] = None,
		summary: Optional[str] = None,
		include_in_schema: bool = True,
		response_class: Type[WerkzeugResponse] = Default(JSONResponse),
	):
		return self.router.post(
			response_model=response_model,
			status_code=status_code,
			description=description,
			tags=tags,
			summary=summary,
			include_in_schema=include_in_schema,
			response_class=response_class,
		)

	def put(
		self,
		*,
		response_model: Any = Default(None),
		status_code: Optional[int] = None,
		description: Optional[str] = None,
		tags: Optional[List[Union[str, Enum]]] = None,
		summary: Optional[str] = None,
		include_in_schema: bool = True,
		response_class: Type[WerkzeugResponse] = Default(JSONResponse),
	):
		return self.router.put(
			response_model=response_model,
			status_code=status_code,
			description=description,
			tags=tags,
			summary=summary,
			include_in_schema=include_in_schema,
			response_class=response_class,
		)

	def delete(
		self,
		*,
		response_model: Any = Default(None),
		status_code: Optional[int] = None,
		description: Optional[str] = None,
		tags: Optional[List[Union[str, Enum]]] = None,
		summary: Optional[str] = None,
		include_in_schema: bool = True,
		response_class: Type[WerkzeugResponse] = Default(JSONResponse),
	):
		return self.router.delete(
			response_model=response_model,
			status_code=status_code,
			description=description,
			tags=tags,
			summary=summary,
			include_in_schema=include_in_schema,
			response_class=response_class,
		)

	def patch(
		self,
		*,
		response_model: Any = Default(None),
		status_code: Optional[int] = None,
		description: Optional[str] = None,
		tags: Optional[List[Union[str, Enum]]] = None,
		summary: Optional[str] = None,
		include_in_schema: bool = True,
		response_class: Type[WerkzeugResponse] = Default(JSONResponse),
	):
		return self.router.patch(
			response_model=response_model,
			status_code=status_code,
			description=description,
			tags=tags,
			summary=summary,
			include_in_schema=include_in_schema,
			response_class=response_class,
		)

	def options(
		self,
		*,
		response_model: Any = None,
		status_code: Optional[int] = None,
		description: Optional[str] = None,
		tags: Optional[List[Union[str, Enum]]] = None,
		summary: Optional[str] = None,
		include_in_schema: bool = True,
		response_class: Type[WerkzeugResponse] = Default(JSONResponse),
	):
		return self.router.options(
			response_model=response_model,
			status_code=status_code,
			description=description,
			tags=tags,
			summary=summary,
			include_in_schema=include_in_schema,
			response_class=response_class,
		)

	def head(
		self,
		*,
		response_model: Any = Default(None),
		status_code: Optional[int] = None,
		description: Optional[str] = None,
		tags: Optional[List[Union[str, Enum]]] = None,
		summary: Optional[str] = None,
		include_in_schema: bool = True,
		response_class: Type[WerkzeugResponse] = Default(JSONResponse),
	):
		return self.router.head(
			response_model=response_model,
			status_code=status_code,
			description=description,
			tags=tags,
			summary=summary,
			include_in_schema=include_in_schema,
			response_class=response_class,
		)

	def exception_handler(self, exc_class: Type[Exception]) -> Callable:
		"""
		Add an exception handler to the application.

		Exception handlers are used to handle exceptions that are raised during the processing of a request.
		"""

		def decorator(func: Callable[[WerkzeugRequest, Exception], WerkzeugResponse]):
			self.exception_handlers[exc_class] = func
			return func

		return decorator
