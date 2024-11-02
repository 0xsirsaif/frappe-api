import dataclasses
import inspect
import json
from collections import defaultdict
from contextlib import ExitStack
from enum import Enum, IntEnum
from typing import (
	Any,
	Callable,
	Dict,
	List,
	Optional,
	Sequence,
	Set,
	Tuple,
	Type,
	Union,
)

from typing_extensions import Literal

try:
	from multipart.multipart import parse_options_header
except ModuleNotFoundError:  # pragma: nocover
	parse_options_header = None

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
	BaseConfig,
	ModelField,
	Undefined,
	UndefinedType,
	Validator,
	_get_model_config,
	_model_dump,
	get_cached_model_fields,
	get_missing_field_error,
	is_bytes_field,
	is_bytes_sequence_field,
	sequence_types,
	serialize_sequence_value,
	value_is_sequence,
)
from fastapi.datastructures import Default, DefaultPlaceholder, FormData, Headers, QueryParams, UploadFile
from fastapi.dependencies.models import Dependant
from fastapi.dependencies.utils import (
	SolvedDependency,
	_get_multidict_value,
	_should_embed_body_fields,
	_validate_value_with_model_field,
	get_body_field,
	get_dependant,
	get_flat_dependant,
	get_parameterless_sub_dependant,
	get_typed_return_annotation,
	request_params_to_args,
)
from fastapi.encoders import jsonable_encoder
from fastapi.openapi.utils import get_openapi
from fastapi.routing import APIRoute as FastAPIRoute, BaseRoute as FastAPIBaseRoute
from fastapi.types import IncEx
from fastapi.utils import generate_unique_id, get_value_or_default, is_body_allowed_for_status_code
from pydantic import BaseModel, PydanticSchemaGenerationError
from pydantic._internal._utils import lenient_issubclass
from pydantic.fields import FieldInfo
from werkzeug.wrappers import (
	Request as WerkzeugRequest,
	Response as WerkzeugResponse,
)

from frappeapi.exception_handler import (
	http_exception_handler,
	request_validation_exception_handler,
	response_validation_exception_handler,
)
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


def _extract_form_body(
	body_fields: List[ModelField],
	received_body: FormData,
) -> Dict[str, Any]:
	values = {}
	first_field = body_fields[0]
	first_field_info = first_field.field_info

	for field in body_fields:
		value = _get_multidict_value(field, received_body)

		if isinstance(first_field_info, params.File) and is_bytes_field(field) and isinstance(value, UploadFile):
			# Synchronously read the file content using the underlying file object
			value = value.file.read()
		elif is_bytes_sequence_field(field) and isinstance(first_field_info, params.File) and value_is_sequence(value):
			# For sequence types, read each file sequentially
			assert isinstance(value, sequence_types)  # type: ignore[arg-type]
			results: List[Union[bytes, str]] = []

			for sub_value in value:
				# Synchronously read each file and append the content
				file_content = sub_value.file.read()
				results.append(file_content)

			value = serialize_sequence_value(field=field, value=results)
		if value is not None:
			values[field.alias] = value

	for key, value in received_body.items():
		if key not in values:
			values[key] = value

	return values


def request_body_to_args(
	body_fields: List[ModelField],
	received_body: Optional[Union[Dict[str, Any], FormData]],
	embed_body_fields: bool,
) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
	values: Dict[str, Any] = {}
	errors: List[Dict[str, Any]] = []

	assert body_fields, "request_body_to_args() should be called with fields"

	single_not_embedded_field = len(body_fields) == 1 and not embed_body_fields
	first_field = body_fields[0]
	body_to_process = received_body
	fields_to_extract: List[ModelField] = body_fields
	if single_not_embedded_field and lenient_issubclass(first_field.type_, BaseModel):
		fields_to_extract = get_cached_model_fields(first_field.type_)
	if isinstance(received_body, FormData):
		body_to_process = _extract_form_body(fields_to_extract, received_body)
	if single_not_embedded_field:
		loc: Tuple[str, ...] = ("body",)
		v_, errors_ = _validate_value_with_model_field(field=first_field, value=body_to_process, values=values, loc=loc)
		return {first_field.name: v_}, errors_

	for field in body_fields:
		loc = ("body", field.alias)
		value: Optional[Any] = None
		if body_to_process is not None:
			try:
				value = body_to_process.get(field.alias)
			# If the received body is a list, not a dict
			except AttributeError:
				errors.append(get_missing_field_error(loc))
				continue
		v_, errors_ = _validate_value_with_model_field(field=field, value=value, values=values, loc=loc)
		if errors_:
			errors.extend(errors_)
		else:
			values[field.name] = v_
	return values, errors


