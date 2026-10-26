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

.. rubric:: Descriptions

**A** ``|`` **between spaces separates an entry's text from its description**, which is inline ReST too. HTML draws
the descriptions as a second column: all of them start at the same horizontal position, whatever the entry's level.
An entry without a description stays valid:

.. code-block:: ReST

   .. tree::

      - CoverageSummary         | the report
        - Directory             | e.g. ``myPackage/``
          - File                | e.g. ``myPackage/Shapes.py``
        - Package

A ``|`` within a literal or a role's text, or escaped as ``\\|``, separates nothing, and neither does a substitution
reference such as ``|br|``.

.. rubric:: Roots, nodes and leaves

An entry without a parent is a root, an entry with children is a node, and every other entry is a leaf. An entry
marked ``-`` gets the icon of its kind. Option ``:icons:`` declares more markers, each with its own icon, whatever the
entry's kind is - e.g. a folder for an empty directory, which is a leaf.

.. rubric:: Legend

**An icon option may explain its icon**, behind a ``|`` between spaces: ``:leaf-icon: 📄 | file``. Option ``:icons:``
then declares one marker per line. The texts form the tree's legend, which HTML draws below the tree - or above it, as
option ``:legend:`` chooses:

.. code-block:: ReST

   .. tree::
      :legend:    top
      :root-icon: 📦 | package
      :node-icon: 📁 | directory
      :leaf-icon: 📄 | file
      :icons:     > ⚙️ | settings
                  # 🐍 | Python module

.. rubric:: HTML and other formats

HTML draws an entry with children as a ``<details>`` element, so a reader folds and unfolds it without JavaScript;
the stylesheet draws the lines and shows the expanded or the collapsed icon. Every other format - e.g. LaTeX - finds
no visitor for :class:`~pyTooling.Sphinx.Node.TreeItem` and :class:`~pyTooling.Sphinx.Node.TreeLabel` and renders
their base-classes instead: a nested bullet list without icons, with a description behind its entry's text and an en
dash. These formats have no legend, as their trees show no icons: :class:`RemoveTreeLegends` removes it.

.. seealso::

   :ref:`DIR/Tree`
      |rarr| The directive's options, with rendered examples.
   :mod:`pyTooling.Sphinx`
      |rarr| The extension this belongs to, and what else it brings.
"""
from re                                import compile as re_compile
from typing                            import Any, Iterable, Optional as Nullable
from unicodedata                       import category, east_asian_width

from docutils                          import nodes
from docutils.parsers.rst              import directives
from sphinx.transforms.post_transforms import SphinxPostTransform

from pyTooling.Common                  import StringEnum
from pyTooling.Decorators              import export
from pyTooling.Tree                    import Node
from pyTooling.Sphinx                  import BaseDirective, SphinxExtensionError, strip
from pyTooling.Sphinx.Node             import TreeDescription, TreeItem, TreeLabel, TreeLegend, TreeLegendItem, \
                                              TreeSeparator


__all__ = [
	"DEFAULT_MARKER", "DEFAULT_ICONS", "CODE_POINT_PATTERN", "SEPARATOR_PATTERN", "SEPARATOR"
]

DEFAULT_MARKER = "-"
"""The marker of an entry whose icon is the one of its kind."""

DEFAULT_ICONS = {
	"root-icon":      "",
	"node-icon":      "",
	"leaf-icon":      "",
	"expanded-icon":  "▾",
	"collapsed-icon": "▸",
}
"""
The icons drawn when the directive's options don't state one, keyed by the option's name.

Roots, nodes and leaves have none, so a tree shows only its lines; a node with children shows whether it is
expanded.
"""

CODE_POINT_PATTERN = re_compile(r"U\+([0-9A-Fa-f]{1,6})")
"""A word of an icon option written as a Unicode code point, e.g. ``U+1F4C1``."""

SEPARATOR_PATTERN = re_compile(r"\\.|``.*?``|`(?:\\.|[^`\\])*`|(?<=\s)(?P<separator>\|)(?=\s|$)")
"""
The separator between an entry's text and its description, as group ``separator``: a ``|`` after whitespace and
before whitespace or the line's end.

