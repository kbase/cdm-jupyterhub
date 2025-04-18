from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, Union, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.deployment_status import DeploymentStatus


T = TypeVar("T", bound="SparkClusterStatus")


@_attrs_define
class SparkClusterStatus:
    """Status information about a Spark cluster.

    Attributes:
        master (DeploymentStatus): Status information of a Kubernetes deployment.
        workers (DeploymentStatus): Status information of a Kubernetes deployment.
        master_url (Union[None, Unset, str]): Spark master URL
        master_ui_url (Union[None, Unset, str]): Spark master UI URL
        error (Union[Unset, bool]): Whether there was an error during the status check Default: False.
    """

    master: "DeploymentStatus"
    workers: "DeploymentStatus"
    master_url: Union[None, Unset, str] = UNSET
    master_ui_url: Union[None, Unset, str] = UNSET
    error: Union[Unset, bool] = False
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        master = self.master.to_dict()

        workers = self.workers.to_dict()

        master_url: Union[None, Unset, str]
        if isinstance(self.master_url, Unset):
            master_url = UNSET
        else:
            master_url = self.master_url

        master_ui_url: Union[None, Unset, str]
        if isinstance(self.master_ui_url, Unset):
            master_ui_url = UNSET
        else:
            master_ui_url = self.master_ui_url

        error = self.error

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "master": master,
                "workers": workers,
            }
        )
        if master_url is not UNSET:
            field_dict["master_url"] = master_url
        if master_ui_url is not UNSET:
            field_dict["master_ui_url"] = master_ui_url
        if error is not UNSET:
            field_dict["error"] = error

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.deployment_status import DeploymentStatus

        d = dict(src_dict)
        master = DeploymentStatus.from_dict(d.pop("master"))

        workers = DeploymentStatus.from_dict(d.pop("workers"))

        def _parse_master_url(data: object) -> Union[None, Unset, str]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, str], data)

        master_url = _parse_master_url(d.pop("master_url", UNSET))

        def _parse_master_ui_url(data: object) -> Union[None, Unset, str]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, str], data)

        master_ui_url = _parse_master_ui_url(d.pop("master_ui_url", UNSET))

        error = d.pop("error", UNSET)

        spark_cluster_status = cls(
            master=master,
            workers=workers,
            master_url=master_url,
            master_ui_url=master_ui_url,
            error=error,
        )

        spark_cluster_status.additional_properties = d
        return spark_cluster_status

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
