import dataclasses
import inspect
import re
from copy import copy
from enum import Enum
from typing import (
	Annotated,
	Any,
	Callable,
	Dict,
	List,
	Mapping,
	Optional,
	Sequence,
	Set,
	Tuple,
	Type,
	Union,
)

from typing_extensions import Literal, get_args, get_origin

try:
	import frappe
	from frappe import whitelist
except ImportError:
	from functools import wraps

	class Frappe:
		def __getattr__(self, item):
			return

	frappe = Frappe()

	def whitelist(methods: Optional[List[str]] = None):
		def decorator(func):
			@wraps(func)
			def wrapper(*args, **kwargs):
				return func(*args, **kwargs)

			return wrapper

		return decorator


from fastapi import params
from fastapi._compat import (
	PYDANTIC_V2,
	BaseConfig,
	ModelField,
	RequiredParam as Required,
	Undefined,
	UndefinedType,
	Validator,
	_get_model_config,
	_model_dump,
	copy_field_info,
	get_cached_model_fields,
	is_scalar_field,
	is_scalar_sequence_field,
)
from fastapi.datastructures import Default, DefaultPlaceholder, DefaultType, QueryParams
from fastapi.dependencies.models import Dependant
from fastapi.dependencies.utils import (
	ParamDetails,
	SolvedDependency,
	_get_multidict_value,
	_validate_value_with_model_field,
	add_param_to_fields,
	get_typed_annotation,
)
from fastapi.encoders import jsonable_encoder
from fastapi.types import IncEx
from fastapi.utils import is_body_allowed_for_status_code
from pydantic import BaseModel, PydanticSchemaGenerationError
from pydantic._internal._utils import lenient_issubclass
from pydantic.fields import FieldInfo
from werkzeug.wrappers import (
	Request as WerkzeugRequest,
	Response as WerkzeugResponse,
)

from frappeapi.exception_handler import http_exception_handler, request_validation_exception_handler
from frappeapi.exceptions import FrappeAPIError, HTTPException, RequestValidationError, ResponseValidationError
from frappeapi.responses import JSONResponse
from frappeapi.utils import extract_endpoint_relative_path


def _prepare_response_content(
	res: Any,
	*,
	exclude_unset: bool,
	exclude_defaults: bool = False,
	exclude_none: bool = False,
) -> Any:
	if isinstance(res, BaseModel):
		read_with_orm_mode = getattr(_get_model_config(res), "read_with_orm_mode", None)
		if read_with_orm_mode:
			# Let from_orm extract the data from this model instead of converting
			# it now to a dict.
			# Otherwise, there's no way to extract lazy data that requires attribute
			# access instead of dict iteration, e.g. lazy relationships.
			return res
		return _model_dump(
			res,
			by_alias=True,
			exclude_unset=exclude_unset,
			exclude_defaults=exclude_defaults,
			exclude_none=exclude_none,
		)
	elif isinstance(res, list):
		return [
			_prepare_response_content(
				item,
				exclude_unset=exclude_unset,
				exclude_defaults=exclude_defaults,
				exclude_none=exclude_none,
			)
			for item in res
		]
	elif isinstance(res, dict):
		return {
			k: _prepare_response_content(
				v,
				exclude_unset=exclude_unset,
				exclude_defaults=exclude_defaults,
				exclude_none=exclude_none,
			)
			for k, v in res.items()
		}
	elif dataclasses.is_dataclass(res):
		return dataclasses.asdict(res)

	return res