The other alternatives match what the separator isn't searched in - an escaped character, an inline literal, and
interpreted text such as a role's -, so a ``|`` in them separates nothing.
"""

SEPARATOR = " \u2013 "
"""What a format without columns writes between an entry's text and its description: an en dash between spaces."""

_Entry = Node
"""
An entry of the content: its text as the value, the index of its line, its marker and its description as key-value
pairs.
"""


@export
def icon(option: Nullable[str]) -> str:
	"""
	Option converter reading an icon: characters as written, and a word ``U+<hex>`` as the code point it names.

	A code point keeps a document readable in an editor whose font lacks the icon's glyph.

	:param option:      The option's value as it was written; ``None`` if the option has no value.
	:returns:           The icon's characters; empty if the option has no value, which draws no icon.
	:raises ValueError: If a word names a code point beyond U+10FFFF.
	:raises ValueError: If a word names a surrogate code point, which is no character.
	"""
	if option is None:
		return ""

	characters = []
	for word in option.split():
		if (match := CODE_POINT_PATTERN.fullmatch(word)) is None:
			characters.append(word)
		elif (codePoint := int(match[1], 16)) > 0x10ffff:
			raise ValueError(f"'{word}' is beyond the last code point U+10FFFF.")
		elif 0xd800 <= codePoint <= 0xdfff:
			raise ValueError(f"'{word}' is a surrogate code point, which is no character.")
		else:
			characters.append(chr(codePoint))

	return "".join(characters)


@export
def describedIcon(option: Nullable[str]) -> tuple[str, str]:
	"""
	Option converter reading an icon and the text explaining it in the tree's legend: ``<icon> | <text>``.

	The icon is read by :func:`icon`. The text follows a separator ``|`` between spaces - see :data:`SEPARATOR_PATTERN`
	-, and is inline ReST. An icon without a text has no item in the legend.

	:param option:      The option's value as it was written; ``None`` if the option has no value.
	:returns:           The icon's characters and the text; empty if the option has no value or no text.
	:raises ValueError: If the value has more than one separator ``|``.
	:raises ValueError: If the value has a text, but no icon.
	"""
	if option is None:
		return "", ""

	value = f" {option}"  # a separator at the start follows a space too
	separators = [match.start() for match in SEPARATOR_PATTERN.finditer(value) if match["separator"] is not None]
	if len(separators) > 1:
		raise ValueError(f"'{option.strip()}' has more than one separator ' | '; a '|' in a text is escaped as '\\|'.")
	elif len(separators) == 0:
		return icon(option), ""

	characters = icon(value[:separators[0]])
	text =       value[separators[0] + 1:].strip()
	if characters == "" and text != "":
		raise ValueError(f"'{option.strip()}' has a text, but no icon.")

	return characters, text


@export
class LegendPosition(StringEnum):
	"""
	Where a legend is drawn, as a directive's option ``:legend:`` states it.

	A tree's legend gets the CSS class ``tree-legend-<value>``, a unit test summary's legend
	``report-unittest-legend-<value>``.
	"""

	Top =    "top"     #: Above the tree or table.
	Bottom = "bottom"  #: Below the tree or table.
	Hidden = "none"    #: Not at all.

	DEFAULT = Bottom   #: An option without a value draws the legend below the tree or table.


