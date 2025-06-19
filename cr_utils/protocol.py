import copy
from dataclasses import dataclass
from typing import Type, TypeVar, cast, get_origin


T = TypeVar("T")

def list_of_dict_to_dict_of_list(list_of_dict: list[dict]) -> dict[list]:
    """
    list[dict] -> dict[list]
    """
    if len(list_of_dict) == 0:
        return {}
    keys = list_of_dict[0].keys()
    output = {key: [] for key in keys}
    for data in list_of_dict:
        for key, item in data.items():
            assert key in output
            output[key].append(item)
    return output

@dataclass
class DataProto:
    item: dict

    def get(self, key: str, typ: Type[T]) -> T:
        value = self.item.get(key)
        origin = get_origin(typ)
        base_type = origin if origin is not None else typ
        if value is not None and not isinstance(value, base_type):
            raise TypeError(f"Key '{key}' expected to be {typ}, got {type(value)}")
        return cast(T, value)

    def select(self, keys: list[str], deepcopy: bool = False) -> 'DataProto':
        if deepcopy:
            item = copy.deepcopy(self.item)
        else:
            item = self.item
        return DataProto({key: item[key] for key in keys})

    def pop(self, keys: list[str]) -> 'DataProto':
        return DataProto({key: self.item.pop(key) for key in keys})

    def push(self, item: dict):
        for key in item:
            self.item[key] = item[key]
