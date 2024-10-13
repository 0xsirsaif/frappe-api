from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Type, Union

from frappeapi.routing import APIRouter
from frappeapi.utils import Default


class FrappeAPI:
	def __init__(
		self,
		title: str = "FrappeAPI",
		summary: Optional[str] = None,
		description: str = "",
		version: str = "0.1.0",
		servers: Optional[List[Dict[str, Union[str, Any]]]] = None,
		exception_handlers: Optional[Dict[Type[Exception], Callable]] = None,
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
			exception_handlers=self.exception_handlers,
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
	):
		return self.router.get(
			response_model=response_model,
			status_code=status_code,
			description=description,
			tags=tags,
			summary=summary,
			include_in_schema=include_in_schema,
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
	):
		return self.router.post(
			response_model=response_model,
			status_code=status_code,
			description=description,
			tags=tags,
			summary=summary,
			include_in_schema=include_in_schema,
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
	):
		return self.router.put(
			response_model=response_model,
			status_code=status_code,
			description=description,
			tags=tags,
			summary=summary,
			include_in_schema=include_in_schema,
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
	):
		return self.router.delete(
			response_model=response_model,
			status_code=status_code,
			description=description,
			tags=tags,
			summary=summary,
			include_in_schema=include_in_schema,
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
	):
		return self.router.patch(
			response_model=response_model,
			status_code=status_code,
			description=description,
			tags=tags,
			summary=summary,
			include_in_schema=include_in_schema,
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
	):
		return self.router.options(
			response_model=response_model,
			status_code=status_code,
			description=description,
			tags=tags,
			summary=summary,
			include_in_schema=include_in_schema,
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
	):
		return self.router.head(
			response_model=response_model,
			status_code=status_code,
			description=description,
			tags=tags,
			summary=summary,
			include_in_schema=include_in_schema,
		)

	def exception_handler(self, exc: Exception):
		"""
		Add an exception handler to the application.

		Exception handlers are used to handle exceptions that are raised during the processing of a request.
		"""

		def decorator(handler: Callable):
			self.exception_handlers[exc] = handler
			return handler

		return decorator
