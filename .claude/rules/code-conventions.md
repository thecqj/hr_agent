# Code Conventions

- **Strict type hints**: Every function must have parameter and return type annotations; must pass `mypy --strict`
- **Modern Python syntax**: `int | None`, `list[str]`, etc. (Python 3.12)
- **ORM style**: SQLAlchemy 2.x `Mapped[]` + `mapped_column()`, never `Column()`
- **DTO style**: Pydantic v2 `BaseModel` for all API boundaries; request/response schemas strictly separated
- **UUID primary keys**: All tables use UUID4; serialized as strings in API responses
- **Enums**: `str + enum.Enum` pattern; stored as enum value strings in DB
- **Circular imports**: ORM models use `TYPE_CHECKING` for type hints between models