import inspect
import json
import types
from collections import deque
from copy import deepcopy
from dataclasses import dataclass
from enum import Enum
from functools import lru_cache
from typing import (
	Any,
	Callable,
	Deque,
	Dict,
	ForwardRef,
	FrozenSet,
	List,
	Mapping,
	Optional,
	Sequence,
	Set,
	Tuple,
	Type,
	Union,
)

try:
	import frappe
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


from pydantic import BaseModel, PydanticSchemaGenerationError, ValidationError
from pydantic._internal._typing_extra import eval_type_lenient as evaluate_forwardref
from pydantic._internal._utils import lenient_issubclass
from pydantic.fields import FieldInfo
from pydantic_core import PydanticUndefined, PydanticUndefinedType
from typing_extensions import Literal, get_args, get_origin
from werkzeug.datastructures import ImmutableMultiDict
from werkzeug.wrappers import (
	Request as WerkzeugRequest,
	Response as WerkzeugResponse,
)

from frappeapi import params
from frappeapi.datastructures import QueryParams
from frappeapi.exception_handler import http_exception_handler, request_validation_exception_handler
from frappeapi.exceptions import ErrorWrapper, FrappeAPIError, HTTPException, RequestValidationError
from frappeapi.models import (
	BaseConfig,
	Dependant,
	ModelField,
	SolvedDependency,
	_normalize_errors,
	_regenerate_error_with_loc,
)
from frappeapi.utils import Default, extract_endpoint_relative_path

Required = PydanticUndefined
Undefined = PydanticUndefined
UndefinedType = PydanticUndefinedType
Validator = Any
UnionType = getattr(types, "UnionType", Union)

sequence_annotation_to_type = {
	Sequence: list,
	List: list,
	list: list,
	Tuple: tuple,
	tuple: tuple,
	Set: set,
	set: set,
	FrozenSet: frozenset,
	frozenset: frozenset,
	Deque: deque,
	deque: deque,
}

sequence_types = tuple(sequence_annotation_to_type.keys())


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


def get_model_fields(model: Type[BaseModel]) -> List[ModelField]:
	return [ModelField(field_info=field_info, name=name) for name, field_info in model.model_fields.items()]


@lru_cache
def get_cached_model_fields(model: Type[BaseModel]) -> List[ModelField]:
	return get_model_fields(model)


def _annotation_is_sequence(annotation: Union[Type[Any], None]) -> bool:
	if lenient_issubclass(annotation, (str, bytes)):
		return False
	return lenient_issubclass(annotation, sequence_types)


def field_annotation_is_sequence(annotation: Union[Type[Any], None]) -> bool:
	origin = get_origin(annotation)
	if origin is Union or origin is UnionType:
		return any(field_annotation_is_sequence(arg) for arg in get_args(annotation))

	return _annotation_is_sequence(annotation) or _annotation_is_sequence(get_origin(annotation))


def is_sequence_field(field: ModelField) -> bool:
	return field_annotation_is_sequence(field.field_info.annotation)


def _get_multidict_value(field: ModelField, values: Mapping[str, Any], alias: Union[str, None] = None) -> Any:
	alias = alias or field.alias
	if is_sequence_field(field) and isinstance(values, (ImmutableMultiDict)):
		value = values.getlist(alias)
	else:
		value = values.get(alias, None)
	if value is None or (is_sequence_field(field) and len(value) == 0):
		if field.required:
			return
		else:
			return deepcopy(field.default)
	return value


def get_missing_field_error(loc: Tuple[str, ...]) -> Dict[str, Any]:
	error = ValidationError.from_exception_data(
		"Field required", [{"type": "missing", "loc": loc, "input": {}}]
	).errors(include_url=False)[0]
	error["input"] = None
	return error  # type: ignore[return-value]


def _validate_value_with_model_field(
	*, field: ModelField, value: Any, values: Dict[str, Any], loc: Tuple[str, ...]
) -> Tuple[Any, List[Any]]:
	if value is None:
		if field.required:
			return None, [get_missing_field_error(loc=loc)]
		else:
			return deepcopy(field.default), []

	v_, errors_ = field.validate(value, values, loc=loc)
	if isinstance(errors_, ErrorWrapper):
		return None, [errors_]
	elif isinstance(errors_, list):
		new_errors = _regenerate_error_with_loc(errors=errors_, loc_prefix=())
		return None, new_errors
	else:
		return v_, []


