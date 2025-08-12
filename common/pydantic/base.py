from typing import Any, Literal

from pydantic import BaseModel as PydanticBaseModel, ConfigDict


class BaseModel(PydanticBaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        str_strip_whitespace=True,
        from_attributes=True,
    )

    def md(
        self,
        *,
        mode: Literal["json", "python"] = "python",
        include: set[int] | set[str] | dict[int, Any] | dict[str, Any] | None = None,
        exclude: set[int] | set[str] | dict[int, Any] | dict[str, Any] | None = None,
        context: Any | None = None,
        by_alias: bool = False,
        exclude_unset: bool = False,
        exclude_defaults: bool = False,
        exclude_none: bool = False,
        round_trip: bool = False,
        warnings: Literal["none", "warn", "error"] | bool = True,
        serialize_as_any: bool = False,
    ) -> dict[str, Any]:
        return super().model_dump(
            mode=mode,
            include=include,
            exclude=exclude,
            context=context,
            by_alias=by_alias,
            exclude_unset=exclude_unset,
            exclude_defaults=exclude_defaults,
            exclude_none=exclude_none,
            round_trip=round_trip,
            warnings=warnings,
            serialize_as_any=serialize_as_any,
        )

    def md_json(
        self,
        *,
        indent: int | None = None,
        include: set[int] | set[str] | dict[int, Any] | dict[str, Any] | None = None,
        exclude: set[int] | set[str] | dict[int, Any] | dict[str, Any] | None = None,
        context: Any | None = None,
        by_alias: bool = False,
        exclude_unset: bool = False,
        exclude_defaults: bool = False,
        exclude_none: bool = False,
        round_trip: bool = False,
        warnings: Literal["none", "warn", "error"] | bool = True,
        serialize_as_any: bool = False,
    ) -> str:
        return super().model_dump_json(
            indent=indent,
            include=include,
            exclude=exclude,
            context=context,
            by_alias=by_alias,
            exclude_unset=exclude_unset,
            exclude_defaults=exclude_defaults,
            exclude_none=exclude_none,
            round_trip=round_trip,
            warnings=warnings,
            serialize_as_any=serialize_as_any,
        )