def serialize_response(
	*,
	field: Optional[ModelField] = None,
	response_content: Any,
	include: Optional[IncEx] = None,
	exclude: Optional[IncEx] = None,
	by_alias: bool = True,
	exclude_unset: bool = False,
	exclude_defaults: bool = False,
	exclude_none: bool = False,
) -> Any:
	if field:
		errors = []
		if not hasattr(field, "serialize"):
			# pydantic v1
			response_content = _prepare_response_content(
				response_content,
				exclude_unset=exclude_unset,
				exclude_defaults=exclude_defaults,
				exclude_none=exclude_none,
			)

		value, errors_ = field.validate(response_content, {}, loc=("response",))

		if isinstance(errors_, list):
			errors.extend(errors_)
		elif errors_:
			errors.append(errors_)

		if errors:
			raise ResponseValidationError(errors=errors, body=response_content)

		if hasattr(field, "serialize"):
			return field.serialize(
				value,
				include=include,
				exclude=exclude,
				by_alias=by_alias,
				exclude_unset=exclude_unset,
				exclude_defaults=exclude_defaults,
				exclude_none=exclude_none,
			)

		return jsonable_encoder(
			value,
			include=include,
			exclude=exclude,
			by_alias=by_alias,
			exclude_unset=exclude_unset,
			exclude_defaults=exclude_defaults,
			exclude_none=exclude_none,
		)
	else:
		return jsonable_encoder(response_content)


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


def analyze_param(
	*,
	param_name: str,
	annotation: Any,
	value: Any,
):
	"""
	Analyzes a single parameter of an API endpoint, extracting and interpreting
	various pieces of information to determine how the parameter should be handled.

	Purpose:
	1. Interpret type annotations and default values of API endpoint parameters.
	2. Handle special cases like `Annotated` types and `Depends` instances.
	3. Create appropriate `FieldInfo` objects for parameter validation and documentation.
	4. Generate `ModelField` instances for use in request parsing and validation.

	Key Concepts:
	- Type Annotations: Used to specify the expected type of a parameter.
	- Annotated: A special type that allows attaching metadata to type hints.
	- FieldInfo: Provides additional information about a field, such as default values, aliases, and validation rules.
	- Depends: Used for dependency injection in the API.
	- ModelField: Represents a field in a Pydantic model, used for validation and serialization.

	Function Flow:
	1. Initialize variables for field_info, depends, and type annotations.
	2. Check if the parameter uses the `Annotated` type:
		- If so, extract the base type and any FrappeAPI-specific annotations.
		- Handle special cases for `FieldInfo` and `Depends` within `Annotated`.
	3. Process `Depends` instances if present in the default value.
	4. Handle cases where `FieldInfo` is provided as the default value.
	5. Assign default values if neither `FieldInfo` nor `Depends` was found.
	6. Create a `ModelField` instance if `FieldInfo` is present.
	7. Perform additional validation for `Query` parameters.

	Special Cases:
	- Annotated with FieldInfo: The function ensures that default values are not set in `Annotated`
	and copies the `FieldInfo` to avoid mutations.
	- Depends: The function handles `Depends` instances both in `Annotated` and as default values,
	ensuring they are not used together.
	- Query Parameters: Additional assertions are made to ensure query parameters are of the correct type
	(scalar or scalar sequence).

	Args:
		param_name (str): The name of the parameter being analyzed.
		annotation (Any): The type annotation of the parameter.
		value (Any): The default value of the parameter.

	Returns:
		ParamDetails: An object containing the resolved type annotation and ModelField (if created).

	Usage Example:
		from typing import Annotated
		from frappeapi import Query

		def my_endpoint(param: Annotated[int, Query(gt=0)] = 1):
			...

		param_details = analyze_param(
			param_name="param", annotation=my_endpoint.__annotations__["param"], value=1
		)

	"""
	field_info = None
	depends = None

	type_annotation: Any = Any
	use_annotation: Any = Any
	if annotation is not inspect.Signature.empty:
		use_annotation = annotation
		type_annotation = annotation

	# Extract Annotated info
	if get_origin(use_annotation) is Annotated:
		annotated_args = get_args(annotation)
		type_annotation = annotated_args[0]
		frappeapi_annotations = [arg for arg in annotated_args[1:] if isinstance(arg, (FieldInfo, params.Depends))]
		frappeapi_specific_annotations = [
			arg for arg in frappeapi_annotations if isinstance(arg, (params.Param, params.Body, params.Depends))
		]
		if frappeapi_specific_annotations:
			frappeapi_annotation: Union[FieldInfo, params.Depends, None] = frappeapi_specific_annotations[-1]
		else:
			frappeapi_annotation = None

		# Set default for Annotated FieldInfo
		if isinstance(frappeapi_annotation, FieldInfo):
			# Copy `field_info` because we mutate `field_info.default` below.
			field_info = copy_field_info(field_info=frappeapi_annotation, annotation=use_annotation)
			assert field_info.default is Undefined or field_info.default is Required, (
				f"`{field_info.__class__.__name__}` default value cannot be set in"
				f" `Annotated` for {param_name!r}. Set the default value with `=` instead."
			)
			if value is not inspect.Signature.empty:
				field_info.default = value
			else:
				field_info.default = Required

		# Get Annotated Depends
		elif isinstance(frappeapi_annotation, params.Depends):
			depends = frappeapi_annotation

	if isinstance(value, params.Depends):
		assert depends is None, (
			"Cannot specify `Depends` in `Annotated` and default value" f" together for {param_name!r}"
		)
		assert field_info is None, (
			"Cannot specify a FastAPI annotation in `Annotated` and `Depends` as a"
			f" default value together for {param_name!r}"
		)
		depends = value

	# Get FieldInfo from default value
	elif isinstance(value, FieldInfo):
		assert field_info is None, (
			"Cannot specify FastAPI annotations in `Annotated` and default value" f" together for {param_name!r}"
		)
		field_info = value
		if PYDANTIC_V2:
			field_info.annotation = type_annotation

	# Get `Depends` from type annotation
	if depends is not None and depends.dependency is None:
		# Copy `depends` before mutating it
		depends = copy(depends)
		depends.dependency = type_annotation

	# Handle default assignations, neither field_info nor depends was not found in Annotated nor default value
	elif field_info is None and depends is None:
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
		if isinstance(field_info, params.Query):
			assert (
				is_scalar_field(field) or is_scalar_sequence_field(field) or lenient_issubclass(field.type_, BaseModel)
			)

	return ParamDetails(type_annotation=type_annotation, depends=None, field=field)