def parse_and_validate_request(
	*,
	request: WerkzeugRequest,
	dependant: Dependant,
	body: Optional[Union[Dict[str, Any], FormData]] = None,
	# TODO: Validate this type
	background_tasks: Optional[Any] = None,
	response: Optional[WerkzeugResponse] = None,
	dependency_overrides_provider: Optional[Any] = None,
	dependency_cache: Optional[Dict[Tuple[Callable[..., Any], Tuple[str]], Any]] = None,
	exit_stack: ExitStack,
	embed_body_fields: bool,
):
	values: Dict[str, Any] = {}
	errors: List[Any] = []
	if response is None:
		response = WerkzeugResponse()
		if "content-length" in response.headers:
			del response.headers["content-length"]

		response.status = 200

	# TODO: Request Query Params
	request_query_params = QueryParams(request.query_string)
	# TODO: Headers
	# Starlette Headers is an immutable, case-insensitive, and a multidict data structure
	# it allows the same header key to have a multiple values (i.e comma-separated)
	# But, Until now, Frappe or somthing in between
	# choose a single Value (e.g., the last occurrence) to represent the header.
	headers_dict = defaultdict(list)
	for key, value in request.headers.items():
		headers_dict[key].append(value)

	combined_headers = {key: ", ".join(values) for key, values in headers_dict.items()}
	request_headers = Headers(combined_headers)

	# TODO: Cookies

	# TODO: Body
	if dependant.body_params:
		(
			body_values,
			body_errors,
		) = request_body_to_args(  # body_params checked above
			body_fields=dependant.body_params,
			received_body=body,
			embed_body_fields=embed_body_fields,
		)
		values.update(body_values)
		errors.extend(body_errors)

	query_values, query_errors = request_params_to_args(dependant.query_params, request_query_params)
	header_values, header_errors = request_params_to_args(dependant.header_params, request_headers)

	values.update(query_values)
	values.update(header_values)
	errors += query_errors + header_errors

	return SolvedDependency(values=values, errors=errors, background_tasks=None, response=response, dependency_cache={})


