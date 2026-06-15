## Python Strict Typing Rules

* **Strict Type Hints**: Every function/method must have explicit parameter and return type hints (use `-> None` if empty).
* **Mypy Strict**: Code must pass `mypy --strict`. Use modern syntax (e.g., `int | None`, `list[str]`).
* **Layer Separation (Crucial)**:
  * **Database (ORM)**: Use modern SQLAlchemy 2.0 type-annotated style (e.g., `Mapped[str] = mapped_column(...)`).
  * **Data Validation (DTO/API)**: Use `Pydantic (v2)` exclusively for request/response schemas, API boundaries, and configuration.

## Post-build Verification
* **Type Check**: Always run `mypy --strict` to validate the typed correctness of the generated code after implementation.
* **Unit Testing**: Every new feature or code modification must be accompanied by corresponding unit tests to verify its correctness.