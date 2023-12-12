# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2023 Scipp contributors (https://github.com/scipp)
# Accessible binders with all necessary providers filled in.
# flake8: noqa F401

from .constructors import Factory
from .logging.providers import log_providers

log_factory = Factory(log_providers)