class APIRoute(FastAPIRoute):
	def __init__(
		self,
		endpoint: Callable,
		*,
		response_model: Any = Default(None),
		status_code: Optional[int] = None,
		tags: Optional[List[Union[str, Enum]]] = None,
		dependencies: Optional[Sequence[params.Depends]] = None,
		summary: Optional[str] = None,
		description: Optional[str] = None,
		response_description: str = "Successful Response",
		responses: Optional[Dict[Union[int, str], Dict[str, Any]]] = None,
		deprecated: bool = False,
		name: Optional[str] = None,
		methods: Optional[Union[Set[str], List[str]]] = None,
		operation_id: Optional[str] = None,
		response_model_include: Optional[IncEx] = None,
		response_model_exclude: Optional[IncEx] = None,
		response_model_by_alias: bool = True,
		response_model_exclude_unset: bool = False,
		response_model_exclude_defaults: bool = False,
		response_model_exclude_none: bool = False,
		include_in_schema: bool = True,
		response_class: Union[Type[WerkzeugResponse], DefaultPlaceholder] = Default(JSONResponse),
		dependency_overrides_provider: Optional[Any] = None,
		callbacks: Optional[List[FastAPIBaseRoute]] = None,
		openapi_extra: Optional[Dict[str, Any]] = None,
		generate_unique_id_function: Union[Callable[["APIRoute"], str], DefaultPlaceholder] = Default(
			generate_unique_id
		),
		# Frappe parameters
		exception_handlers: Dict[Type[Exception], Callable[[WerkzeugRequest, Exception], WerkzeugResponse]],
	):
		self.prefix = "/api/method"
		self.endpoint = endpoint
		self.path = self.prefix + "/" + extract_endpoint_relative_path(self.endpoint) + "." + self.endpoint.__name__

		if isinstance(response_model, DefaultPlaceholder):
			return_annotation = get_typed_return_annotation(self.endpoint)
			response_model = None if lenient_issubclass(return_annotation, WerkzeugResponse) else return_annotation

		self.response_model = response_model
		self.summary = summary
		self.response_description = response_description
		self.deprecated = deprecated
		self.operation_id = operation_id
		self.response_model_include = response_model_include
		self.response_model_exclude = response_model_exclude
		self.response_model_by_alias = response_model_by_alias
		self.response_model_exclude_unset = response_model_exclude_unset
		self.response_model_exclude_defaults = response_model_exclude_defaults
		self.response_model_exclude_none = response_model_exclude_none
		self.include_in_schema = include_in_schema
		self.response_class = response_class
		self.dependency_overrides_provider = dependency_overrides_provider
		self.callbacks = callbacks
		self.openapi_extra = openapi_extra
		self.generate_unique_id_function = generate_unique_id_function
		self.tags = tags or []
		self.responses = responses or {}
		self.name = name or getattr(self.endpoint, "__name__", None)
		self.path_regex, self.path_format, self.param_convertors = None, self.path, {}

		if methods is None:
			methods = ["GET"]
		self.methods: Set[str] = {method.upper() for method in methods}
		if isinstance(generate_unique_id_function, DefaultPlaceholder):
			current_generate_unique_id: Callable[[APIRoute], str] = generate_unique_id_function.value
		else:
			current_generate_unique_id = generate_unique_id_function
		self.unique_id = self.operation_id or current_generate_unique_id(self)

		# normalize enums e.g. http.HTTPStatus
		if isinstance(status_code, IntEnum):
			status_code = int(status_code)

		self.status_code = status_code

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

		self.dependencies = list(dependencies or [])
		self.description = description or inspect.cleandoc(self.endpoint.__doc__ or "")
		# if a "form feed" character (page break) is found in the description text,
		# truncate description text to the content preceding the first "form feed"
		self.description = self.description.split("\f")[0].strip()

		response_fields = {}
		for additional_status_code, response in self.responses.items():
			assert isinstance(response, dict), "An additional response must be a dict"
			model = response.get("model")
			if model:
				assert is_body_allowed_for_status_code(
					additional_status_code
				), f"Status code {additional_status_code} must not have a response body"
				response_name = f"Response_{additional_status_code}_{self.unique_id}"
				response_field = create_model_field(name=response_name, type_=model, mode="serialization")
				response_fields[additional_status_code] = response_field

		if response_fields:
			self.response_fields: Dict[Union[int, str], ModelField] = response_fields
		else:
			self.response_fields = {}
		assert callable(endpoint), "endpoint must be a callable"

		self.dependant = get_dependant(
			path=self.path,
			call=self.endpoint,
		)
		for depends in self.dependencies[::-1]:
			self.dependant.dependencies.insert(
				0,
				get_parameterless_sub_dependant(depends=depends, path=self.path_format),
			)

		self._flat_dependant = get_flat_dependant(self.dependant)
		self._embed_body_fields = _should_embed_body_fields(self._flat_dependant.body_params)
		self.body_field = get_body_field(
			flat_dependant=self._flat_dependant,
			name=self.unique_id,
			embed_body_fields=self._embed_body_fields,
		)

		self.exception_handlers = exception_handlers

	def handle_request(self, *args, **kwargs):
		MAX_IN_MEMORY_FILE_SIZE = 1 * 1024 * 1024  # 1MB
		request = frappe.request
		is_body_form = self.body_field and isinstance(self.body_field.field_info, params.Form)

		with ExitStack() as file_stack:
			try:
				body: Any = None
				if self.body_field:
					if is_body_form:
						# Ensure python-multipart is available
						assert (
							parse_options_header is not None
						), "The `python-multipart` library must be installed to use form parsing."

						# Convert werkzeug headers to starlette headers
						headers_dict = defaultdict(list)
						for key, value in request.headers.items():
							headers_dict[key].append(value)

						combined_headers = {key: ", ".join(values) for key, values in headers_dict.items()}
						request_headers = Headers(combined_headers)

						# items of FormData
						_items: list[tuple[str, str | UploadFile]] = []

						# Add form fields
						if request.form:
							for key, value in request.form.items():
								_items.append((key, value))

						# Add and manage file fields
						if request.files:
							for field_name, fileobj in request.files.items():
								if hasattr(fileobj, "read"):
									content_length = getattr(fileobj, "content_length", None)
									# Check if content_length is set and is greater than 0
									# This is to avoid the case where content_length is not set
									# and the file is being read into memory
									if content_length is not None and content_length > 0:
										if content_length <= MAX_IN_MEMORY_FILE_SIZE:
											# Small file: Read content into memory
											file_content = fileobj.read()
											_items.append((field_name, file_content))
											fileobj.close()  # Explicitly close the file
										else:
											# Large file: Wrap in UploadFile without reading
											upload_file = UploadFile(
												file=fileobj,
												headers=request_headers,
											)
											_items.append((field_name, upload_file))
											if hasattr(fileobj, "close"):
												# Attach close callback to the file object
												file_stack.callback(fileobj.close)
									else:
										# content_length is not set; treat as large file
										upload_file = UploadFile(
											file=fileobj,
											filename=fileobj.filename,
											headers=request_headers,
										)
										_items.append((field_name, upload_file))
										if hasattr(fileobj, "close"):
											file_stack.callback(fileobj.close)
								else:
									# Handle cases where 'read' is not available
									raise HTTPException(
										status_code=400,
										detail=f"Cannot process the uploaded file for field '{field_name}'.",
									)
						body = FormData(_items)
					else:
						# Handle JSON or other non-form bodies
						body_bytes = request.get_data()
						if body_bytes:
							json_body: Any = Undefined
							content_type_value = request.headers.get("content-type", "")
							if not content_type_value:
								json_body = request.get_json(silent=True)
							else:
								import email.message

								message = email.message.Message()
								message["content-type"] = content_type_value
								if message.get_content_maintype() == "application":
									subtype = message.get_content_subtype()
									if subtype == "json" or subtype.endswith("+json"):
										json_body = request.get_json(silent=True)
							body = json_body if json_body != Undefined else body_bytes
			except json.JSONDecodeError as e:
				validation_error = RequestValidationError(
					[
						{
							"type": "json_invalid",
							"loc": ("body", e.pos),
							"msg": "JSON decode error",
							"input": {},
							"ctx": {"error": e.msg},
						}
					],
					body=e.doc,
				)
				raise validation_error from e
			except HTTPException:
				# If a middleware raises an HTTPException, it should be raised again
				raise
			except Exception as e:
				http_error = HTTPException(status=400, detail="There was an error parsing the body")
				raise http_error from e

			errors: List[Any] = []
			with ExitStack() as exit_stack:
				try:
					solved_result = parse_and_validate_request(
						request=request,
						dependant=self.dependant,
						body=body,
						exit_stack=exit_stack,
						embed_body_fields=self._embed_body_fields,
					)
					errors = solved_result.errors
					if not errors:
						request_data = solved_result.values
						raw_response = self.endpoint(**request_data)

						if isinstance(raw_response, WerkzeugResponse):
							# if raw_response.background is None:
							# 	raw_response.background = solved_result.background_tasks
							response = raw_response
						else:
							# response_args: Dict[str, Any] = {"background": solved_result.background_tasks}
							response_args: Dict[str, Any] = {}
							# If status_code was set, use it, otherwise use the default from the
							# # response class, in the case of redirect it's 307
							current_status_code = (
								self.status_code if self.status_code else solved_result.response.status_code
							)
							if current_status_code is not None:
								response_args["status_code"] = current_status_code
							if solved_result.response.status_code:
								response_args["status_code"] = solved_result.response.status_code

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
					if errors:
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
						return response_validation_exception_handler(request, exc)
				except Exception as exc:
					for exc_type, handler in self.exception_handlers.items():
						if isinstance(exc, exc_type):
							return handler(request, exc)
					raise exc

		if response is None:
			raise FrappeAPIError("No response object was returned.")

		return response

	def __repr__(self) -> str:
		class_name = self.__class__.__name__
		methods = sorted(self.methods or [])
		path, name = self.path, self.name
		return f"{class_name}(path={path!r}, name={name!r}, methods={methods!r})"


