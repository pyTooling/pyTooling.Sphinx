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
A Sphinx directive drawing a hierarchy as a tree: a directory, a class hierarchy, the structure of a testsuite.

Written as text in a code block, a hierarchy needs its lines drawn by hand, can't link to what it shows, and can't
be folded. The ``tree`` directive takes the hierarchy as an indented list in the style of a YAML block sequence, and
draws the lines itself:

.. code-block:: ReST

   .. tree::
      :root-icon: 📦
      :node-icon: 📁
      :leaf-icon: 📄
      :icons:     > 📁

      - pyTooling
        - Tree
          - :class:`~pyTooling.Tree.Node`
        > Graph
        - README.md

**An entry is a line starting with a marker** and a space, and an entry indented deeper than the one above it is that
entry's child. An entry's text is inline ReST, so a role such as ``:class:`` or ``:ref:`` links to what the entry names.

.. rubric:: Roots, nodes and leaves

An entry without a parent is a root, an entry with children is a node, and every other entry is a leaf. An entry
marked ``-`` gets the icon of its kind. Option ``:icons:`` declares more markers, each with its own icon, whatever the
entry's kind is - e.g. a folder for an empty directory, which is a leaf.

.. rubric:: HTML and other formats

HTML draws an entry with children as a ``<details>`` element, so a reader folds and unfolds it without JavaScript;
the stylesheet draws the lines and shows the expanded or the collapsed icon. Every other format - e.g. LaTeX - finds
no visitor for :class:`TreeItem` and :class:`TreeLabel` and renders their base-classes instead: a nested bullet list
without icons.

.. seealso::

   :ref:`DIR/Tree`
      |rarr| The directive's options, with rendered examples.
   :mod:`pyTooling.Sphinx`
      |rarr| The extension this belongs to, and what else it brings.
