# ==================================================================================================================== #
#             _____           _ _               ____        _     _                                                    #
#  _ __  _   |_   _|__   ___ | (_)_ __   __ _  / ___| _ __ | |__ (_)_ __ __  __                                        #
# | '_ \| | | || |/ _ \ / _ \| | | '_ \ / _` | \___ \| '_ \| '_ \| | '_ \\ \/ /                                        #
# | |_) | |_| || | (_) | (_) | | | | | | (_| |_ ___) | |_) | | | | | | | |>  <                                         #
# | .__/ \__, ||_|\___/ \___/|_|_|_| |_|\__, (_)____/| .__/|_| |_|_|_| |_/_/\_\                                        #
# |_|    |___/                          |___/        |_|                                                               #
# ==================================================================================================================== #
# Authors:                                                                                                             #
#   Patrick Lehmann                                                                                                    #
#                                                                                                                      #
# License:                                                                                                             #
# ==================================================================================================================== #
# Copyright 2026-2026 Patrick Lehmann - Bötzingen, Germany                                                             #
#                                                                                                                      #
# Licensed under the Apache License, Version 2.0 (the "License");                                                      #
# you may not use this file except in compliance with the License.                                                     #
# You may obtain a copy of the License at                                                                              #
#                                                                                                                      #
#   http://www.apache.org/licenses/LICENSE-2.0                                                                         #
#                                                                                                                      #
# Unless required by applicable law or agreed to in writing, software                                                  #
# distributed under the License is distributed on an "AS IS" BASIS,                                                    #
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.                                             #
# See the License for the specific language governing permissions and                                                  #
# limitations under the License.                                                                                       #
#                                                                                                                      #
# SPDX-License-Identifier: Apache-2.0                                                                                  #
# ==================================================================================================================== #
#
"""
The docutils nodes pyTooling.Sphinx adds, and what registering one with Sphinx takes.

A node is a class here; the functions writing it are in a module per output format - :mod:`~pyTooling.Sphinx.HTML` -
and :data:`~pyTooling.Sphinx.NODES` pairs both for :func:`~pyTooling.Sphinx.setup`. A node without visitors for a
format is written by the visitors of its base-class there.
"""
from typing               import Any, Callable, NotRequired, TypedDict

from docutils             import nodes

from pyTooling.Decorators import export


__all__ = ["visitFunc", "departFunc"]

type visitFunc =  Callable[[Any, Any], Any]
"""A function writing the start of a node: called with the translator and the node."""

type departFunc = Callable[[Any, Any], Any]
"""A function writing the end of a node: called with the translator and the node."""


@export
class RegisteredNode(TypedDict):
	"""An entry of :data:`~pyTooling.Sphinx.NODES`: a node class, and its visitors per output format."""

	name:  str                                        #: Name of the node.
	node:  type[nodes.Element]                        #: The node class to register.
	html:  tuple[visitFunc, departFunc]               #: Visit and depart function writing the node in HTML.
	latex: NotRequired[tuple[visitFunc, departFunc]]  #: Visit and depart function writing the node in LaTeX, if any.


@export
class TreeItem(nodes.list_item):
	"""
	An entry of a tree: a list item, which HTML draws around a ``<details>`` element if the entry has children.

	Attribute ``expanded`` states whether the entry is expanded initially, and is ``None`` if it has no children.
	"""


@export
class TreeLabel(nodes.paragraph):
	"""
	An entry's text: a paragraph, which HTML draws as the ``<summary>`` of the entry's ``<details>`` element.

	Attribute ``icon`` holds the icon of the entry's kind, ``expandedIcon`` and ``collapsedIcon`` the icons showing
	whether the entry is expanded. Both are ``None`` if the entry has no children.
	"""