class APIRouter:
	def __init__(
		self,
		*,
		title: str,
		version: str,
		openapi_version: str = "3.1.0",
		summary: Optional[str] = None,
		description: Optional[str] = None,
		separate_input_output_schemas: bool = True,
		openapi_tags: Optional[List[Dict[str, Any]]] = None,
		terms_of_service: Optional[str] = None,
		contact: Optional[Dict[str, Union[str, Any]]] = None,
		license_info: Optional[Dict[str, Union[str, Any]]] = None,
		webhooks: Optional[List[Any]] = None,
		servers: Optional[List[Dict[str, Union[str, Any]]]] = None,
		default_response_class: Type[WerkzeugResponse] = Default(WerkzeugResponse),
		exception_handlers: Dict[Type[Exception], Callable[[WerkzeugRequest, Exception], WerkzeugResponse]] = None,
	):
		self.default_response_class = default_response_class
		self.routes: List[APIRoute] = []
		self.exception_handlers = exception_handlers
		self.title = title
		self.version = version
		self.openapi_version = openapi_version
		self.summary = summary
		self.description = description
		self.separate_input_output_schemas = separate_input_output_schemas
		self.openapi_tags = openapi_tags
		self.terms_of_service = terms_of_service
		self.contact = contact
		self.license_info = license_info
		self.webhooks = webhooks
		self.servers = servers
		self.openapi_schema: Optional[Dict[str, Any]] = None

	def openapi(self) -> Dict[str, Any]:
		if self.openapi_schema is None:
			self.openapi_schema = get_openapi(
				title=self.title,
				version=self.version,
				openapi_version=self.openapi_version,
				summary=self.summary,
				description=self.description,
				routes=self.routes,
				webhooks=self.webhooks,
				tags=self.openapi_tags,
				servers=self.servers,
				terms_of_service=self.terms_of_service,
				contact=self.contact,
				license_info=self.license_info,
				separate_input_output_schemas=self.separate_input_output_schemas,
			)

		return self.openapi_schema

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
		# Frappe parameters
		allow_guest: bool = False,
		xss_safe: bool = False,
	):
		def decorator(func: Callable):
			# Register the route

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

			# When the route is called, it will be handled by the route's handle_request method
			@whitelist(methods=methods, allow_guest=allow_guest, xss_safe=xss_safe)
			def wrapper(*args, **kwargs):
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
		# Frappe parameters
		allow_guest: bool = False,
		xss_safe: bool = False,
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
			allow_guest=allow_guest,
			xss_safe=xss_safe,
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
		# Frappe parameters
		allow_guest: bool = False,
		xss_safe: bool = False,
	):
		return self.api_route(
			methods=["POST"],
			response_model=response_model,
			status_code=status_code,
			description=description,
			tags=tags,
			summary=summary,
			include_in_schema=include_in_schema,
			response_class=response_class,
			allow_guest=allow_guest,
			xss_safe=xss_safe,
		)

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
		# Frappe parameters
		allow_guest: bool = False,
		xss_safe: bool = False,
	):
		return self.api_route(
			methods=["PUT"],
			response_model=response_model,
			status_code=status_code,
			description=description,
			tags=tags,
			summary=summary,
			include_in_schema=include_in_schema,
			response_class=response_class,
			allow_guest=allow_guest,
			xss_safe=xss_safe,
		)

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
		# Frappe parameters
		allow_guest: bool = False,
		xss_safe: bool = False,
	):
		return self.api_route(
			methods=["DELETE"],
			response_model=response_model,
			status_code=status_code,
			description=description,
			tags=tags,
			summary=summary,
			include_in_schema=include_in_schema,
			response_class=response_class,
			allow_guest=allow_guest,
			xss_safe=xss_safe,
		)

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
		# Frappe parameters
		allow_guest: bool = False,
		xss_safe: bool = False,
	):
		return self.api_route(
			methods=["PATCH"],
			response_model=response_model,
			status_code=status_code,
			description=description,
			tags=tags,
			summary=summary,
			include_in_schema=include_in_schema,
			response_class=response_class,
			allow_guest=allow_guest,
			xss_safe=xss_safe,
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
		response_class: Union[Type[WerkzeugResponse], DefaultPlaceholder] = Default(JSONResponse),
		# Frappe parameters
		allow_guest: bool = False,
		xss_safe: bool = False,
	):
		return self.api_route(
			methods=["OPTIONS"],
			response_model=response_model,
			status_code=status_code,
			description=description,
			tags=tags,
			summary=summary,
			include_in_schema=include_in_schema,
			response_class=response_class,
			allow_guest=allow_guest,
			xss_safe=xss_safe,
		)

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
		# Frappe parameters
		allow_guest: bool = False,
		xss_safe: bool = False,
	):
		return self.api_route(
			methods=["HEAD"],
			response_model=response_model,
			status_code=status_code,
			description=description,
			tags=tags,
			summary=summary,
			include_in_schema=include_in_schema,
			response_class=response_class,
			allow_guest=allow_guest,
			xss_safe=xss_safe,
		)