@export
def markerIcons(option: Nullable[str]) -> dict[str, tuple[str, str]]:
	"""
	Option converter reading the markers an entry may start with, each with its icon and the text explaining it in the
	tree's legend: ``<marker> <icon>``, separated by commas, or ``<marker> <icon> | <text>``, one per line.

	A marker is one character, neither a letter, a digit, a comma nor a space. An icon and its text are read by
	:func:`describedIcon`. A line with a separator ``|`` holds one marker, so a text may contain commas; a line without
	one is split at its commas.

	:param option:      The option's value as it was written; ``None`` if the option has no value.
	:returns:           The icons and their texts, keyed by their marker, in the order declared.
	:raises ValueError: If an item isn't a marker followed by a space and an icon.
	:raises ValueError: If a marker is a letter, a digit or a comma.
	:raises ValueError: If a marker is declared twice.
	:raises ValueError: If an item has more than one separator ``|``.
	"""
	if option is None:
		return {}

	icons: dict[str, tuple[str, str]] = {}
	for line in option.splitlines():
		if any(match["separator"] is not None for match in SEPARATOR_PATTERN.finditer(line)):
			items = [line]
		else:
			items = line.split(",")

		for item in items:
			if (item := item.strip()) == "":
				continue

			marker =    item[0]
			separator = item[1:2]
			value =     item[2:]
			if separator.strip() != "" or value.strip() == "":
				raise ValueError(f"'{item}' is not a marker followed by a space and an icon.")
			elif marker.isalnum():
				raise ValueError(f"Marker '{marker}' is a letter or a digit.")
			elif marker in icons:
				raise ValueError(f"Marker '{marker}' is declared twice.")

			icons[marker] = describedIcon(value)

	return icons


