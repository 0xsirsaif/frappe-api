__version__ = "0.1.0"

from fastapi.datastructures import UploadFile  # noqa: F401
from fastapi.params import (
	Body,  # noqa: F401
	Depends,  # noqa: F401
	File,  # noqa: F401
	Form,  # noqa: F401
	Header,  # noqa: F401
	Query,  # noqa: F401
)

from frappeapi.applications import FrappeAPI  # noqa: F401
