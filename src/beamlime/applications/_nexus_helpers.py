# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2024 Scipp contributors (https://github.com/scipp)
from typing import (
    Any,
    Callable,
    Iterable,
    Literal,
    Mapping,
    Optional,
    Sequence,
    TypedDict,
)

import numpy as np


class NexusDatasetDict(TypedDict):
    """``dataset`` module structure in the nexus json format."""

    module: str
    config: dict[str, Any]
    attributes: list[Mapping[str, Any]]


NexusPath = tuple[str | None, ...]


class NexusGroupDict(TypedDict):
    """A nexus group that holds the data module place holder or datasets.

    It was named as a group, not a module
    since the module place holder is one of the children of it.
    """

    children: list[Mapping]
    """A module place holder or datasets."""
    name: str
    """Name of the group."""


NexusGroupDictStore = dict[NexusPath, NexusGroupDict]


def create_dataset(
    *, name: str, dtype: str, initial_values: Any, unit: str | None = None
) -> NexusDatasetDict:
    """Creates a dataset according to the arguments."""
    dataset: NexusDatasetDict = {
        "module": "dataset",
        "config": {
            "name": name,
            "dtype": dtype,
            "values": initial_values,
        },
        "attributes": [],
    }
    if unit is not None:
        attrs = dataset["attributes"]
        attrs.append(
            {
                "name": "units",
                "dtype": "string",
                "values": unit,
            }
        )
    return dataset


ModuleNameType = Literal["ev44"]  # "f144", "tdct" will be added in the future
"""Name of the module that is supported by beamlime."""


def _get_array_values(dataset: Mapping) -> np.ndarray:
    return dataset["config"]["values"]


def _set_values(dataset: Mapping, values: Any) -> None:
    dataset["config"]["values"] = values


def _initialize_ev44(group: NexusGroupDict) -> None:
    """Initialize ev44 datasets in the parent.

    Params
    ------
    group:
        A data group that has a module place holder as a child.

    Side Effects
    ------------
    ``children`` of the ``group`` will have 4 datasets with empty values.

    - event_time_zero
    - event_time_offset
    - event_index
    - event_id

    This function doesn't remove a place holder from the ``children``.
    It is expected to be removed outside of this function.

    """
    children = group.setdefault("children", [])
    # event_time_zero
    children.append(
        create_dataset(
            name="event_time_zero",
            dtype="int",
            initial_values=np.asarray([]),
            unit="ns",
        )
    )
    # event_time_offset
    children.append(
        create_dataset(
            name="event_time_offset",
            dtype="int",
            initial_values=np.asarray([]),
            unit="ns",
        )
    )
    # event_index
    children.append(
        create_dataset(
            name="event_index",
            dtype="int",
            initial_values=np.asarray([]),
        )
    )
    # event_id
    if "monitor" in group["name"]:
        ...  # Monitor doesn't have ``event_id``
    else:
        children.append(
            create_dataset(
                name="event_id",
                dtype="int",
                initial_values=np.asarray([]),
            )
        )


def _merge_ev44(group: NexusGroupDict, data_piece: Mapping) -> None:
    """Merges new values from a message into the data group.

    Params
    ------
    group:
        A data group that has a module place holder as a child.
    data_piece:
        New message containing deserialized ev44.

    Side Effects
    ------------
    Each dataset in the children of ``group`` will have new values appended.
    Most of array-like values are simply appended
    but the ``event_index``(``reference_time_index`` from ev44) is increased
    by the number of previous values of ``event_time_offset``
    to find the global ``event_index``.
    ``data_piece`` only has local ``event_index`` which always starts with 0.

    """
    # event_time_zero - reference_time
    event_time_zero_dataset = find_nexus_structure(group, ("event_time_zero",))
    original_event_time_zero = _get_array_values(event_time_zero_dataset)
    new_event_time_zero = data_piece["reference_time"]
    _set_values(
        event_time_zero_dataset,
        np.concatenate((original_event_time_zero, new_event_time_zero)),
    )
    # event_time_offset - time_of_flight
    event_time_offset_dataset = find_nexus_structure(group, ("event_time_offset",))
    original_event_time_offset = _get_array_values(event_time_offset_dataset)
    new_event_time_offset = data_piece["time_of_flight"]
    _set_values(
        event_time_offset_dataset,
        np.concatenate((original_event_time_offset, new_event_time_offset)),
    )
    # event_index - reference_time_index
    event_index_dataset = find_nexus_structure(group, ("event_index",))
    original_event_index = _get_array_values(event_index_dataset)
    event_index_offset = len(original_event_time_offset)
    new_event_index = data_piece["reference_time_index"] + event_index_offset
    _set_values(
        event_index_dataset, np.concatenate((original_event_index, new_event_index))
    )
    # event_id - pixel_id
    if (
        "pixel_id" in data_piece and data_piece["pixel_id"] is not None
    ):  # Pixel id is optional.
        event_id_dataset = find_nexus_structure(group, ("event_id",))
        original_event_id = _get_array_values(event_id_dataset)
        new_event_id = data_piece["pixel_id"]
        _set_values(event_id_dataset, np.concatenate((original_event_id, new_event_id)))


