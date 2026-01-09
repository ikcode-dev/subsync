---
applyTo: "**/*.py"
---
# Python Coding Guidelines

## Code Style
- **PEP 8**: Follow the PEP 8 style guide for Python code.
- **Type Hints**: Use Python's type hinting system for all function arguments and return values.
- **Docstrings**: Write clear docstrings for modules, classes, and functions.

## Error Handling
- **Exceptions**: Use specific exception handling rather than catching generic `Exception`.
- **Logging**: Use the standard `logging` module instead of `print` statements for debug and info messages (unless outputting to stdout for CLI user interaction).

## Dataclasses
- **Mutable defaults**: Use `field(default_factory=lambda: [])` instead of `field(default_factory=list)` to ensure Pyright/Pylance can infer the correct element type from the annotation.

```python
# ❌ Causes "Type is partially unknown" warning
words: list[Word] = field(default_factory=list)

# ✅ Type checker infers list[Word] correctly
words: list[Word] = field(default_factory=lambda: [])
```
