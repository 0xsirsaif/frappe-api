import inspect
import json
import os
import typing
from inspect import Parameter, signature
from typing import Any

from pydantic import ValidationError, create_model
from werkzeug.wrappers import Response


class DefaultPlaceholder:
	def __init__(self, value: Any):
		self.value = value

	def __eq__(self, o: object) -> bool:
		return isinstance(o, DefaultPlaceholder) and self.value == o.value

	def __hash__(self) -> int:
		return hash(self.value)


def Default(value: Any):  # noqa: N802
	return DefaultPlaceholder(value)


def extract_endpoint_relative_path(func):
	full_path = inspect.getfile(func)
	path_parts = full_path.split(os.sep)
	try:
		apps_index = path_parts.index("apps") + 2
		sub_path_parts = path_parts[apps_index:]
		file_name = sub_path_parts[-1]
		sub_path_parts[-1] = os.path.splitext(file_name)[0]
		return ".".join(sub_path_parts)
	except ValueError:
		return None


def create_openapi_param_dict(func) -> list[dict]:
	sig = inspect.signature(func)
	type_hints = typing.get_type_hints(func)
	openapi_params = []
	for name, param in sig.parameters.items():
		param_type = type_hints.get(name, str)  # Default to string if type hint missing
		openapi_type = map_type_to_openapi(param_type)
		param_dict = {
			"name": name,
			"in": "query",
			"required": param.default is inspect.Parameter.empty,  # Required if default is not set
			"schema": {"type": openapi_type},
		}
		openapi_params.append(param_dict)

	return openapi_params


def map_type_to_openapi(py_type) -> str:
	mapping = {int: "integer", float: "number", str: "string", bool: "boolean"}
	return mapping.get(py_type, "string")


def create_validator_model(func):
	"""
	Create a Pydantic model dynamically based on function's annotations and defaults.
	"""
	annotations = typing.get_type_hints(func)
	fields = {
		name: (annotations[name], param.default if param.default is not Parameter.empty else ...)
		for name, param in signature(func).parameters.items()
		if name != "return"
	}

	return create_model(f"{func.__name__}_ValidationModel", **fields)


def format_validation_error(error: ValidationError, loc: str = "query") -> Response:
	"""
	Format the Pydantic ValidationError to match FastAPI error response style.
	"""
	details = []
	for err in error.errors():
		details.append(
			{
				"type": err["type"],
				"loc": [loc] + list(err["loc"]),
				"msg": err["msg"],
				"input": err.get("ctx", {}).get("input"),
			}
		)
	error_response = {"detail": details}

	response_body = json.dumps(error_response)

	return Response(response_body, status=422, mimetype="application/json")
