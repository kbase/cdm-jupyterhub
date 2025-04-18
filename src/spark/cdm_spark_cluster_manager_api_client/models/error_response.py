from collections.abc import Mapping
from typing import Any, TypeVar, Union, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="ErrorResponse")


@_attrs_define
class ErrorResponse:
    """Standard error response model.

    Attributes:
        error (Union[None, Unset, int]): Error code
        error_type (Union[None, Unset, str]): Error type
        message (Union[None, Unset, str]): Error message
    """

    error: Union[None, Unset, int] = UNSET
    error_type: Union[None, Unset, str] = UNSET
    message: Union[None, Unset, str] = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        error: Union[None, Unset, int]
        if isinstance(self.error, Unset):
            error = UNSET
        else:
            error = self.error

        error_type: Union[None, Unset, str]
        if isinstance(self.error_type, Unset):
            error_type = UNSET
        else:
            error_type = self.error_type

        message: Union[None, Unset, str]
        if isinstance(self.message, Unset):
            message = UNSET
        else:
            message = self.message

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if error is not UNSET:
            field_dict["error"] = error
        if error_type is not UNSET:
            field_dict["error_type"] = error_type
        if message is not UNSET:
            field_dict["message"] = message

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)

        def _parse_error(data: object) -> Union[None, Unset, int]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, int], data)

        error = _parse_error(d.pop("error", UNSET))

        def _parse_error_type(data: object) -> Union[None, Unset, str]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, str], data)

        error_type = _parse_error_type(d.pop("error_type", UNSET))

        def _parse_message(data: object) -> Union[None, Unset, str]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, str], data)

        message = _parse_message(d.pop("message", UNSET))

        error_response = cls(
            error=error,
            error_type=error_type,
            message=message,
        )

        error_response.additional_properties = d
        return error_response

    @property
    def additional_keys(self) -> list[str]:
        return list(self.additional_properties.keys())

    def __getitem__(self, key: str) -> Any:
        return self.additional_properties[key]

    def __setitem__(self, key: str, value: Any) -> None:
        self.additional_properties[key] = value

    def __delitem__(self, key: str) -> None:
        del self.additional_properties[key]

    def __contains__(self, key: str) -> bool:
        return key in self.additional_properties
