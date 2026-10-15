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
A Sphinx directive listing Unicode characters with their names and code points.

The characters are icons, e.g. the ones a ``tree`` draws. An icon written as a character is hard to type, and written
as a code point hard to recognize. The ``unicode-table`` directive takes the icons as content, one per line, and
computes a row per icon: the icon, its Unicode name and its code points, in the form the icon options of the ``tree``
directive take them:

.. code-block:: ReST

   .. unicode-table::

      📦       | a package
      U+1F4C1  | a directory
      ⚙️       | settings

**An entry is a line holding an icon**, written as characters or as code points ``U+<hex>``, several words forming
one icon - e.g. ``U+2699 U+FE0F``. A ``|`` between spaces separates the icon from its description, which is inline
ReST.

.. rubric:: Names and code points

The names are Python's :mod:`unicodedata`'s, so a row can't contradict its icon. A sequence is named by its characters,
joined by ``+``; a variation selector and the zero width joiner select how the characters are drawn, and don't count:
``⚙️`` - ``U+2699 U+FE0F`` - is named ``GEAR``. A character without a name gets the label the Unicode standard gives
it, e.g. ``<private-use-E000>``. A code point not assigned in the Unicode version of :mod:`unicodedata` is warned about,
as its name is unknown.

.. rubric:: HTML and other formats

HTML writes a :class:`~pyTooling.Sphinx.Node.CopyButton` beside an icon and beside its code points, which copies them
into the clipboard; the script :file:`pyTooling.js` gives the buttons their function. Every other format finds no
visitor for :class:`~pyTooling.Sphinx.Node.CopyButton` and writes its base-class, an empty inline element. LaTeX
writes no icons, as pdfLaTeX stops at a character it has no definition for - which an emoji is - and LuaLaTeX needs
an emoji font: :class:`RemoveUnicodeGlyphs` removes the icons' column.

.. seealso::

   :ref:`DIR/UnicodeTable`
      |rarr| The directive's options, with rendered examples.
   :ref:`DIR/Tree/CommonIcons`
      |rarr| Icons commonly used in a tree, listed by this directive.