@export
class Tree(BaseDirective):
	"""
	The ``tree`` directive: a hierarchy, written as an indented list, drawn as a tree.

	:meth:`_ParseEntries` reads the content into :class:`~pyTooling.Tree.Node` instances, one tree per root, and
	:meth:`_BuildItem` turns them into nested bullet lists of :class:`~pyTooling.Sphinx.Node.TreeItem` and
	:class:`~pyTooling.Sphinx.Node.TreeLabel`. The options choose the icons and how many levels are expanded initially;
	``:class:`` puts additional CSS classes on the tree. :meth:`_BuildLegend` turns the texts of the icons into the
	tree's legend, which ``:legend:`` places above or below the tree.

	If an entry has a description, every entry's text ends with a :class:`~pyTooling.Sphinx.Node.TreeDescription`, and
	:meth:`_ColumnWidth` estimates how wide the column of the texts in front of the descriptions is.
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
		"root-icon":       describedIcon,
		"node-icon":       describedIcon,
		"leaf-icon":       describedIcon,
		"expanded-icon":   icon,
		"collapsed-icon":  icon,
		"icons":           markerIcons,
		"legend":          LegendPosition.Parse,
		"expanded-levels": directives.nonnegative_int,
		"class":           strip,
	}

	def run(self) -> list[nodes.Node]:
		"""
		Draw the hierarchy written in the content, and the legend of its icons.

		Option ``:legend:`` without any icon having a text draws no legend, and is warned about.

		:returns: The tree as a bullet list with its legend above or below it, or the message of whatever the content or
		          the icons' texts got wrong.
		"""
		markers = self.options.get("icons", {})
		describedIcons = {
			name: self.options.get(name, (DEFAULT_ICONS[name], "")) for name in ("root-icon", "node-icon", "leaf-icon")
		}
		describedIcons.update(markers)
		position = self.options.get("legend", LegendPosition.DEFAULT)
		try:
			roots = self._ParseEntries(self.content, (DEFAULT_MARKER, *markers))
			legend, messages = self._BuildLegend(describedIcons.values(), position)
		except SphinxExtensionError as ex:
			return [self.state.document.reporter.error(f"{self.directiveName}: {ex}", line=self.lineno)]

		icons = {name: self.options.get(name, DEFAULT_ICONS[name]) for name in ("expanded-icon", "collapsed-icon")}
		icons.update((key, characters) for key, (characters, _) in describedIcons.items())
		expandedLevels = self.options.get("expanded-levels", None)
		descriptionColumn = any(entry["description"] != "" for root in roots for entry in root.IteratePreOrder())

		tree = nodes.bullet_list(classes=["pytooling-tree"] + self.options.get("class", "").split())
		for root in roots:
			tree += self._BuildItem(root, icons, expandedLevels, descriptionColumn)

		if descriptionColumn:
			columnWidth = self._ColumnWidth(tree.findall(TreeLabel))
			for item in tree.children:
				item["columnWidth"] = columnWidth

		if len(legend.children) == 0:
			if "legend" in self.options and position is not LegendPosition.Hidden:
				messages.append(self.state.document.reporter.warning(
					f"{self.directiveName}: ':legend: {position}' without an icon having a text draws no legend.",
					line=self.lineno
				))
			return [tree, *messages]
		elif position is LegendPosition.Top:
			return [legend, tree, *messages]
		elif position is LegendPosition.Bottom:
			return [tree, legend, *messages]
		else:
			return [tree, *messages]

	def _BuildLegend(
		self,
		describedIcons: Iterable[tuple[str, str]],
		position: LegendPosition
	) -> tuple[TreeLegend, list[nodes.system_message]]:
		"""
		Build the legend of the tree's icons: an item per icon with a text, in the order given.

		An icon given twice with the same text - e.g. a folder for a node and for a marker - is explained once. A text is
		parsed as inline ReST at the directive's line, as an option has no line of its own.

		:param describedIcons:        Each icon with its text; an icon with an empty text has no item.
		:param position:              Where the legend is drawn; the legend gets the CSS class ``tree-legend-<position>``.
		:returns:                     The legend - without items, if no icon has a text -, and the messages about the
		                              texts.
		:raises SphinxExtensionError: If an icon is given twice with different texts.
		"""
		texts: dict[str, str] = {}
		for characters, text in describedIcons:
			if text == "":
				continue
			elif characters not in texts:
				texts[characters] = text
			elif texts[characters] != text:
				raise SphinxExtensionError(f"Icon '{characters}' has two texts: '{texts[characters]}' and '{text}'.")

		legend = TreeLegend("", classes=["pytooling-tree-legend", f"tree-legend-{position}"])
		messages: list[nodes.system_message] = []
		for characters, text in texts.items():
			textNodes, textMessages = self.state.inline_text(text, self.lineno)
			legend += TreeLegendItem(text, "", *textNodes, icon=characters)
			messages.extend(textMessages)

		return legend, messages

	@staticmethod
	def _ParseEntries(content: Iterable[str], markers: Iterable[str] = (DEFAULT_MARKER, )) -> list[_Entry]:
		"""
		Read the content into trees: an entry per line, and an entry indented deeper than the one above is its child.

		An entry's text is the node's value. Key ``index`` holds the index of the entry's line in the content, key
		``marker`` the marker the line starts with, and key ``description`` the text behind a separator ``|`` - see
		:data:`SEPARATOR_PATTERN` -, or an empty string.

		:param content:               The directive's content, line by line.
		:param markers:               Optional, the markers an entry may start with. Default: ``-``.
		:returns:                     The root of each tree, in the order written.
		:raises SphinxExtensionError: If the content holds no entry.
		:raises SphinxExtensionError: If a line doesn't start with a marker and a space.
		:raises SphinxExtensionError: If a line has more than one separator ``|``.
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

			separators = [match.start() for match in SEPARATOR_PATTERN.finditer(text) if match["separator"] is not None]
			if len(separators) > 1:
				raise SphinxExtensionError(
					f"'{text.rstrip()}' has more than one separator ' | '; a '|' in a text is escaped as '\\|'."
				)
			elif len(separators) == 1:
				value, description = text[1:separators[0]].strip(), text[separators[0] + 1:].strip()
			else:
				value, description = text[1:].strip(), ""

			if value == "":
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
			entry: _Entry = Node(
				value=value, keyValuePairs={"index": index, "marker": marker, "description": description}, parent=parent
			)
			if parent is None:
				roots.append(entry)

			ancestors.append((indentation, entry))

		if len(roots) == 0:
			raise SphinxExtensionError("The directive's content holds no entry.")

		return roots

	def _BuildItem(
		self,
		entry: _Entry,
		icons: dict[str, str],
		expandedLevels: Nullable[int],
		descriptionColumn: bool
	) -> TreeItem:
		"""
		Build an entry and, below it, its children.

		The entry's text and description are parsed as inline ReST at the line they were written on, so a message about
		a role in them points to that line. Such messages follow the entry's text in the list item.

		:param entry:             The entry, as :meth:`_ParseEntries` read it.
		:param icons:             The icons, keyed by the option naming them, or by their marker.
		:param expandedLevels:    How many levels are expanded initially; ``None`` expands all.
		:param descriptionColumn: Whether the tree has descriptions: then the entry's text ends with a description, empty
		                          if the entry has none.
		:returns:                 The entry as a list item, holding its text and a bullet list of its children.
		"""
		line = self.content_offset + entry["index"] + 1
		textNodes, messages = self.state.inline_text(entry.Value, line)

		if entry.IsRoot:
			kind = "root"
		elif entry.HasChildren:
			kind = "node"
		else:
			kind = "leaf"

		entryIcon = icons[entry["marker"]] if entry["marker"] in icons else icons[f"{kind}-icon"]

		item = TreeItem("", classes=[f"tree-{kind}"] + (["tree-expandable"] if entry.HasChildren else []))
		item["columnWidth"] = None
		item += (label := TreeLabel(entry.Value, "", *textNodes, icon=entryIcon, level=entry.Level))
		if descriptionColumn:
			description = TreeDescription(entry["description"])
			if entry["description"] != "":
				descriptionNodes, descriptionMessages = self.state.inline_text(entry["description"], line)
				description += descriptionNodes
				messages += descriptionMessages
				label += TreeSeparator("", SEPARATOR)

			label += description

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
			children += self._BuildItem(child, icons, expandedLevels, descriptionColumn)

		return item

	@staticmethod
	def _ColumnWidth(labels: Iterable[TreeLabel]) -> str:
		"""
		Estimate the width of the column of the entries' texts in a tree with descriptions, from the tree's left edge.

		An entry needs its level's indentation, its expander, and its icon, a gap and its text. HTML renders the text
		later, in a font chosen by the theme, so the text's width is estimated in character cells, CSS unit ``ch``: two
		for a wide character, e.g. an emoji, none for a combining or format character, e.g. a variation selector, and
		one for every other character. The gap counts as one cell.

		The width is the widest entry's: per level, the indentation and the most cells at that level, and of these the
		maximum, computed by the browser with CSS function ``max()``. The indentation is CSS custom property
		``--pyTooling-tree-level``, so a project's indentation is accounted for.

		:param labels: The entries' texts, with their level, icon and description.
		:returns:      The width as a CSS length.
		"""
		cellsPerLevel: dict[int, int] = {}
		for label in labels:
			text = "".join(
				child.astext() for child in label.children if not isinstance(child, (TreeSeparator, TreeDescription))
			)
			if label["icon"] != "":
				text = f"{label['icon']} {text}"

			cells = sum(
				2 if east_asian_width(character) in ("W", "F") else 0 if category(character) in ("Mn", "Me", "Cf") else 1
				for character in text
			)
			cellsPerLevel[label["level"]] = max(cells, cellsPerLevel.get(label["level"], 0))

		widths = ", ".join(
			f"{cells}ch" if level == 0 else f"calc({level} * var(--pyTooling-tree-level) + {cells}ch)"
			for level, cells in sorted(cellsPerLevel.items())
		)
		return f"calc(var(--pyTooling-tree-expander-width) + max({widths}))"


@export
class RemoveTreeLegends(SphinxPostTransform):
	"""
	A post-transform removing the trees' legends from the output formats, whose trees show no icons: LaTeX, text,
	manual pages and Texinfo.

	These formats write a tree as a nested bullet list, so a legend would explain icons the reader doesn't see.
	"""

	default_priority = 200                                  #: Priority among the post-transforms.
	formats =          ("latex", "text", "man", "texinfo")  #: Output formats the transform runs for.

	def run(self, **kwargs: Any) -> None:
		"""
		Remove every legend of a tree.

		:param kwargs: Keyword arguments Sphinx passes to a post-transform; none is used.
		"""
		for legend in list(self.document.findall(TreeLegend)):
			legend.parent.remove(legend)
