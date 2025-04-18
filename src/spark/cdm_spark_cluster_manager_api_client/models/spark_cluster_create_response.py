from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

T = TypeVar("T", bound="SparkClusterCreateResponse")


@_attrs_define
class SparkClusterCreateResponse:
    """Response model for cluster creation.

    Attributes:
        cluster_id (str): Unique identifier for the cluster
        master_url (str): URL to connect to the Spark master
        master_ui_url (str): URL to access the Spark master UI
    """

    cluster_id: str
    master_url: str
    master_ui_url: str
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        cluster_id = self.cluster_id

        master_url = self.master_url

        master_ui_url = self.master_ui_url

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "cluster_id": cluster_id,
                "master_url": master_url,
                "master_ui_url": master_ui_url,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        cluster_id = d.pop("cluster_id")

        master_url = d.pop("master_url")

        master_ui_url = d.pop("master_ui_url")

        spark_cluster_create_response = cls(
            cluster_id=cluster_id,
            master_url=master_url,
            master_ui_url=master_ui_url,
        )

        spark_cluster_create_response.additional_properties = d
        return spark_cluster_create_response

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
