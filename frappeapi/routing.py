import inspect
import json
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Dict, ForwardRef, List, Optional, Set, Type, Union

try:
	from frappe import whitelist
except ImportError:
	from functools import wraps

	def whitelist(methods: Optional[List[str]] = None):
		def decorator(func):
			@wraps(func)
			def wrapper(*args, **kwargs):
				return func(*args, **kwargs)

			return wrapper

		return decorator


from pydantic import PydanticSchemaGenerationError
from pydantic._internal._typing_extra import eval_type_lenient as evaluate_forwardref
from pydantic.fields import FieldInfo
from pydantic_core import PydanticUndefined, PydanticUndefinedType as PydanticUndefinedType
from typing_extensions import Literal
from werkzeug.wrappers import Response as WerkzeugResponse

from frappeapi import params
from frappeapi.models import BaseConfig, Dependant, ModelField
from frappeapi.utils import Default, extract_endpoint_relative_path

Required = PydanticUndefined
Undefined = PydanticUndefined
UndefinedType = PydanticUndefinedType
Validator = Any


class FrappeAPIError(Exception):
	pass


def create_model_field(
	name: str,
	type_: Any,
	class_validators: Optional[Dict[str, Validator]] = None,
	default: Optional[Any] = Undefined,
	required: Union[bool, UndefinedType] = Undefined,
	model_config: Type[BaseConfig] = BaseConfig,
	field_info: Optional[FieldInfo] = None,
	alias: Optional[str] = None,
	mode: Literal["validation", "serialization"] = "validation",
) -> ModelField:
	class_validators = class_validators or {}
	field_info = field_info or FieldInfo(annotation=type_, default=default, alias=alias)
	kwargs = {"name": name, "field_info": field_info, "mode": mode}

	try:
		return ModelField(**kwargs)  # type: ignore[arg-type]
	except (RuntimeError, PydanticSchemaGenerationError):
		raise FrappeAPIError(
			"Invalid args for response field! Hint: "
			f"check that {type_} is a valid Pydantic field type. "
			"If you are using a return type annotation that is not a valid Pydantic "
			"field (e.g. Union[Response, dict, None]) you can disable generating the "
			"response model from the type annotation with the path operation decorator "
			"parameter response_model=None. Read more: "
			"https://fastapi.tiangolo.com/tutorial/response-model/"
		) from None


@dataclass
class ParamDetails:
	type_annotation: Any
	field: Optional[ModelField]


def analyze_param(
	*,
	param_name: str,
	annotation: Any,
	value: Any,
):
	field_info = None
	type_annotation: Any = Any
	use_annotation: Any = Any
	if annotation is not inspect.Signature.empty:
		use_annotation = annotation
		type_annotation = annotation

	if field_info is None:
		default_value = value if value is not inspect.Signature.empty else Required
		field_info = params.Query(annotation=use_annotation, default=default_value)

	field = None
	if field_info is not None:
		if isinstance(field_info, params.Param) and getattr(field_info, "in_", None) is None:
			field_info.in_ = params.ParamTypes.query

		use_annotation_from_field_info = use_annotation
		if not field_info.alias and getattr(field_info, "convert_underscores", None):
			alias = param_name.replace("_", "-")
		else:
			alias = field_info.alias or param_name
		field_info.alias = alias

		field = create_model_field(
			name=param_name,
			type_=use_annotation_from_field_info,
			default=field_info.default,
			alias=alias,
			required=field_info.default in (Required, Undefined),
			field_info=field_info,
		)

	return ParamDetails(type_annotation=type_annotation, field=field)


def get_typed_annotation(annotation: Any, globalns: Dict[str, Any]) -> Any:
	if isinstance(annotation, str):
		annotation = ForwardRef(annotation)
		annotation = evaluate_forwardref(annotation, globalns, globalns)
	return annotation


def add_param_to_fields(*, field: ModelField, dependant: Dependant) -> None:
	field_info = field.field_info
	field_info_in = getattr(field_info, "in_", None)
	if field_info_in == params.ParamTypes.query:
		dependant.query_params.append(field)
	elif field_info_in == params.ParamTypes.header:
		dependant.header_params.append(field)
	else:
		assert (
			field_info_in == params.ParamTypes.cookie
		), f"non-body parameters must be in path, query, header or cookie: {field.name}"
		dependant.cookie_params.append(field)