def request_params_to_args(
	fields: Sequence[ModelField],
	received_params: Union[Mapping[str, Any], QueryParams],
) -> Tuple[Dict[str, Any], List[Any]]:
	values: Dict[str, Any] = {}
	errors: List[Dict[str, Any]] = []

	if not fields:
		return values, errors

	# If there is only one field, and it is a Pydantic BaseModel,
	# then we need to extract all the fields from the model
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


def parse_and_validate_request(
	*, dependant: Dependant, request: Union[WerkzeugRequest, Any], response: Optional[WerkzeugResponse] = None
):
	values: Dict[str, Any] = {}
	errors: List[Any] = []
	if response is None:
		response = WerkzeugResponse()
		if "content-length" in response.headers:
			del response.headers["content-length"]

		response.status = 200

	request_query_params = QueryParams(frappe.request.query_string)

	query_values, query_errors = request_params_to_args(dependant.query_params, request_query_params)
	values.update(query_values)
	errors.extend(query_errors)

	return SolvedDependency(values=values, errors=errors, background_tasks=None, response=response, dependency_cache={})


def get_typed_signature(func: Callable[..., Any]) -> inspect.Signature:
	"""
	Generate a typed signature (parameters) for the endpoint function.
	"""
	signature = inspect.signature(func)
	globalns = getattr(func, "__globals__", {})
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


def build_dependant(
	*,
	path: str,
	func: Callable[..., Any],
	name: Optional[str] = None,
	security_scopes: Optional[List[str]] = None,
	use_cache: bool = True,
) -> Dependant:
	endpoint_signature = get_typed_signature(func)
	signature_params = endpoint_signature.parameters
	dependant = Dependant(
		call=func,
		name=name,
		path=path,
		security_scopes=security_scopes,
		use_cache=use_cache,
	)

	for param_name, param in signature_params.items():
		param_details = analyze_param(param_name=param_name, annotation=param.annotation, value=param.default)

		assert param_details.field is not None
		add_param_to_fields(field=param_details.field, dependant=dependant)

	return dependant


