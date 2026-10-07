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

A node is a class here; the functions writing it are in a module per output format - :mod:`~pyTooling.Sphinx.HTML`
and :mod:`~pyTooling.Sphinx.LaTeX` - and :data:`~pyTooling.Sphinx.NODES` pairs both for :func:`~pyTooling.Sphinx.setup`.
A node without visitors for a format is written by the visitors of its base-class there.
"""
from typing               import Any, Callable, NotRequired, TypedDict

from docutils             import nodes

from pyTooling.Decorators import export


__all__ = ["visitFunc", "departFunc", "COVERAGE_STATES"]

#: The coverage states of a listing's lines, as the listing's legend names them, by state; ``""`` for a line, which
#: isn't executable.
COVERAGE_STATES = {
	"covered":   "covered",
	"partial":   "partial",
	"uncovered": "uncovered",
	"excluded":  "excluded",
	"":          "not executable",
}

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
	Attribute ``columnWidth`` holds the width of the column of the entries' texts as a CSS length, measured from the
	tree's left edge, if the entry is a root of a tree with descriptions; else ``None``.
	"""


@export
class TreeLabel(nodes.paragraph):
	"""
	An entry's text: a paragraph, which HTML draws as the ``<summary>`` of the entry's ``<details>`` element.

	Attribute ``icon`` holds the icon of the entry's kind, ``expandedIcon`` and ``collapsedIcon`` the icons showing
	whether the entry is expanded. Both are ``None`` if the entry has no children. Attribute ``level`` holds the entry's
	level, ``0`` for a root, and ``descriptionColumn`` whether the tree has descriptions: then HTML draws the entry as
	a row of two columns, whether this entry has a description or not.

	An entry's description follows its text, as a :class:`TreeSeparator` and a :class:`TreeDescription`.
	"""


@export
class TreeSeparator(nodes.inline):
	"""
	The separator between an entry's text and its description: an en dash, which HTML skips.

	HTML draws the description in a column of its own. Every other format - e.g. LaTeX - writes its base-class, so the
	description follows the text in the same line: ``text – description``.
	"""


@export
class TreeDescription(nodes.inline):
	"""
	An entry's description, which HTML draws in a column of its own: all descriptions of a tree start at the same
	horizontal position, whatever the entry's level.
	"""


@export
class Abbreviation(nodes.abbreviation):
	"""
	A reference to an abbreviation in its short form, which HTML draws with a box explaining it on hover.

	Attributes ``short`` and ``long`` hold the abbreviation's forms, even if the node's text is a title the role was
	written with; ``summary`` holds the summary of its description the box shows, or an empty string. The attribute
	``explanation`` of the base-class is left unset: LaTeX and text would append it in parentheses, and an abbreviation
	is written in the form its role asks for.
	"""


@export
class Landscape(nodes.container):
	"""
	A container whose content LaTeX puts on landscape pages, e.g. a wide table; HTML writes the content only.

	LaTeX's ``landscape`` environment needs package ``pdflscape``, which :func:`~pyTooling.Sphinx.setup` requests. The
	report tables of domain ``report`` are what this node holds.
	"""


@export
class CoverageListing(nodes.literal_block):
	"""
	A source file's code coverage: its lines, syntax highlighted, each marked by its coverage state.

	Attribute ``lines`` holds a tuple per line: the line number, the state (``covered``, ``partial``, ``uncovered``,
	``excluded``, or ``""`` for a line, which isn't executable), the hits or ``None``, the number of branches and of
	taken branches, and the line's tokens as ``(CSS class, text)`` pairs - the short classes of Pygments' token types,
	which Sphinx' Pygments stylesheet colors. Attribute ``anchors`` states whether a line gets the ID ``L<number>``.
	Attribute ``path`` holds the file's path in the report, which the listing's header shows beside the legend of the
	coverage states.

	The node's text is the plain source, so a builder without visitors for this node writes it as a literal block.
	"""
