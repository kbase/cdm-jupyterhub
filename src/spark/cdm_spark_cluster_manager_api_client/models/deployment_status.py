from collections.abc import Mapping
from typing import Any, TypeVar, Union, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="DeploymentStatus")


@_attrs_define
class DeploymentStatus:
    """Status information of a Kubernetes deployment.

    Attributes:
        available_replicas (Union[Unset, int]): Number of available replicas Default: 0.
        ready_replicas (Union[Unset, int]): Number of ready replicas Default: 0.
        replicas (Union[Unset, int]): Total number of desired replicas Default: 0.
        unavailable_replicas (Union[Unset, int]): Number of unavailable replicas Default: 0.
        is_ready (Union[Unset, bool]): Whether all replicas are ready Default: False.
        exists (Union[Unset, bool]): Whether the deployment exists Default: True.
        error (Union[None, Unset, str]): Error message if any
    """

    available_replicas: Union[Unset, int] = 0
    ready_replicas: Union[Unset, int] = 0
    replicas: Union[Unset, int] = 0
    unavailable_replicas: Union[Unset, int] = 0
    is_ready: Union[Unset, bool] = False
    exists: Union[Unset, bool] = True
    error: Union[None, Unset, str] = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        available_replicas = self.available_replicas

        ready_replicas = self.ready_replicas

        replicas = self.replicas

        unavailable_replicas = self.unavailable_replicas

        is_ready = self.is_ready

        exists = self.exists

        error: Union[None, Unset, str]
        if isinstance(self.error, Unset):
            error = UNSET
        else:
            error = self.error

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if available_replicas is not UNSET:
            field_dict["available_replicas"] = available_replicas
        if ready_replicas is not UNSET:
            field_dict["ready_replicas"] = ready_replicas
        if replicas is not UNSET:
            field_dict["replicas"] = replicas
        if unavailable_replicas is not UNSET:
            field_dict["unavailable_replicas"] = unavailable_replicas
        if is_ready is not UNSET:
            field_dict["is_ready"] = is_ready
        if exists is not UNSET:
            field_dict["exists"] = exists
        if error is not UNSET:
            field_dict["error"] = error

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        available_replicas = d.pop("available_replicas", UNSET)

        ready_replicas = d.pop("ready_replicas", UNSET)

        replicas = d.pop("replicas", UNSET)

        unavailable_replicas = d.pop("unavailable_replicas", UNSET)

        is_ready = d.pop("is_ready", UNSET)

        exists = d.pop("exists", UNSET)

        def _parse_error(data: object) -> Union[None, Unset, str]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, str], data)

        error = _parse_error(d.pop("error", UNSET))

        deployment_status = cls(
            available_replicas=available_replicas,
            ready_replicas=ready_replicas,
            replicas=replicas,
            unavailable_replicas=unavailable_replicas,
            is_ready=is_ready,
            exists=exists,
            error=error,
        )

        deployment_status.additional_properties = d
        return deployment_status

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
