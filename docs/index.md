# FrappeAPI

⚠️ **Alert: Beta Version**

Build APIs for Frappe with the simplicity of FastAPI! FrappeAPI aims to streamline your Frappe development experience by offering a familiar, intuitive API creation process.

**Note:** This project is currently in beta and not yet ready for production use. Expect changes and improvements as we work towards a stable release.

## Why?

Despite Frappe >= 15.0.0 pushing towards using type hints for API development and enhancing `frappe.whitelist()`, FrappeAPI aims to take it a step further by:

- Wrapping `frappe.whitelist()` for an even smoother API design
- Providing automatic API documentation (like FastAPI) at `/docs`
- Implementing response-model-based serialization to guard contract between client and server
- Ultimately delivering a FastAPI-like developer experience in Frappe

The goal is to make Frappe API development more intuitive, type-safe, and self-documenting, building upon Frappe's recent improvements.

## Roadmap

- [x] Implement `app.get(...)` method
- [ ] Implement `app.post(...)` method
- [ ] Implement `app.put(...)` method
- [ ] Implement `app.patch(...)` method
- [ ] Implement `app.delete(...)` method

### Query Parameter Features

- [ ] Automatic query parameter parsing/conversion based on type hints
- [ ] Required query parameters `needy: str`
- [ ] Optional query parameters with default values `skip: int = 0`
- [ ] Optional query parameters without default values `limit: Union[int, None] = None`
- [ ] Automatic Documentation generation for query parameters
- [ ] Enum support for query parameters
- [ ] Additional information and validation for query parameters
  - [ ] String validations
    - [ ] min_length
    - [ ] max_length
    - [ ] regex pattern
  - [ ] Numeric validations
    - [ ] gt
    - [ ] ge
    - [ ] lt
    - [ ] le
  - [ ] Metadata
    - [ ] title
    - [ ] description
    - [ ] deprecated