"""
from typing                            import Any, Iterable, NamedTuple, Optional as Nullable, Self
from unicodedata                       import category, name as unicodeName, unidata_version

from docutils                          import nodes
from sphinx.transforms.post_transforms import SphinxPostTransform

from pyTooling.Decorators              import export, readonly
from pyTooling.Sphinx                  import BaseDirective, SphinxExtensionError, strip
from pyTooling.Sphinx.Node             import CopyButton
from pyTooling.Sphinx.Tree             import SEPARATOR_PATTERN, icon


__all__ = ["TABLE_CLASS", "LABELS"]

#: The CSS class of every table the directive writes, by which :class:`RemoveUnicodeGlyphs` finds them.
TABLE_CLASS = "pytooling-unicode-table"

#: The labels of a code point without a name, by its general category, as the Unicode standard (section 4.8) forms
#: them: ``<label-XXXX>``.
#:
#: Category ``Cn`` is a reserved code point or a noncharacter, which :func:`codePointLabel` tells apart.
LABELS = {
	"Cc": "control",
	"Co": "private-use",
	"Cs": "surrogate",
	"Cn": "reserved",
}


@export
def isNoncharacter(character: str) -> bool:
	"""
	Check whether a character is one of the 66 noncharacters, which Unicode reserves for a program's internal use.

	The noncharacters are U+FDD0 to U+FDEF, and the last two code points of every plane, e.g. U+FFFE and U+FFFF.

	:param character: The character.
	:returns:         ``True`` if the character is a noncharacter.
	"""
	codePoint = ord(character)
	return 0xfdd0 <= codePoint <= 0xfdef or codePoint & 0xfffe == 0xfffe


@export
def isSelector(character: str) -> bool:
	"""
	Check whether a character selects how its neighbours are drawn, instead of being drawn itself.

	Such a character is a variation selector, e.g. U+FE0F selecting an emoji's colourful presentation, or the zero width
	joiner U+200D, which joins emoji into one, e.g. a man and a computer into a technologist.

	:param character: The character.
	:returns:         ``True`` if the character is a variation selector or the zero width joiner.
	"""
	codePoint = ord(character)
	return 0xfe00 <= codePoint <= 0xfe0f or 0xe0100 <= codePoint <= 0xe01ef or codePoint == 0x200d


@export
def codePointLabel(character: str) -> str:
	"""
	Return a character's name, or the label the Unicode standard gives a code point without a name.

	A label is ``<label-XXXX>``, e.g. ``<control-0009>``, ``<private-use-E000>``, ``<reserved-0378>`` or
	``<noncharacter-FFFF>``: the kind of the code point, and its hexadecimal value with at least four digits.

	:param character: The character.
	:returns:         The character's name, or its label.
	"""
	if (name := unicodeName(character, "")) != "":
		return name

	codeCategory = category(character)
	label = "noncharacter" if codeCategory == "Cn" and isNoncharacter(character) else LABELS[codeCategory]
	return f"<{label}-{ord(character):04X}>"


@export
class UnicodeEntry(NamedTuple):
	"""
	An entry of a ``unicode-table``: an icon's characters, and the description written behind it.

	:attr:`Name` and :attr:`CodePoints` are computed from the characters, so they can't contradict the icon.
	"""

	characters:  str  #: The icon's characters, e.g. a gear and variation selector 16.
	description: str  #: The description as inline ReST; empty if the entry has none.
	lineIndex:   int  #: Index of the entry's line in the directive's content.

	@classmethod
	def Parse(cls, line: str, lineIndex: int) -> Self:
		"""
		Read an entry from a line of the directive's content: an icon, and optionally a description behind a separator.

		The icon is read as the icon options of the ``tree`` directive read theirs - see
		:func:`~pyTooling.Sphinx.Tree.icon`: characters as written, and a word ``U+<hex>`` as the code point it names. The
		separator is a ``|`` between spaces - see :data:`~pyTooling.Sphinx.Tree.SEPARATOR_PATTERN`.

		:param line:                  The line, not blank.
		:param lineIndex:             Index of the line in the directive's content.
		:returns:                     The entry.
		:raises SphinxExtensionError: If the line has more than one separator ``|``.
		:raises SphinxExtensionError: If the line has a description, but no icon.
		:raises SphinxExtensionError: If a word names a code point beyond U+10FFFF, or a surrogate.
		"""
		text = f" {line.strip()}"  # a separator at the start follows a space too
		separators = [match.start() for match in SEPARATOR_PATTERN.finditer(text) if match["separator"] is not None]
		if len(separators) > 1:
			raise SphinxExtensionError(
				f"'{line.strip()}' has more than one separator ' | '; a '|' in a text is escaped as '\\|'."
			)
		elif len(separators) == 1:
			iconText =    text[:separators[0]]
			description = text[separators[0] + 1:].strip()
		else:
			iconText =    text
			description = ""

		try:
			characters = icon(iconText)
		except ValueError as ex:
			raise SphinxExtensionError(f"'{line.strip()}' has an invalid icon: {ex}") from ex

		if characters == "":
			raise SphinxExtensionError(f"'{line.strip()}' has a description, but no icon.")

		return cls(characters, description, lineIndex)

	@readonly
	def Name(self) -> str:
		"""
		Read-only property to return the icon's name: the names of its characters, joined by ``+``.

		Variation selectors and the zero width joiner select how the characters are drawn and aren't named, unless the
		icon consists of nothing else: ``U+2699 U+FE0F`` is named ``GEAR``. A character without a name contributes its
		label - see :func:`codePointLabel`.

		:returns: The name, e.g. ``GEAR`` or ``MAN + PERSONAL COMPUTER``.
		"""
		named = [character for character in self.characters if not isSelector(character)]
		return " + ".join(codePointLabel(character) for character in (named if len(named) > 0 else self.characters))

	@readonly
	def CodePoints(self) -> str:
		"""
		Read-only property to return the icon's code points, as the icon options of the ``tree`` directive take them.

		:returns: The code points ``U+<hex>`` with at least four digits, separated by spaces, e.g. ``U+2699 U+FE0F``.
		"""
		return " ".join(f"U+{ord(character):04X}" for character in self.characters)

	@readonly
	def UnassignedCharacters(self) -> list[str]:
		"""
		Read-only property to return the characters, which aren't assigned in the Unicode version of :mod:`unicodedata`.

		Such a character is a typo - or newer than the Python running the build: Python 3.12 knows Unicode 15.0. A
		noncharacter is no such character.

		:returns: The unassigned characters, in the order written.
		"""
		return [
			character for character in self.characters if category(character) == "Cn" and not isNoncharacter(character)
		]


@export
class UnicodeTable(BaseDirective):
	"""
	The ``unicode-table`` directive: a table of icons, each with its Unicode name and its code points.

	:meth:`_ParseContent` reads the content into :class:`UnicodeEntry` instances, and :meth:`run` turns them into a
	table: the icon, its name, its code points and - if an entry has one - its description. The icon and the code
	points each get a :class:`~pyTooling.Sphinx.Node.CopyButton`. ``:class:`` puts additional CSS classes on the table.
	"""

	directiveName: str = "unicode-table"  #: Name the directive is invoked by.

	has_content =               True   #: A boolean; ``True`` if content is allowed.
	required_arguments =        0      #: Number of required directive arguments.
	optional_arguments =        0      #: Number of optional arguments after the required ones.
	final_argument_whitespace = False  #: A boolean; ``True`` if the last argument may contain spaces.
	# docutils declares 'option_spec' on 'Directive' and 'BaseDirective' assigns it, so mypy calls every
	# spelling of this override a conflict with one of them
	#: Mapping of option names to validator functions.
	option_spec: dict[str, Any] = {  # type: ignore[misc]
		"class": strip,
	}

	def run(self) -> list[nodes.Node]:
		"""
		Write the table of the icons listed in the content.

		An icon with a character, which isn't assigned in the Unicode version of :mod:`unicodedata`, is warned about at
		its line, and still gets its row.

		:returns: The table, followed by the messages about the descriptions and the unassigned characters, or the message
		          of whatever the content got wrong.
		"""
		try:
			entries = self._ParseContent(self.content)
		except SphinxExtensionError as ex:
			return [self.state.document.reporter.error(f"{self.directiveName}: {ex}", line=self.lineno)]

		withDescriptions = any(entry.description != "" for entry in entries)
		columns: list[tuple[str, Nullable[int]]] = [("Icon", 10), ("Name", 45), ("Code points", 25)]
		if withDescriptions:
			columns.append(("Description", 40))

		classes = [TABLE_CLASS] + self.options.get("class", "").split()
		tableGroup = self._CreateSingleRowTableHeader(columns, TABLE_CLASS, classes)
		tableGroup += (tableBody := nodes.tbody())

		messages: list[nodes.system_message] = []
		for entry in entries:
			line = self.content_offset + entry.lineIndex + 1
			if len(unassigned := entry.UnassignedCharacters) > 0:
				codePoints = ", ".join(f"U+{ord(character):04X}" for character in unassigned)
				messages.append(self.state.document.reporter.warning(
					f"{self.directiveName}: {codePoints} isn't assigned in Unicode {unidata_version}, which Python's "
					f"'unicodedata' knows; its name is unknown.",
					line=line
				))

			name = entry.Name
			tableBody += (row := nodes.row())
			row += nodes.entry("", nodes.paragraph(
				"", "",
				nodes.inline(entry.characters, entry.characters, classes=["unicode-glyph"]),
				CopyButton("", copy=entry.characters, label=f"Copy the icon {name}")
			))
			row += nodes.entry("", nodes.paragraph(name, name))
			row += nodes.entry("", nodes.paragraph(
				"", "",
				nodes.literal(entry.CodePoints, entry.CodePoints),
				CopyButton("", copy=entry.CodePoints, label=f"Copy the code points of {name}")
			))
			if withDescriptions:
				descriptionNodes, descriptionMessages = self.state.inline_text(entry.description, line)
				row += nodes.entry("", nodes.paragraph(entry.description, "", *descriptionNodes))
				messages.extend(descriptionMessages)

		return [tableGroup.parent, *messages]

	@staticmethod
	def _ParseContent(content: Iterable[str]) -> list[UnicodeEntry]:
		"""
		Read the content into entries: an entry per line, blank lines skipped.

		:param content:               The directive's content, line by line.
		:returns:                     The entries, in the order written.
		:raises SphinxExtensionError: If the content holds no entry.
		:raises SphinxExtensionError: If a line isn't an entry - see :meth:`UnicodeEntry.Parse`.
		"""
		entries = [UnicodeEntry.Parse(line, index) for index, line in enumerate(content) if line.strip() != ""]
		if len(entries) == 0:
			raise SphinxExtensionError("The directive's content holds no entry.")

		return entries


@export
class RemoveUnicodeGlyphs(SphinxPostTransform):
	"""
	A post-transform removing the icons' column from the tables of the ``unicode-table`` directive in LaTeX.

	pdfLaTeX stops at a character it has no definition for - which an emoji is -, and LuaLaTeX needs an emoji font to
	draw one. The names and the code points identify the icons without it.
	"""

	default_priority = 200          #: Priority among the post-transforms.
	formats =          ("latex", )  #: Output formats the transform runs for.

	def run(self, **kwargs: Any) -> None:
		"""
		Remove the first column - the icons' - of every table of the ``unicode-table`` directive.

		:param kwargs: Keyword arguments Sphinx passes to a post-transform; none is used.
		"""
		for table in list(self.document.findall(nodes.table)):
			if TABLE_CLASS not in table["classes"]:
				continue

			tableGroup = table.next_node(nodes.tgroup)
			tableGroup["cols"] -= 1
			tableGroup.remove(tableGroup.next_node(nodes.colspec))
			for row in list(tableGroup.findall(nodes.row)):
				row.remove(row[0])
