# Roadmap

## Frappe Versions

- [ ] Frappe V14 support
- [ ] Frappe V15 support

## Methods

- [x] Implement `app.get(...)` method
- [ ] Implement `app.post(...)` method
- [ ] Implement `app.put(...)` method
- [ ] Implement `app.patch(...)` method
- [ ] Implement `app.delete(...)` method

## Query Parameter Features

- [x] Automatic query parameter parsing/conversion based on type hints
- [x] Required query parameters `needy: str`
- [x] Optional query parameters with default values `skip: int = 0`
- [x] Optional query parameters without default values `limit: Union[int, None] = None`
- [ ] Automatic Documentation generation for query parameters
- [x] Enum support for query parameters [path parameters - predefined values](https://fastapi.tiangolo.com/tutorial/path-params/#predefined-values)
- [ ] Additional information and validation for query parameters
  
  - [x] String validations `min_length`, `max_length`, `regex pattern`
  - [x] Numeric validations `gt`, `ge`, `lt`, `le`
  - [x] Metadata `title`, `description`, `deprecated`
  - [x] Additional Validation and information with `Annotated`
  - [x] Ellipsis as required `q: Annotated[str, Query(...)]`

- [ ] App-Level (global) dependencies, that will be available to all endpoints
- [ ] Endpoint-Level dependencies
- [ ] to be continued...

## Improve Frappe API System - Contribution

- [ ] Add support for standard URI format i.e use `/` not `.` for endpoint paths
- [ ] Add support for path parameters i.e `/api/method/greet/{name}`

## Related Frappe PRs and Issues

- [PR #23135](https://github.com/frappe/frappe/pull/23135): Introducing type hints for API functions
- [PR #22300](https://github.com/frappe/frappe/pull/22300): Enhancing `frappe.whitelist()` functionality
- [PR #19029](https://github.com/frappe/frappe/pull/19029): Efforts to improve type safety in Frappe
- [Issue #14905](https://github.com/frappe/frappe/issues/14905): Discussion on improving API documentation

## To be determined

- [ ] `tags: list[str]` parsed as Query or Body? [see the hint here](https://fastapi.tiangolo.com/tutorial/query-params-str-validations/?h=annotated#query-parameter-list-multiple-values)
