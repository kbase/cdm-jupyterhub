from collections.abc import Mapping
from typing import Any, TypeVar, Union, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="SparkClusterConfig")


@_attrs_define
class SparkClusterConfig:
    """Configuration for creating a new Spark cluster.

    Attributes:
        worker_count (Union[Unset, int]): Number of worker nodes in the Spark cluster (Range: 1 to 25). Default: 2.
        worker_cores (Union[Unset, int]): Number of CPU cores allocated to each worker node (Range: 1 to 64). Default:
            10.
        worker_memory (Union[Unset, int, str]): Memory allocated per worker node (Range: 102.4 MiB to 256 GiB). Accepts
            formats like '10GiB', '10240MiB'. Default: '10GiB'.
        master_cores (Union[Unset, int]): Number of CPU cores allocated to the master node (Range: 1 to 64). Default:
            10.
        master_memory (Union[Unset, int, str]): Memory allocated for the master node (Range: 102.4 MiB to 256 GiB).
            Accepts formats like '10GiB', '10240MiB'. Default: '10GiB'.
    """

    worker_count: Union[Unset, int] = 2
    worker_cores: Union[Unset, int] = 10
    worker_memory: Union[Unset, int, str] = "10GiB"
    master_cores: Union[Unset, int] = 10
    master_memory: Union[Unset, int, str] = "10GiB"
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        worker_count = self.worker_count

        worker_cores = self.worker_cores

        worker_memory: Union[Unset, int, str]
        if isinstance(self.worker_memory, Unset):
            worker_memory = UNSET
        else:
            worker_memory = self.worker_memory

        master_cores = self.master_cores

        master_memory: Union[Unset, int, str]
        if isinstance(self.master_memory, Unset):
            master_memory = UNSET
        else:
            master_memory = self.master_memory

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if worker_count is not UNSET:
            field_dict["worker_count"] = worker_count
        if worker_cores is not UNSET:
            field_dict["worker_cores"] = worker_cores
        if worker_memory is not UNSET:
            field_dict["worker_memory"] = worker_memory
        if master_cores is not UNSET:
            field_dict["master_cores"] = master_cores
        if master_memory is not UNSET:
            field_dict["master_memory"] = master_memory

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        worker_count = d.pop("worker_count", UNSET)

        worker_cores = d.pop("worker_cores", UNSET)

        def _parse_worker_memory(data: object) -> Union[Unset, int, str]:
            if isinstance(data, Unset):
                return data
            return cast(Union[Unset, int, str], data)

        worker_memory = _parse_worker_memory(d.pop("worker_memory", UNSET))

        master_cores = d.pop("master_cores", UNSET)

        def _parse_master_memory(data: object) -> Union[Unset, int, str]:
            if isinstance(data, Unset):
                return data
            return cast(Union[Unset, int, str], data)

        master_memory = _parse_master_memory(d.pop("master_memory", UNSET))

        spark_cluster_config = cls(
            worker_count=worker_count,
            worker_cores=worker_cores,
            worker_memory=worker_memory,
            master_cores=master_cores,
            master_memory=master_memory,
        )

        spark_cluster_config.additional_properties = d
        return spark_cluster_config

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