class APIRoute:
	def __init__(
		self,
		path: str,
		func: Callable,
		*,
		methods: Optional[Union[Set[str], List[str]]] = None,
		response_model: Any = None,
		status_code: Optional[int] = None,
		description: Optional[str] = None,
		tags: Optional[List[Union[str, Enum]]] = None,
		summary: Optional[str] = None,
		include_in_schema: bool = True,
	):
		self.path = path
		self.func = func

		if methods is None:
			methods = ["GET"]
		self.methods: Set[str] = {method.upper() for method in methods}

		self.response_model = response_model
		self.status_code = status_code
		self.description = description
		self.tags = tags
		self.summary = summary
		self.include_in_schema = include_in_schema

	def get_typed_signature(self) -> inspect.Signature:
		signature = inspect.signature(self.func)
		globalns = getattr(self.func, "__globals__", {})
		typed_params = [
			inspect.Parameter(
				name=param.name,
				kind=param.kind,
				default=param.default,
				annotation=get_typed_annotation(param.annotation, globalns),
			)
			for param in signature.parameters.values()
		]
		typed_signature = inspect.Signature(typed_params)
		return typed_signature

	def handle_request(self, *args, **kwargs):
		try:
			# TODO: Here we will do all the parsing, validation, and serialization ...etc
			endpoint_signature = self.get_typed_signature()
			signature_params = endpoint_signature.parameters
			dependant = Dependant(
				call=self.func,
				name=None,
				path=self.path,
				security_scopes=None,
				use_cache=True,
			)

			for param_name, param in signature_params.items():
				param_details = analyze_param(
					param_name=param_name, annotation=param.annotation, value=param.default
				)
				assert param_details.field is not None
				add_param_to_fields(field=param_details.field, dependant=dependant)

			assert dependant.call is not None, "dependant.call must be a function"

			# Remove known Frappe-specific arguments
			kwargs.pop("cmd", None)

			# Get the function's signature
			sig = inspect.signature(self.func)

			# Filter arguments to only those the function expects
			bound_args = sig.bind(*args, **kwargs)
			bound_args.apply_defaults()

			# Call the function with the filtered arguments
			result = self.func(*bound_args.args, **bound_args.kwargs)

			# Convert the result to JSON and return a response
			response_content = json.dumps(result)
			return WerkzeugResponse(
				response_content, status=self.status_code or 200, mimetype="application/json"
			)
		except Exception as exc:
			error_response = {"detail": str(exc)}
			response_body = json.dumps(error_response)
			return WerkzeugResponse(response_body, status=500, mimetype="application/json")


class APIRouter:
	def __init__(
		self,
		prefix: str = "/api/method",
		default_response_class: Type[WerkzeugResponse] = Default(WerkzeugResponse),
	):
		if prefix:
			assert prefix.startswith("/"), "A path prefix must start with '/'"
			assert not prefix.endswith(
				"/"
			), "A path prefix must not end with '/', as the routes will start with '/'"
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
		methods: Optional[Union[Set[str], List[str]]] = None,
	):
		path = self.prefix + extract_endpoint_relative_path(func) + "." + func.__name__
		route = APIRoute(
			path,
			func,
			methods=methods,
			response_model=response_model,
			status_code=status_code,
			description=description,
			tags=tags,
			summary=summary,
			include_in_schema=include_in_schema,
		)
		self.routes.append(route)
		return route

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
		def decorator(func: Callable):
			@whitelist(methods=methods)
			def wrapper(*args, **kwargs):
				route = self.add_api_route(
					func,
					response_model=response_model,
					status_code=status_code,
					description=description,
					tags=tags,
					summary=summary,
					include_in_schema=include_in_schema,
					methods=methods,
				)
				return route.handle_request(*args, **kwargs)

			return wrapper

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

	def post(
		self,
		*,
		response_model: Any = None,
		status_code: Optional[int] = None,
		description: Optional[str] = None,
		tags: Optional[List[Union[str, Enum]]] = None,
		summary: Optional[str] = None,
		include_in_schema: bool = True,
	):
		pass

	def put(
		self,
		*,
		response_model: Any = None,
		status_code: Optional[int] = None,
		description: Optional[str] = None,
		tags: Optional[List[Union[str, Enum]]] = None,
		summary: Optional[str] = None,
		include_in_schema: bool = True,
	):
		pass

	def delete(
		self,
		*,
		response_model: Any = None,
		status_code: Optional[int] = None,
		description: Optional[str] = None,
		tags: Optional[List[Union[str, Enum]]] = None,
		summary: Optional[str] = None,
		include_in_schema: bool = True,
	):
		pass

	def patch(
		self,
		*,
		response_model: Any = None,
		status_code: Optional[int] = None,
		description: Optional[str] = None,
		tags: Optional[List[Union[str, Enum]]] = None,
		summary: Optional[str] = None,
		include_in_schema: bool = True,
	):
		pass

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
		pass

	def head(
		self,
		*,
		response_model: Any = None,
		status_code: Optional[int] = None,
		description: Optional[str] = None,
		tags: Optional[List[Union[str, Enum]]] = None,
		summary: Optional[str] = None,
		include_in_schema: bool = True,
	):
		pass