def _node_name(n):
    """Defines the name of a nexus tree branch or leaf"""
    config = n.get("config", {})
    return n.get("name", config.get("name"))


def iter_nexus_structure(
    structure: Mapping, root: Optional[NexusPath] = None
) -> Iterable[tuple[tuple[str | None, ...], Mapping]]:
    """Visits all branches and leafs in the nexus tree"""
    path = (*root, _node_name(structure)) if root is not None else tuple()
    yield path, structure
    for child in structure.get("children", []):
        yield from iter_nexus_structure(child, root=path)


def find_nexus_structure(structure: Mapping, path: Sequence[Optional[str]]) -> Mapping:
    """Returns the branch or leaf associated with `path`, or None if not found"""
    if len(path) == 0:
        return structure
    head, *tail = path
    for child in structure["children"]:
        if head == _node_name(child):
            return find_nexus_structure(child, tail)
    raise KeyError(f"Path {path} not found in the nexus structure.")


def find_parent(structure: Mapping, path: Sequence[Optional[str]]) -> NexusGroupDict:
    # TODO: We can use typeguard here later.
    return find_nexus_structure(structure, path[:-1])


def find_ev44_matching_paths(
    structure: Mapping, data_piece: Mapping
) -> Iterable[NexusPath]:
    source_name = data_piece["source_name"]
    for path, node in iter_nexus_structure(structure):
        if (
            node.get("module") == "ev44"
            and node.get("config", {}).get("source") == source_name
        ):
            yield path


def _merge_message_into_data_module_store(
    *,
    data_module_store: NexusGroupDictStore,
    structure: Mapping,
    data_piece: Mapping,
    path_matching_func: Callable[[Mapping, Mapping], Iterable[tuple[str | None, ...]]],
    data_field_initialize_func: Callable[[NexusGroupDict], None],
    merge_func: Callable[[NexusGroupDict, Mapping], None],
) -> None:
    """Bridge function to merge a message into the store.

    This bridge was needed since different modules
    have different ways to match the paths and merge the data.

    Parameters
    ----------
    data_module_store:
        The data module store that holds the data.
    structure:
        The nexus structure.
    data_piece:
        The content of the message.
    path_matching_func:
        A function that returns the paths that match the message.
    data_field_initialize_func:
        A function that initializes the datasets in the module.
        *Initialize is done only when the relevant message arrives.*
        It is because we should distinguish between empty dataset and
        unexpectedly-not-receiving data.
    merge_func:
        A function that merges the message into the store.

    Side Effects
    ------------
    The ``data_module_store`` is updated with the merged data.

    """
    for path in path_matching_func(structure, data_piece):
        try:
            merge_func(data_module_store[path], data_piece)
        except KeyError:
            parent = find_parent(structure, path)
            # Validate the module place holder in the parent
            if len(parent["children"]) > 1:
                raise ValueError("Multiple modules found in the same data group.")
            # Initialize the data module storage.
            data_module_store[path] = {
                **parent,
                "children": [],  # Drop the module place holder
            }
            # Initialize the data fields.
            data_field_initialize_func(data_module_store[path])
            # Merge data piece
            merge_func(data_module_store[path], data_piece)


def merge_message_into_data_module_store(
    data_module_store: NexusGroupDictStore,
    structure: Mapping,
    kind: ModuleNameType,
    data_piece: Mapping,
):
    """Merges message into the associated nexus group.

    If there are multiple paths that match the message,
    all paths will be used.
    In principle, there should only be one path that matches the message.

    But the nexus template does not guarantee that there is a unique matching module.
    There are still some nexus templates that contain multi-matching
    module place holders (i.e. same ``source_name`` in ev44 module).

    In this case, it is more safe to use all paths
    so that no data is lost in the data reduction,
    even though it means unnecessary memory usage
    and slower in the grouping/binning process
    (``N`` times slower where ``N`` is number of duplicating modules).

    For example, if we store all data in to every detector data bank,
    then irrelevant data points will not affect the data reduction
    once the data is grouped by the pixel ids.
    However, if we choose to store the data in only one of the detector data banks,
    then the data of the rest of detectors will be lost.
    """
    if kind == "ev44":
        _merge_message_into_data_module_store(
            data_module_store=data_module_store,
            structure=structure,
            data_piece=data_piece,
            path_matching_func=find_ev44_matching_paths,
            data_field_initialize_func=_initialize_ev44,
            merge_func=_merge_ev44,
        )
    else:
        raise NotImplementedError


def combine_data_module_store_and_structure(
    data_module_store: NexusGroupDictStore, structure: Mapping
) -> Mapping:
    """Creates a new nexus structure, replacing the stream modules
    with the datasets in `store`, while avoiding
    to copy data from `structure` if unnecessary"""
    if len(data_module_store) == 0:
        return structure
    if (None,) in data_module_store:
        return data_module_store[(None,)]

    new = {**structure}  # Faster than `dict()`
    # and avoid static type-error of `copy`
    # since `structure` is `Mapping`
    if "children" in structure:
        children = []
        for child in structure["children"]:
            children.append(
                combine_data_module_store_and_structure(
                    {
                        tuple(tail): group
                        for (head, *tail), group in data_module_store.items()
                        if head == _node_name(child)
                    },
                    child,
                )
            )
        new["children"] = children
    return new
