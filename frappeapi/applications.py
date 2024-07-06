import inspect
import json
from typing import Any, Dict, List, Optional, Union

import frappe
from frappe import whitelist
from openapi_pydantic_v2 import Info, OpenAPI, Operation, PathItem, Response, Server
from pydantic import BaseModel, ValidationError
from typing_extensions import Annotated, Doc
from werkzeug.wrappers import Response as WerkzeugResponse

from frappeapi.datastructures import QueryParams
from frappeapi.utils import (
	create_openapi_param_dict,
	create_validator_model,
	extract_relative_path,
	format_validation_error,
)


class FrappeAPI:
	def __init__(
		self,
		title: Annotated[
			str,
			Doc(
				"""
                    The title of the API.
                    It will be added to the generated OpenAPI (e.g., visible at `/docs`).
                    """
			),
		] = "FrappeAPI",
		summary: Annotated[
			Optional[str],
			Doc(
				"""
                    A short summary of the API.
                    It will be added to the generated OpenAPI (e.g., visible at `/docs`).
                    """
			),
		] = None,
		description: Annotated[
			str,
			Doc(
				"""
                    A description of the API. Supports Markdown (using [CommonMark syntax](https://commonmark.org/)).
                    It will be added to the generated OpenAPI (e.g., visible at `/docs`).
                    """
			),
		] = "",
		version: Annotated[
			str,
			Doc(
				"""
                    The version of the API.
                    Note: This is the version of your application, not the OpenAPI specification nor FastAPI.
                    It will be added to the generated OpenAPI (e.g., visible at `/docs`).
                    """
			),
		] = "0.1.0",
		servers: Annotated[
			Optional[List[Dict[str, Union[str, Any]]]],
			Doc(
				"""
                A `list` of `dict`s with connectivity information to a target server.

                You would use it, for example, if your application is served from
                different domains and you want to use the same Swagger UI in the
                browser to interact with each of them (instead of having multiple
                browser tabs open). Or if you want to leave fixed the possible URLs.

                If the servers `list` is not provided, or is an empty `list`, the
                default value would be a `dict` with a `url` value of `/`.

                Each item in the `list` is a `dict` containing:

                * `url`: A URL to the target host. This URL supports Server Variables
                and MAY be relative, to indicate that the host location is relative
                to the location where the OpenAPI document is being served. Variable
                substitutions will be made when a variable is named in `{`brackets`}`.
                * `description`: An optional string describing the host designated by
                the URL. [CommonMark syntax](https://commonmark.org/) MAY be used for
                rich text representation.
                * `variables`: A `dict` between a variable name and its value. The value
                    is used for substitution in the server's URL template.

                ```python
                from frappeapi import FrappeAPI

                app = FrappeAPI(
                    servers=[
                        {"url": "https://stag.example.com", "description": "Staging environment"},
                        {"url": "https://prod.example.com", "description": "Production environment"},
                    ]
                )
                ```
                """
			),
		] = None,
	):
		self.title = title
		self.summary = summary
		self.description = description
		self.version = version
		self.routes: List[Dict[str, Any]] = []
		self.openapi_schema: Optional[Dict[str, Any]] = None
		self.servers = servers or [{"url": "/"}]

	def generate_openapi_schema(self):
		paths = {}
		for item in self.routes:
			paths[item["path"]] = item["item"]

		openapi_model = OpenAPI(
			openapi="3.0.0",
			info=Info(title=self.title, version=self.version, description=self.description),
			paths=paths,
			servers=[Server(**server) for server in self.servers],
		)
		return openapi_model

	def generate_openapi_json(self):
		openapi_schema = self.generate_openapi_schema().dict(by_alias=True, exclude_none=True)
		return json.dumps(openapi_schema, indent=2)

	def openapi(self):
		if not self.openapi_schema:
			self.openapi_schema = self.generate_openapi_schema()

		return self.openapi_schema

	def add_route(
		self,
		path: str,
		method: str,
		response_model: BaseModel,
		parameters: List[Dict[str, Any]] | None = None,
	):
		# Correctly handle adding a new path or appending to an existing one
		path_item = next((item for item in self.routes if item["path"] == path), None)
		if not path_item:
			path_item = {"path": path, "item": PathItem()}
			self.routes.append(path_item)

		# Dynamically set the operation based on the HTTP method
		operation = Operation(
			parameters=parameters,
			responses={
				"200": Response(
					description="Successful response",
					content={"application/json": {"schema": response_model.model_json_schema()}},
				)
			},
		)
		setattr(path_item["item"], method.lower(), operation)

	def get(self, response_model: Any = None):
		def decorator(func):
			path = "/api/method/" + extract_relative_path(inspect.getfile(func)) + "." + func.__name__

			@whitelist(methods=["GET"])
			def wrapper(*args, **kwargs):
				try:
					query_param_validator_model = create_validator_model(func)
					query_params = QueryParams(frappe.request.query_string)
					query_param_validator_model(**query_params.to_dict())
				except ValidationError as e:
					return format_validation_error(e)

				valid_params = inspect.signature(func).parameters
				filtered_args = {k: v for k, v in kwargs.items() if k in valid_params}
				try:
					result = func(*args, **filtered_args)
					if issubclass(response_model, BaseModel):
						response_content = json.dumps(response_model(**result).dict())
						return WerkzeugResponse(response_content, status=200, mimetype="application/json")
					else:
						response_content = json.dumps(result)
						return WerkzeugResponse(response_content, status=200, mimetype="application/json")
				except Exception as exc:
					error_response = {"detail": str(exc)}
					response_body = json.dumps(error_response)
					return WerkzeugResponse(response_body, status=500, mimetype="application/json")

			parameters = create_openapi_param_dict(func)
			self.add_route(path=path, method="GET", response_model=response_model, parameters=parameters)
			return wrapper

		return decorator
