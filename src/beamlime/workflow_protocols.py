# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2024 Scipp contributors (https://github.com/scipp)
from importlib.metadata import entry_points
from pathlib import Path
from typing import NewType, Protocol, runtime_checkable

from ess.reduce.nexus.json_nexus import JSONGroup

try:
    import scipp as sc
except ImportError as e:
    raise ImportError("Please install the scipp to use the ``DummyWorkflow``.") from e


Workflow = NewType('Workflow', str)
'''Name of the workflow plugin to use'''

WorkflowResult = dict[str, sc.DataArray]
"""Result of a workflow, a dictionary of scipp DataArrays."""


@runtime_checkable
class StatelessWorkflow(Protocol):
    """
    Protocol for stateless workflows.

    Can be implemented by a class or a function in plugins, in the
    `beamlime.stateless` entry point group.
    """

    def __call__(
        self,
        nexus_filename: Path,
        nxevent_data: dict[str, JSONGroup],
        nxlog: dict[str, JSONGroup],
    ) -> WorkflowResult: ...


class DummyStatelessWorkflow:
    "Dummy workflow for testing purposes, returning random counts per event and log."

    def __init__(self):
        import numpy as np

        self.rng = np.random.default_rng()
        self.x = sc.array(dims=['x'], values=np.arange(10), unit='m')

    def __call__(
        self,
        nexus_filename: Path,
        nxevent_data: dict[str, JSONGroup],
        nxlog: dict[str, JSONGroup],
    ) -> WorkflowResult:
        from itertools import chain

        return {
            f'random_counts-{nexus_filename.as_posix()}-{name}': sc.DataArray(
                data=sc.array(dims=['x'], values=self.rng.random(10), unit='counts'),
                coords={'x': self.x},
            )
            for name in chain(nxevent_data, nxlog)
        }


def provide_stateless_workflow(workflow: Workflow) -> StatelessWorkflow:
    stateless_workflows = entry_points(group='beamlime.stateless')
    return stateless_workflows[workflow].load()


dummy_stateless_workflow = DummyStatelessWorkflow()


@runtime_checkable
class LiveWorkflow(Protocol):
    def __init__(self, nexus_filename: Path) -> None:
        """Initialize the workflow with all static information.

        The only argument we need is the path to the nexus file or
        a file object that workflow can read from,
        since the file carrys all the static information.
        """
        ...

    def __call__(
        self, nxevent_data: dict[str, JSONGroup], nxlog: dict[str, JSONGroup]
    ) -> WorkflowResult:
        """Call the workflow and return the computed results that can be visualized.

        Parameters
        ----------
        nxevent_data:
            Dictionary of event data groups.
            It should contain empty events even if no events was received
            since the last call.

        nxlog:
            Dictionary of log data groups.
            It should only contain keys that we received since the last call.


        Returns
        -------
        :
            A dictionary of objects that can be visualized.

        """
        ...