def generate_unique_id(route: "APIRoute") -> str:
	operation_id = f"{route.name}{route.path}"
	operation_id = re.sub(r"\W", "_", operation_id)
	assert route.methods
	operation_id = f"{operation_id}_{list(route.methods)[0].lower()}"
	return operation_id


def get_value_or_default(
	first_item: Union[DefaultPlaceholder, DefaultType],
	*extra_items: Union[DefaultPlaceholder, DefaultType],
) -> Union[DefaultPlaceholder, DefaultType]:
	"""
	Pass items or `DefaultPlaceholder`s by descending priority.

	The first one to _not_ be a `DefaultPlaceholder` will be returned.

	Otherwise, the first item (a `DefaultPlaceholder`) will be returned.
	"""
	items = (first_item,) + extra_items
	for item in items:
		if not isinstance(item, DefaultPlaceholder):
			return item
	return first_item


def get_typed_return_annotation(call: Callable[..., Any]) -> Any:
	signature = inspect.signature(call)
	annotation = signature.return_annotation

	if annotation is inspect.Signature.empty:
		return None

	globalns = getattr(call, "__globals__", {})
	return get_typed_annotation(annotation, globalns)


class APIRoute:
	def __init__(
		self,
		func: Callable,
		*,
		exception_handlers: Dict[Type[Exception], Callable[[WerkzeugRequest, Exception], WerkzeugResponse]],
		methods: Optional[Union[Set[str], List[str]]] = None,
		response_model: Any = Default(None),
		status_code: Optional[int] = None,
		description: Optional[str] = None,
		tags: Optional[List[Union[str, Enum]]] = None,
		summary: Optional[str] = None,
		include_in_schema: bool = True,
		response_class: Union[Type[WerkzeugResponse], DefaultPlaceholder] = Default(JSONResponse),
		response_model_include: Optional[IncEx] = None,
		response_model_exclude: Optional[IncEx] = None,
		response_model_by_alias: bool = True,
		response_model_exclude_unset: bool = False,
		response_model_exclude_defaults: bool = False,
		response_model_exclude_none: bool = False,
	):
		self.func = func
		self.prefix = "/api/method"
		self.path = self.prefix + extract_endpoint_relative_path(self.func) + "." + self.func.__name__
		self.name = getattr(self.func, "__name__", None)

		if methods is None:
			methods = ["GET"]
		self.methods: Set[str] = {method.upper() for method in methods}

		if isinstance(response_model, DefaultPlaceholder):
			return_annotation = get_typed_return_annotation(self.func)
			response_model = None if lenient_issubclass(return_annotation, WerkzeugResponse) else return_annotation

		self.response_model = response_model

		self.status_code = status_code

		self.description = description or inspect.cleandoc(self.func.__doc__ or "")
		# if a "form feed" character (page break) is found in the description text,
		# truncate description text to the content preceding the first "form feed"
		self.description = self.description.split("\f")[0].strip()

		self.response_class = response_class

		self.tags = tags
		self.summary = summary
		self.unique_id = generate_unique_id(self)

		self.include_in_schema = include_in_schema
		self.response_model_include = response_model_include
		self.response_model_exclude = response_model_exclude
		self.response_model_by_alias = response_model_by_alias
		self.response_model_exclude_unset = response_model_exclude_unset
		self.response_model_exclude_defaults = response_model_exclude_defaults
		self.response_model_exclude_none = response_model_exclude_none

		self.exception_handlers = exception_handlers

		if self.response_model:
			assert is_body_allowed_for_status_code(
				status_code
			), f"Status code {status_code} must not have a response body"

			response_name = "Response_" + self.unique_id

			self.response_field = create_model_field(
				name=response_name,
				type_=self.response_model,
				mode="serialization",
			)
			self.secure_cloned_response_field = self.response_field
		else:
			self.response_field = None  # type: ignore
			self.secure_cloned_response_field = None

	def handle_request(self, *args, **kwargs):
		request = frappe.request
		try:
			dependent = build_dependant(path=self.path, func=self.func)
			assert dependent.call is not None, "dependant.call must be a function"

			errors: List[Any] = []
			solved_result = parse_and_validate_request(dependant=dependent, request=request)
			errors = solved_result.errors
			body = None
			if not errors:
				request_data = solved_result.values
				raw_response = self.func(**request_data)

				if isinstance(raw_response, WerkzeugResponse):
					# if raw_response.background is None:
					# 	raw_response.background = solved_result.background_tasks
					response = raw_response
				else:
					# response_args: Dict[str, Any] = {"background": solved_result.background_tasks}
					response_args: Dict[str, Any] = {}
					# If status_code was set, use it, otherwise use the default from the
					# # response class, in the case of redirect it's 307
					current_status_code = self.status_code if self.status_code else solved_result.response.status_code
					if current_status_code is not None:
						response_args["status"] = current_status_code
					if solved_result.response.status_code:
						response_args["status"] = solved_result.response.status_code

					content = serialize_response(
						field=self.secure_cloned_response_field,
						response_content=raw_response,
						include=self.response_model_include,
						exclude=self.response_model_exclude,
						by_alias=self.response_model_by_alias,
						exclude_unset=self.response_model_exclude_unset,
						exclude_defaults=self.response_model_exclude_defaults,
						exclude_none=self.response_model_exclude_none,
					)

					if isinstance(self.response_class, DefaultPlaceholder):
						actual_response_class: Type[WerkzeugResponse] = self.response_class.value
					else:
						actual_response_class = self.response_class

					response = actual_response_class(content, **response_args)
					if not is_body_allowed_for_status_code(response.status_code):
						response.body = b""

					for key, value in solved_result.response.headers.items():
						if key not in response.headers:
							response.headers.add(key, value)

					if response is None:
						raise FrappeAPIError("No response object was returned.")

				return response
			else:
				validation_error = RequestValidationError(errors, body=body)
				raise validation_error

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
		except ResponseValidationError as exc:
			if self.exception_handlers.get(ResponseValidationError):
				return self.exception_handlers[ResponseValidationError](request, exc)
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
		default_response_class: Type[WerkzeugResponse] = Default(WerkzeugResponse),
		exception_handlers: Dict[Type[Exception], Callable[[WerkzeugRequest, Exception], WerkzeugResponse]] = None,
	):
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
		response_class: Union[Type[WerkzeugResponse], DefaultPlaceholder] = Default(JSONResponse),
	):
		current_response_class = get_value_or_default(response_class, self.default_response_class)
		route = APIRoute(
			func,
			exception_handlers=self.exception_handlers,
			methods=methods,
			response_model=response_model,
			status_code=status_code,
			description=description,
			tags=tags,
			summary=summary,
			include_in_schema=include_in_schema,
			response_class=current_response_class,
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
		response_class: Type[WerkzeugResponse] = Default(JSONResponse),
	):
		def decorator(func: Callable):
			# TODO: Add allow_guest to the decorator
			# TODO: Validate @has_website_permission
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
					response_class=response_class,
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
		response_class: Type[WerkzeugResponse] = Default(JSONResponse),
	):
		return self.api_route(
			methods=["GET"],
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
		response_model: Any = None,
		status_code: Optional[int] = None,
		description: Optional[str] = None,
		tags: Optional[List[Union[str, Enum]]] = None,
		summary: Optional[str] = None,
		include_in_schema: bool = True,
		response_class: Union[Type[WerkzeugResponse], DefaultPlaceholder] = Default(JSONResponse),
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
		response_class: Union[Type[WerkzeugResponse], DefaultPlaceholder] = Default(JSONResponse),
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
		response_class: Union[Type[WerkzeugResponse], DefaultPlaceholder] = Default(JSONResponse),
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
		response_class: Union[Type[WerkzeugResponse], DefaultPlaceholder] = Default(JSONResponse),
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
		response_class: Union[Type[WerkzeugResponse], DefaultPlaceholder] = Default(JSONResponse),
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
		response_class: Union[Type[WerkzeugResponse], DefaultPlaceholder] = Default(JSONResponse),
	):
		pass
