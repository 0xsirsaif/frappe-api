"""
FastAPI-style path routing for **FrappeAPI**
==============================================

Purpose
----------
- Enable decorators like `@app.get("/items/{code}")` next to the existing
  dotted-path system.
- Use routes registered in the FrappeAPI app instance without duplication.
- Leave every Frappe lifecycle guarantee intact (DB, auth, error handling).

How it works
--------------
1. Each FrappeAPI instance registers routes in its self.router.routes collection.
2. At import time we monkey-patch **`frappe.api.handle`**:
   - For every `/api/**` request we check against the registered routes.
   - On a match, we extract path parameters and call the corresponding handler.
   - If nothing matches we fall back to the original `frappe.api.handle`.
"""

from __future__ import annotations

import logging
import types
from enum import Enum
from typing import TYPE_CHECKING, Any, Callable, List, Optional, Type, Union

if TYPE_CHECKING:
	from unittest.mock import Mock

	frappe = Mock()
else:
	import frappe

from fastapi.datastructures import Default
from starlette.routing import Match, Route
from werkzeug.wrappers import Response as WerkzeugResponse

from frappeapi.responses import JSONResponse

logger = logging.getLogger(__name__)

__all__ = [
	"GET",
	"POST",
	"PUT",
	"DELETE",
	"PATCH",
	"OPTIONS",
	"HEAD",
	"register_app",
]

_FRAPPEAPI_INSTANCES = []


def register_app(app):
	"""Register a FrappeAPI instance to be considered for routing."""
	if app not in _FRAPPEAPI_INSTANCES:
		_FRAPPEAPI_INSTANCES.append(app)


def _factory(methods: List[str]) -> Callable:
	def decorator(
		path: str,
		*,
		response_model: Any = Default(None),
		status_code: Optional[int] = None,
		description: Optional[str] = None,
		tags: Optional[List[Union[str, Enum]]] = None,
		summary: Optional[str] = None,
		include_in_schema: bool = True,
		response_class: Type[WerkzeugResponse] = Default(JSONResponse),
		allow_guest: bool = False,
		xss_safe: bool = False,
		fastapi_path_format: bool = False,
	) -> Callable[[Callable], Callable]:
		def register(func: Callable) -> Callable:
			# This is just a pass-through - the actual registration happens in applications.py via the FrappeAPI._dual method
			return func

		return register

	return decorator


GET = _factory(["GET"])
POST = _factory(["POST"])
PUT = _factory(["PUT"])
DELETE = _factory(["DELETE"])
PATCH = _factory(["PATCH"])
OPTIONS = _factory(["OPTIONS"])
HEAD = _factory(["HEAD"])


def _get_frappe_version() -> int:
	"""
	Detect Frappe major version.

	Returns:
		int: Major version number (14, 15, 16, etc.)
	"""
	try:
		if hasattr(frappe, "__version__"):
			version_string = frappe.__version__
			if version_string:
				# Parse version like "14.23.0" or "15.5.1"
				major_version = int(version_string.split(".")[0])
				logger.info(f"Detected Frappe version: {version_string} (major: {major_version})")
				return major_version
	except (ValueError, AttributeError, IndexError) as e:
		logger.warning(f"Failed to parse Frappe version: {e}")

	# Fallback: Try to detect by module structure
	try:
		# v15+ uses frappe.api as a module (has __init__.py)
		# v14 uses frappe.api as a single file
		if hasattr(frappe, "api") and hasattr(frappe.api, "API_URL_MAP"):
			# v15+ has API_URL_MAP for Werkzeug routing
			logger.info("Detected Frappe v15+ (has API_URL_MAP)")
			return 15
	except (ImportError, AttributeError):
		pass

	# Default to v14 if unable to detect
	logger.warning("Unable to detect Frappe version, defaulting to v14 compatibility mode")
	return 14


def _create_v14_patch(orig_handle: Callable) -> Callable:
	"""
	Create a patch compatible with Frappe v14.

	Args:
		orig_handle: Original frappe.api.handle function (no parameters)

	Returns:
		Patched handle function (no parameters)
	"""

	def patched_handle(request=None) -> types.ModuleType | dict:
		request_path = frappe.local.request.path

		for app_instance in _FRAPPEAPI_INSTANCES:
			if not app_instance.fastapi_path_format:
				continue

			if not (
				request_path.startswith("/api/")
				and not request_path.startswith("/api/method/")
				and not request_path.startswith("/api/resource/")
			):
				continue

			path_segment_to_match = request_path[4:]

			if not hasattr(app_instance, "router") or not hasattr(app_instance.router, "routes"):
				continue

			for api_route in app_instance.router.routes:
				# api_route.fastapi_path_format_flag is the mode of the APIRoute instance itself.
				# api_route.path_for_starlette_matching is the relative path like "/items/{item_id}".
				if not (api_route.fastapi_path_format_flag and api_route.path_for_starlette_matching):
					continue

				scope = {
					"type": "http",
					"path": path_segment_to_match,
					"root_path": "",
					"method": frappe.local.request.method.upper(),
				}

				# Create a temporary Starlette route for matching.
				starlette_route = Route(
					api_route.path_for_starlette_matching,
					endpoint=api_route.endpoint,
					methods=[m for m in api_route.methods] if api_route.methods else None,
				)

				match, child_scope = starlette_route.matches(scope)
				if match == Match.FULL:
					path_params = child_scope.get("path_params", {})
					frappe.local.request.path_params = path_params
					response = api_route.handle_request()
					return response

		# No FastAPI-style route matched for any app instance in FastAPI mode,
		# or the path was not a FastAPI-style candidate.
		# Fall back to the original Frappe handler for dotted paths or other unhandled /api/ calls.
		if request:
			return orig_handle(request)
		return orig_handle()

	return patched_handle


