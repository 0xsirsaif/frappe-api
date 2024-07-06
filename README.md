# FrappeAPI

⚠️ **Alert: Beta Version**

Build APIs for Frappe with the simplicity of FastAPI! FrappeAPI aims to streamline your Frappe development experience by offering a familiar, intuitive API creation process.

**Note:** This project is currently in beta and not yet ready for production use. Expect changes and improvements as we work towards a stable release.

## Why?

Despite Frappe >= 15.0.0 pushing towards using type hints for API development and enhancing `frappe.whitelist()`, I'd like to take it a step further. This project aims to:

- Wrap `frappe.whitelist()` for an even smoother API design
- Provide automatic API documentation (like FastAPI) at `/docs`
- Implement response-model-based serialization to guard contract between client and server
- Ultimately deliver a FastAPI-like developer experience in Frappe

The goal is to make Frappe API development more intuitive, type-safe, and self-documenting, building upon Frappe's recent improvements.

And honestly? Why not? Sometimes you just want to build something cool, even if it might be a bit unnecessary. Who knows, it might just make Frappe developers' lives a little easier (or at least more FastAPI-ish). I'm doing it for the love of coding, the thrill of "what if?", and of course, for learning. If it helps someone along the way, that's a bonus!

## Roadmap

### Frappe

- [ ] Frappe V14 support
- [ ] Frappe V15 support

### Methods

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
