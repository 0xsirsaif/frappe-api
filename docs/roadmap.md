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

- [ ] Automatic query parameter parsing/conversion based on type hints
- [ ] Required query parameters `needy: str`
- [ ] Optional query parameters with default values `skip: int = 0`
- [ ] Optional query parameters without default values `limit: Union[int, None] = None`
- [ ] Automatic Documentation generation for query parameters
- [ ] Enum support for query parameters [path parameters - predefined values](https://fastapi.tiangolo.com/tutorial/path-params/#predefined-values)
- [ ] Additional information and validation for query parameters

  - [ ] String validations
    - [ ] `min_length`
    - [ ] `max_length`
    - [ ] `regex pattern`
  - [ ] Numeric validations
    - [ ] `gt`
    - [ ] `ge`
    - [ ] `lt`
    - [ ] `le`
  - [ ] Metadata
    - [ ] `title`
    - [ ] `description`
    - [ ] `deprecated`

- [ ] to be continued...

## Related Frappe PRs and Issues

- [PR #23135](https://github.com/frappe/frappe/pull/23135): Introducing type hints for API functions
- [PR #22300](https://github.com/frappe/frappe/pull/22300): Enhancing `frappe.whitelist()` functionality
- [PR #19029](https://github.com/frappe/frappe/pull/19029): Efforts to improve type safety in Frappe
- [Issue #14905](https://github.com/frappe/frappe/issues/14905): Discussion on improving API documentation