def _create_v15_plus_patch(orig_handle: Callable) -> Callable:
	"""
	Create a patch compatible with Frappe v15+.

	Args:
		orig_handle: Original frappe.api.handle function (takes request parameter)

	Returns:
		Patched handle function (takes request parameter)
	"""

	def patched_handle(request) -> types.ModuleType | dict:
		# In v15+, request is passed as a parameter
		request_path = request.path

		for app_instance in _FRAPPEAPI_INSTANCES:
			if not app_instance.fastapi_path_format:
				continue

			# Skip Frappe's native API versioning routes (v15+ feature)
			if request_path.startswith(("/api/v1/", "/api/v2/")):
				continue

			if not (
				request_path.startswith("/api/")
				and not request_path.startswith("/api/method/")
				and not request_path.startswith("/api/resource/")
			):
				continue

			# FrappeAPI uses /api/... (without v1/v2 prefix)
			path_segment_to_match = request_path[4:]  # Remove "/api"

			if not hasattr(app_instance, "router") or not hasattr(app_instance.router, "routes"):
				continue

			for api_route in app_instance.router.routes:
				# api_route.fastapi_path_format_flag is the mode of the APIRoute instance itself.
				# api_route.path_for_starlette_matching is the relative path like "/items/{item_id}".
				if not (api_route.fastapi_path_format_flag and api_route.path_for_starlette_matching):
					continue

				scope = {
					"type": "http",
					"path": path_segment_to_match,
					"root_path": "",
					"method": request.method.upper(),
				}

				# Create a temporary Starlette route for matching.
				starlette_route = Route(
					api_route.path_for_starlette_matching,
					endpoint=api_route.endpoint,
					methods=[m for m in api_route.methods] if api_route.methods else None,
				)

				match, child_scope = starlette_route.matches(scope)
				if match == Match.FULL:
					path_params = child_scope.get("path_params", {})
					# Store path params in both places for compatibility
					frappe.local.request.path_params = path_params
					# Also store on request object if it supports it (v15+)
					if hasattr(request, "__dict__"):
						request.path_params = path_params
					response = api_route.handle_request()
					return response

		# No FastAPI-style route matched for any app instance in FastAPI mode,
		# or the path was not a FastAPI-style candidate.
		# Fall back to the original Frappe handler with request parameter
		return orig_handle(request)

	return patched_handle


def _install_patch() -> None:
	"""
	Install version-appropriate patch to frappe.api.handle.

	Automatically detects Frappe version and applies compatible patch:
	- v14: Patch with no parameters
	- v15+: Patch with request parameter

	The patch is installed once per process and skipped during migrations.
	"""
	# Skip patching during migrations
	if hasattr(frappe, "flags") and getattr(frappe.flags, "in_migrate", False):
		logger.info("Skipping FrappeAPI patch installation during migration")
		return

	# Skip if already patched
	if getattr(frappe, "_fastapi_path_patch_done", False):
		logger.debug("FrappeAPI patch already installed")
		return

	# Skip if frappe.api is not available
	if not hasattr(frappe, "api"):
		logger.warning("frappe.api module not found, skipping FrappeAPI patch installation")
		return

	try:
		# Detect Frappe version
		frappe_version = _get_frappe_version()

		# Get original handle function
		orig_handle = frappe.api.handle

		# Create version-appropriate patch
		if frappe_version >= 15:
			logger.info(f"Installing FrappeAPI patch for Frappe v{frappe_version}+ (with request parameter)")
			patched_handle = _create_v15_plus_patch(orig_handle)
		else:
			logger.info(f"Installing FrappeAPI patch for Frappe v{frappe_version} (without request parameter)")
			patched_handle = _create_v14_patch(orig_handle)

		# Apply the patch
		frappe.api.handle = patched_handle
		frappe._fastapi_path_patch_done = True
		frappe._frappeapi_detected_version = frappe_version

		logger.info("FrappeAPI patch installed successfully")

	except Exception as e:
		logger.error(f"Failed to install FrappeAPI patch: {e}", exc_info=True)
		# Don't raise - fail gracefully and allow Frappe to continue
		# FrappeAPI routes just won't work, but dotted paths will still function


_install_patch()
