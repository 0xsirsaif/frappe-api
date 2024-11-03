# FrappeAPI

Better APIs for Frappe!

⚠️ **Alert: Beta Version**
This project is currently in beta. Expect changes and improvements as we work towards a stable release.

## Why?

The goal is to build a better API framework for Frappe.

## Roadmap

### Frappe Versions

- [x] Frappe V14 support
- [ ] Frappe V15 support

### Methods

- [x] Implement `app.get(...)` method.
- [x] Implement `app.post(...)` method.
- [x] Implement `app.put(...)` method.
- [x] Implement `app.patch(...)` method
- [x] Implement `app.delete(...)` method

### Query Parameter Features

- [x] Automatic query parameter parsing/conversion based on type hints.
- [x] Required query parameters `needy: str`.
- [x] Required query parameters with Ellipsis `...`. See [Pydantic Required Fields](https://docs.pydantic.dev/latest/concepts/models/#required-fields) and [FastAPI Required with Ellipsis](https://fastapi.tiangolo.com/tutorial/query-params-str-validations/#required-with-ellipsis).
- [x] Optional query parameters with default values `skip: int = 0`.
- [x] Optional query parameters without default values `limit: Union[int, None] = None`.
- [x] Enum support for query parameters [path parameters - predefined values](https://fastapi.tiangolo.com/tutorial/path-params/#predefined-values).
- [x] Boolean query parameters `is_admin: bool = False`. see [Pydantic's Boolean type](https://docs.pydantic.dev/2.0/usage/types/booleans/).
- [x] List query parameters (i.e. a query parameter q that can appear multiple times in the URL, e.g. `?q=foo&q=bar`)
- [x] Aliases for query parameters. `q: str = Query(alias="query")`
- [x] Query parameters as Pydantic model. `filters: Filter`. See [Query Parameter Models](https://fastapi.tiangolo.com/tutorial/query-param-models/#query-parameter-models)
- [x] Automatic Documentation generation for query parameters.

### Body Parameter Features

- [x] Body parameter as Pydantic model. `item: Item`
- [x] Multiple body parameters. `item: Item, user: User`, resulting in `{"item": {"name": "foo"}, "user": {"name": "bar"}}`
- [x] Singular values in body, defined as `Body()`. `name: str = Body()` so that to not conflict with query parameters.
- [x] Special `embed` Body parameter. See [Embed a single body parameter](https://fastapi.tiangolo.com/tutorial/body-multiple-params/#embed-a-single-body-parameter)
- [x] Nested Models for body parameters.
- [x] Automatic body parameter parsing/conversion based on type hints.

### Header Parameters

- [x] Support header parameters like FastAPI did. See [Header Parameters](https://fastapi.tiangolo.com/tutorial/header-params/)
- [ ] Header parameters as Pydantic model. See [Header Parameter Models](https://fastapi.tiangolo.com/tutorial/header-param-models/)
- [ ] Duplicate header parameters.
- [ ] Ability to forbid extra headers. `model_config={"extra": "forbid"}`

### Cookie Parameters

- [ ] Support cookie parameters like FastAPI did.

### Form Data

- [x] Define form field as `Form()`. `name: str = Form()`.
- [x] Multiple form fields. `name: str = Form(), age: int = Form()`
- [x] Form data as Pydantic model. `data: Data`
- [ ] Ability to forbid extra form fields. `model_config={"extra": "forbid"}`

### File Uploads

- [x] Define file upload field as `File()`. `file: Annotated[bytes, File()]`, FrappeAPI will read the file for you and you will receive the contents as bytes with file-like interface. This means that the whole contents will be stored in memory. This will work well for small files.
- [x] `UploadFile` for large files. `file: UploadFile`. Uses `tempfile.SpooledTemporaryFile` to store the file contents in memory or disk depending on the size. You get a file-like interface with the file contents streamed from the client to the server. `UploadFile` is FastAPI's, it supports async file handling, but FrappeAPI does not yet support async APIs, fortunately, `UploadFile` has `file` attribute to access the raw standard Python file (blocking, not async), useful and needed for non-async code.
- [ ] Optional file upload field. `file: Annotated[bytes | None, File()] = None`
- [ ] Optional `UploadFile` field. `file: UploadFile | None = None`
- [ ] Multiple file upload fields. `files: Annotated[list[bytes], File()]`
- [ ] Multiple `UploadFile` fields. `files: list[UploadFile]`

### Handling Errors

- [x] HTTPException
- [x] RequestValidationError
- [x] ResponseValidationError
- [x] Register custom exception handlers. See [Add custom headers](https://fastapi.tiangolo.com/tutorial/handling-errors/#add-custom-headers)
- [x] Override default exception handlers.

### Response Models

- [x] Method `response_model` parameter to define response model as Pydantic model. `response_model=Model`, `response_model=list[Model]` ...etc
- [x] Response model as return type with standard type hints or Pydantic model. `-> Model`, `-> list[Model]`...etc
- [x] Limit and filter the output data to what is defined in the return type.
- [x] `response_model` parameter takes precedence over return type if both are provided.

### Additional information and validation fields

- [x] String validations, `min_length`, `max_length`, `pattern`.
- [x] Numeric validations, `gt`, `ge`, `lt`, `le`.
- [x] Metadata, `title`, `description`, `deprecated`.
- [x] others, `include_in_schema`.

## Related Frappe PRs and Issues

- [PR #23135](https://github.com/frappe/frappe/pull/23135): Introducing type hints for API functions.
- [PR #22300](https://github.com/frappe/frappe/pull/22300): Enhancing `frappe.whitelist()` functionality.
- [PR #19029](https://github.com/frappe/frappe/pull/19029): Efforts to improve type safety in Frappe.
- [Issue #14905](https://github.com/frappe/frappe/issues/14905): Discussion on improving API documentation.
