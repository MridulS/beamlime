# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2023 Scipp contributors (https://github.com/scipp)

from logging import LogRecord
from types import TracebackType
from typing import Mapping, Union, overload

from colorama import Style

_SysExcInfoType = Union[
    tuple[type[BaseException], BaseException, Union[TracebackType, None]],
    tuple[None, None, None],
]

_ArgsType = Union[tuple[object, ...], Mapping[str, object]]


class BeamlimeLogRecord(LogRecord):
    """
    Note
    ----
    First 8 Arguments cannot be keyword-only arguments
    because of the way ``logging`` creates an empty record.
    It uses positional arguments to create a record instance.
    """

    _extra_defaults = {"app_name": ""}

    @overload
    def __init__(self, record: LogRecord):
        ...

    @overload
    def __init__(
        self,
        *,
        name: str,
        level: int,
        msg: object,
        pathname: Union[str, None] = None,
        lineno: Union[int, None] = None,
        func: Union[str, None] = None,
        sinfo: Union[str, None] = None,
        args: Union[_ArgsType, None] = None,
        exc_info: Union[_SysExcInfoType, None] = None,
        app_name: str = "",
    ):
        ...

    def __init__(
        self,
        record: Union[LogRecord, None] = None,
        *,
        name: Union[str, None] = None,
        level: Union[int, None] = None,
        msg: Union[object, None] = None,
        pathname: Union[str, None] = None,
        lineno: Union[int, None] = None,
        func: Union[str, None] = None,
        sinfo: Union[str, None] = None,
        args: Union[_ArgsType, None] = None,
        exc_info: Union[_SysExcInfoType, None] = None,
        app_name: str = "",
    ) -> None:
        self.app_name = app_name
        if record is not None:
            self.__copy_from__(record)
        else:
            super().__init__(
                name, level, pathname, lineno, msg, args, exc_info, func, sinfo
            )

    def __copy_from__(self, record: LogRecord) -> None:
        self.__dict__.update(record.__dict__)


class BeamlimeColorLogRecord(BeamlimeLogRecord):
    _extra_defaults = {
        "app_name": "",
        "ansi_color": "",
        "debug_color": "",
        "info_color": "",
        "warn_color": "",
        "reset_color": Style.RESET_ALL,
    }

    def __init__(
        self,
        record: Union[LogRecord, None] = None,
        *,
        name: Union[str, None] = None,
        level: Union[int, None] = None,
        msg: Union[object, None] = None,
        pathname: Union[str, None] = None,
        lineno: Union[int, None] = None,
        func: Union[str, None] = None,
        sinfo: Union[str, None] = None,
        args: Union[_ArgsType, None] = None,
        exc_info: Union[_SysExcInfoType, None] = None,
        app_name: str = "",
    ) -> None:
        self.ansi_color = self._extra_defaults["ansi_color"]
        self.reset_color = self._extra_defaults["reset_color"]
        if record is not None:
            super().__init__(record=record)
        else:
            super().__init__(
                name=name,
                level=level,
                pathname=pathname,
                lineno=lineno,
                msg=msg,
                args=args,
                exc_info=exc_info,
                func=func,
                sinfo=sinfo,
                app_name=app_name,
            )