"""
from re                   import compile as re_compile
from typing               import Any, Iterable, Optional as Nullable

from docutils             import nodes
from docutils.parsers.rst import directives
from sphinx.writers.html5 import HTML5Translator

from pyTooling.Decorators import export
from pyTooling.Tree       import Node
from pyTooling.Sphinx     import BaseDirective, SphinxExtensionError, strip


__all__ = ["DEFAULT_MARKER", "DEFAULT_ICONS", "CODE_POINT_PATTERN"]

#: The marker of an entry whose icon is the one of its kind.
DEFAULT_MARKER = "-"

#: The icons drawn when the directive's options don't state one, keyed by the option's name.
#:
#: Roots, nodes and leaves have none, so a tree shows only its lines; a node with children shows whether it is
#: expanded.
DEFAULT_ICONS = {
	"root-icon":      "",
	"node-icon":      "",
	"leaf-icon":      "",
	"expanded-icon":  "▾",
	"collapsed-icon": "▸",
}

#: A word of an icon option written as a Unicode code point, e.g. ``U+1F4C1``.
CODE_POINT_PATTERN = re_compile(r"U\+([0-9A-Fa-f]{1,6})")

_Entry = Node[None, str, str, Any]
"""An entry of the content: its text as the value, the index of its line and its marker as key-value pairs."""


@export
def icon(option: Nullable[str]) -> str:
	"""
	Option converter reading an icon: characters as written, and a word ``U+<hex>`` as the code point it names.

	A code point keeps a document readable in an editor whose font lacks the icon's glyph.

	:param option:      The option's value as it was written; ``None`` if the option has no value.
	:returns:           The icon's characters; empty if the option has no value, which draws no icon.
	:raises ValueError: If a word names a code point beyond U+10FFFF.
	"""
	if option is None:
		return ""

	characters = []
	for word in option.split():
		if (match := CODE_POINT_PATTERN.fullmatch(word)) is None:
			characters.append(word)
		elif (codePoint := int(match[1], 16)) > 0x10ffff:
			raise ValueError(f"'{word}' is beyond the last code point U+10FFFF.")
		else:
			characters.append(chr(codePoint))

	return "".join(characters)


@export
def markerIcons(option: Nullable[str]) -> dict[str, str]:
	"""
	Option converter reading the markers an entry may start with, each with its icon: ``<marker> <icon>``, separated by
	commas.

	A marker is one character, neither a letter, a digit, a comma nor a space. An icon is read by :func:`icon`.

	:param option:      The option's value as it was written; ``None`` if the option has no value.
	:returns:           The icons, keyed by their marker.
	:raises ValueError: If an item isn't a marker followed by a space and an icon.
	:raises ValueError: If a marker is a letter, a digit or a comma.
	:raises ValueError: If a marker is declared twice.
	"""
	if option is None:
		return {}

	icons: dict[str, str] = {}
	for item in option.split(","):
		if (item := item.strip()) == "":
			continue

		marker, separator, value = item[0], item[1:2], item[2:]
		if separator.strip() != "" or value.strip() == "":
			raise ValueError(f"'{item}' is not a marker followed by a space and an icon.")
		elif marker.isalnum():
			raise ValueError(f"Marker '{marker}' is a letter or a digit.")
		elif marker in icons:
			raise ValueError(f"Marker '{marker}' is declared twice.")

		icons[marker] = icon(value)

	return icons


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


@export
def visitTreeItem(translator: HTML5Translator, node: TreeItem) -> None:
	"""
	Open an entry in HTML: a list item, and a ``<details>`` element if the entry has children.

	:param translator: The HTML translator writing the page.
	:param node:       The entry.
	"""
	translator.body.append(translator.starttag(node, "li", ""))
	if node["expanded"] is not None:
		translator.body.append("<details open>" if node["expanded"] else "<details>")


@export
def departTreeItem(translator: HTML5Translator, node: TreeItem) -> None:
	"""
	Close an entry in HTML.

	:param translator: The HTML translator writing the page.
	:param node:       The entry.
	"""
	if node["expanded"] is not None:
		translator.body.append("</details>")
	translator.body.append("</li>\n")


@export
def visitTreeLabel(translator: HTML5Translator, node: TreeLabel) -> None:
	"""
	Open an entry's text in HTML, behind its icons.

	An entry with children opens a ``<summary>`` and writes both expander icons, the stylesheet showing one of them.
	Any other entry writes an empty expander instead, so its text is aligned with its siblings'. Icons are hidden from
	a screen reader.

	:param translator: The HTML translator writing the page.
	:param node:       The entry's text.
	"""
	if node["expandedIcon"] is None:
		translator.body.append('<span class="tree-expander" aria-hidden="true"></span>')
	else:
		translator.body.append("<summary>")
		for state, stateIcon in (("expanded", node["expandedIcon"]), ("collapsed", node["collapsedIcon"])):
			translator.body.append(
				f'<span class="tree-expander tree-{state}" aria-hidden="true">{translator.encode(stateIcon)}</span>'
			)

	if node["icon"] != "":
		translator.body.append(f'<span class="tree-icon" aria-hidden="true">{translator.encode(node["icon"])}</span>')

	translator.body.append('<span class="tree-text">')


@export
def departTreeLabel(translator: HTML5Translator, node: TreeLabel) -> None:
	"""
	Close an entry's text in HTML, and its ``<summary>`` if the entry has children.

	:param translator: The HTML translator writing the page.
	:param node:       The entry's text.
	"""
	translator.body.append("</span>")
	if node["expandedIcon"] is not None:
		translator.body.append("</summary>")


@export
class Tree(BaseDirective):
	"""
	The ``tree`` directive: a hierarchy, written as an indented list, drawn as a tree.

	:meth:`_ParseEntries` reads the content into :class:`~pyTooling.Tree.Node` instances, one tree per root, and
	:meth:`_BuildItem` turns them into nested bullet lists of :class:`TreeItem` and :class:`TreeLabel`. The options
	choose the icons and how many levels are expanded initially; ``:class:`` puts additional CSS classes on the tree.
	"""

	directiveName: str = "tree"  #: Name the directive is invoked by.

	has_content =               True   #: A boolean; ``True`` if content is allowed.
	required_arguments =        0      #: Number of required directive arguments.
	optional_arguments =        0      #: Number of optional arguments after the required ones.
	final_argument_whitespace = False  #: A boolean; ``True`` if the last argument may contain spaces.
	# docutils declares 'option_spec' on 'Directive' and 'BaseDirective' assigns it, so mypy calls every
	# spelling of this override a conflict with one of them
	#: Mapping of option names to validator functions.
	option_spec: dict[str, Any] = {  # type: ignore[misc]
		"root-icon":       icon,
		"node-icon":       icon,
		"leaf-icon":       icon,
		"expanded-icon":   icon,
		"collapsed-icon":  icon,
		"icons":           markerIcons,
		"expanded-levels": directives.nonnegative_int,
		"class":           strip,
	}

	def run(self) -> list[nodes.Node]:
		"""
		Draw the hierarchy written in the content.

		:returns: The tree as a bullet list, or the message of whatever the content got wrong.
		"""
		try:
			markers = self.options.get("icons", {})
			roots = self._ParseEntries(self.content, (DEFAULT_MARKER, *markers))
		except SphinxExtensionError as ex:
			return [self.state.document.reporter.error(f"{self.directiveName}: {ex}", line=self.lineno)]

		icons = {name: self.options.get(name, default) for name, default in DEFAULT_ICONS.items()}
		icons.update(markers)
		expandedLevels = self.options.get("expanded-levels", None)

		tree = nodes.bullet_list(classes=["pytooling-tree"] + self.options.get("class", "").split())
		for root in roots:
			tree += self._BuildItem(root, icons, expandedLevels)

		return [tree]

	@staticmethod
	def _ParseEntries(content: Iterable[str], markers: Iterable[str] = (DEFAULT_MARKER, )) -> list[_Entry]:
		"""
		Read the content into trees: an entry per line, and an entry indented deeper than the one above is its child.

		An entry's text is the node's value. Key ``index`` holds the index of the entry's line in the content, and key
		``marker`` the marker the line starts with.

		:param content:               The directive's content, line by line.
		:param markers:               Optional, the markers an entry may start with. Default: ``-``.
		:returns:                     The root of each tree, in the order written.
		:raises SphinxExtensionError: If the content holds no entry.
		:raises SphinxExtensionError: If a line doesn't start with a marker and a space.
		:raises SphinxExtensionError: If an entry has no text.
		:raises SphinxExtensionError: If an entry is indented less than the entry above, but not as deep as one of its
		                              ancestors.
		"""
		roots: list[_Entry] = []
		ancestors: list[tuple[int, _Entry]] = []  # entries the next one can be a child or a sibling of, with indentation
		for index, line in enumerate(content):
			if (text := line.lstrip(" ")).strip() == "":
				continue

			indentation = len(line) - len(text)
			marker = text[0]
			if marker not in markers or text[1:2].strip() != "":
				accepted = ", ".join(f"'{marker} '" for marker in markers)
				raise SphinxExtensionError(f"'{text.rstrip()}' is not an entry, which starts with {accepted}.")

			if (value := text[1:].strip()) == "":
				raise SphinxExtensionError(f"'{text.rstrip()}' is an entry without text.")

			closed = False
			while len(ancestors) > 0 and ancestors[-1][0] > indentation:
				ancestors.pop()
				closed = True

			if len(ancestors) > 0 and ancestors[-1][0] == indentation:
				ancestors.pop()
			elif closed:
				raise SphinxExtensionError(
					f"'{text.rstrip()}' is indented less than the entry above, but not as deep as one of its ancestors."
				)

			parent = ancestors[-1][1] if len(ancestors) > 0 else None
			entry: _Entry = Node(value=value, keyValuePairs={"index": index, "marker": marker}, parent=parent)
			if parent is None:
				roots.append(entry)

			ancestors.append((indentation, entry))

		if len(roots) == 0:
			raise SphinxExtensionError("The directive's content holds no entry.")

		return roots

	def _BuildItem(self, entry: _Entry, icons: dict[str, str], expandedLevels: Nullable[int]) -> TreeItem:
		"""
		Build an entry and, below it, its children.

		The entry's text is parsed as inline ReST at the line it was written on, so a message about a role in it points
		to that line. Such messages follow the entry's text in the list item.

		:param entry:          The entry, as :meth:`_ParseEntries` read it.
		:param icons:          The icons, keyed by the option naming them, or by their marker.
		:param expandedLevels: How many levels are expanded initially; ``None`` expands all.
		:returns:              The entry as a list item, holding its text and a bullet list of its children.
		"""
		textNodes, messages = self.state.inline_text(entry.Value, self.content_offset + entry["index"] + 1)

		if entry.IsRoot:
			kind = "root"
		elif entry.HasChildren:
			kind = "node"
		else:
			kind = "leaf"

		entryIcon = icons[entry["marker"]] if entry["marker"] in icons else icons[f"{kind}-icon"]

		item = TreeItem("", classes=[f"tree-{kind}"] + (["tree-expandable"] if entry.HasChildren else []))
		item += (label := TreeLabel(entry.Value, "", *textNodes, icon=entryIcon))
		item += messages

		if not entry.HasChildren:
			item["expanded"] = None
			label["expandedIcon"] = None
			label["collapsedIcon"] = None
			return item

		item["expanded"] = expandedLevels is None or entry.Level < expandedLevels
		label["expandedIcon"] = icons["expanded-icon"]
		label["collapsedIcon"] = icons["collapsed-icon"]

		item += (children := nodes.bullet_list())
		for child in entry.GetChildren():
			children += self._BuildItem(child, icons, expandedLevels)

		return item