def request_params_to_args(
	fields: Sequence[ModelField],
	received_params: Union[Mapping[str, Any], QueryParams],
) -> Tuple[Dict[str, Any], List[Any]]:
	values: Dict[str, Any] = {}
	errors: List[Dict[str, Any]] = []

	if not fields:
		return values, errors

	# If there is only one field, and it is a Pydantic BaseModel, then we need to extract all the fields from the model
	first_field = fields[0]
	fields_to_extract = fields
	single_not_embedded_field = False
	if len(fields) == 1 and lenient_issubclass(first_field.type_, BaseModel):
		fields_to_extract = get_cached_model_fields(first_field.type_)
		single_not_embedded_field = True

	params_to_process: Dict[str, Any] = {}
	processed_keys = set()

	for field in fields_to_extract:
		alias = None
		value = _get_multidict_value(field, received_params, alias=alias)
		if value is not None:
			params_to_process[field.name] = value
		processed_keys.add(alias or field.alias)
		processed_keys.add(field.name)

	for key, value in received_params.items():
		if key not in processed_keys:
			params_to_process[key] = value

	if single_not_embedded_field:
		field_info = first_field.field_info
		assert isinstance(field_info, params.Param), "Params must be subclasses of Param"

		loc: Tuple[str, ...] = (field_info.in_.value,)
		v_, errors_ = _validate_value_with_model_field(
			field=first_field, value=params_to_process, values=values, loc=loc
		)

		return {first_field.name: v_}, errors_

	for field in fields:
		value = _get_multidict_value(field, received_params)
		field_info = field.field_info
		assert isinstance(field_info, params.Param), "Params must be subclasses of Param"
		loc = (field_info.in_.value, field.alias)
		v_, errors_ = _validate_value_with_model_field(field=field, value=value, values=values, loc=loc)
		if errors_:
			errors.extend(errors_)
		else:
			values[field.name] = v_

	return values, errors


def solve_dependencies(
	*, dependant: Dependant, request: Union[WerkzeugRequest, Any], response: Optional[WerkzeugResponse] = None
):
	values: Dict[str, Any] = {}
	errors: List[Any] = []
	if response is None:
		response = WerkzeugResponse()
		if "content-length" in response.headers:
			del response.headers["content-length"]

		response.status_code = 200  # Default to OK status

	request_query_params = QueryParams(frappe.request.query_string).to_dict()

	query_values, query_errors = request_params_to_args(dependant.query_params, request_query_params)
	values.update(query_values)
	errors.extend(query_errors)

	return SolvedDependency(
		values=values,
		errors=errors,
		response=response,
	)


class APIRoute:
	def __init__(
		self,
		path: str,
		func: Callable,
		*,
		exception_handlers: Dict[Type[Exception], Callable[[WerkzeugRequest, Exception], WerkzeugResponse]],
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
		self.exception_handlers = exception_handlers

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

			# TODO: Validation and serialization
			errors: List[Any] = []
			# werkzeug.local.LocalProxy
			request = frappe.request
			solved_result = solve_dependencies(dependant=dependant, request=request)
			errors = solved_result.errors
			body = None
			if not errors:
				pass
			else:
				validation_error = RequestValidationError(_normalize_errors(errors), body=body)
				raise validation_error

			result = self.func(**solved_result.values)

			# Convert the result to JSON and return a response
			response_content = json.dumps(result)
			return WerkzeugResponse(
				response_content, status=self.status_code or 200, mimetype="application/json"
			)
		except HTTPException as exc:
			if self.exception_handlers.get(HTTPException):
				return self.exception_handlers[HTTPException](request, exc)
			else:
				return http_exception_handler(request, exc)
		except RequestValidationError as exc:
			if self.exception_handlers.get(RequestValidationError):
				return self.exception_handlers[RequestValidationError](request, exc)
			else:
				return request_validation_exception_handler(request, exc)
		except Exception as exc:
			# Check if there's a custom handler for this exception type
			for exc_type, handler in self.exception_handlers.items():
				if isinstance(exc, exc_type):
					return handler(request, exc)
			raise exc


class APIRouter:
	def __init__(
		self,
		prefix: str = "/api/method",
		default_response_class: Type[WerkzeugResponse] = Default(WerkzeugResponse),
		exception_handlers: Dict[
			Type[Exception], Callable[[WerkzeugRequest, Exception], WerkzeugResponse]
		] = {},
	):
		if prefix:
			assert prefix.startswith("/"), "A path prefix must start with '/'"
			assert not prefix.endswith(
				"/"
			), "A path prefix must not end with '/', as the routes will start with '/'"
		self.prefix = prefix
		self.default_response_class = default_response_class
		self.routes: List[APIRoute] = []
		self.exception_handlers = exception_handlers

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
			exception_handlers=self.exception_handlers,
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
