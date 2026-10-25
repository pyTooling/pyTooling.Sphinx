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

from pyTooling.Common                  import StringEnum, getFullyQualifiedName
from pyTooling.Decorators              import export, readonly
from pyTooling.MetaClasses             import ExtendedType
from pyTooling.Sphinx                  import BaseDirective, SphinxExtensionError, strip
from pyTooling.Sphinx.Node             import CopyButton
from pyTooling.Sphinx.Tree             import SEPARATOR_PATTERN, icon


__all__ = ["TABLE_CLASS"]

TABLE_CLASS = "pytooling-unicode-table"
"""The CSS class of every table the directive writes, by which :class:`RemoveUnicodeGlyphs` finds them."""


@export
class CodePointType(StringEnum):
	"""
	The type of a code point, as the Unicode standard (section 2.4, table 2-3) defines it.

	A code point without a name is labelled by its type (section 4.8): ``<control-0009>``. A letter, a symbol or a format
	character has a name.
	"""

	Graphic =      "graphic"       #: A letter, mark, number, punctuation, symbol or space.
	Format =       "format"        #: An invisible character affecting its neighbours, or a line or paragraph separator.
	Control =      "control"       #: A control character, e.g. a tab.
	PrivateUse =   "private-use"   #: A character assigned by a private agreement, not by Unicode.
	Surrogate =    "surrogate"     #: Half of a UTF-16 surrogate pair, never a character of its own.
	Noncharacter = "noncharacter"  #: Reserved for a program's internal use; one of the 66 noncharacters.
	Reserved =     "reserved"      #: Not assigned in the Unicode version of :mod:`unicodedata`.


@export
class CodePoint(metaclass=ExtendedType, slots=True):
	"""
	A Unicode code point: its value, and what :mod:`unicodedata` knows about it - its general category, its type and its
	name.

	A code point is written in the standard's notation ``U+<hex>`` with at least four digits, e.g. ``U+2699``
	(:attr:`Notation`). :func:`str` returns its character.
	"""

	_value:     int  #: The code point's value, in range 0 to 0x10FFFF.
	_character: str  #: The code point's character.

	def __init__(self, value: int) -> None:
		"""
		Initializes a code point by its value.

		:param value:       The code point's value.
		:raises ValueError: If parameter ``value`` is ``None``.
		:raises TypeError:  If parameter ``value`` isn't of type :class:`int`.
		:raises ValueError: If parameter ``value`` is out of range 0 to 0x10FFFF.
		"""
		if value is None:
			raise ValueError("Parameter 'value' is None.")
		elif not isinstance(value, int):
			ex = TypeError("Parameter 'value' is not of type 'int'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(value)}'.")
			raise ex
		elif not 0 <= value <= 0x10ffff:
			ex = ValueError("Parameter 'value' is out of range 0 to 0x10FFFF.")
			ex.add_note(f"Got value '{value:#x}'.")
			raise ex

		self._value =     value
		self._character = chr(value)

	@classmethod
	def FromCharacter(cls, character: str) -> Self:
		"""
		Create the code point of a character.

		:param character:   The character.
		:returns:           The character's code point.
		:raises ValueError: If parameter ``character`` is ``None``.
		:raises TypeError:  If parameter ``character`` isn't of type :class:`str`.
		:raises ValueError: If parameter ``character`` isn't a single character.
		"""
		if character is None:
			raise ValueError("Parameter 'character' is None.")
		elif not isinstance(character, str):
			ex = TypeError("Parameter 'character' is not of type 'str'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(character)}'.")
			raise ex
		elif len(character) != 1:
			ex = ValueError("Parameter 'character' isn't a single character.")
			ex.add_note(f"Got {len(character)} characters.")
			raise ex

		return cls(ord(character))

	@readonly
	def Value(self) -> int:
		"""
		Read-only property to access the code point's value (:attr:`_value`).

		:returns: The value.
		"""
		return self._value

	@readonly
	def Character(self) -> str:
		"""
		Read-only property to access the code point's character (:attr:`_character`).

		:returns: The character.
		"""
		return self._character

	@readonly
	def Category(self) -> str:
		"""
		Read-only property to return the code point's general category, as :mod:`unicodedata` knows it.

		:returns: The general category's abbreviation, e.g. ``Lu`` for an uppercase letter or ``Cn`` for an unassigned
		          code point.
		"""
		return category(self._character)

	@readonly
	def Type(self) -> CodePointType:
		"""
		Read-only property to return the code point's type, derived from its general category.

		A code point of category ``Cn`` is a noncharacter or reserved.

		:returns: The type.
		"""
		match category(self._character):
			case "Cn":
				return CodePointType.Noncharacter if self.IsNoncharacter else CodePointType.Reserved
			case "Cc":
				return CodePointType.Control
			case "Co":
				return CodePointType.PrivateUse
			case "Cs":
				return CodePointType.Surrogate
			case "Cf" | "Zl" | "Zp":
				return CodePointType.Format
			case _:
				return CodePointType.Graphic

	@readonly
	def Name(self) -> str:
		"""
		Read-only property to return the code point's name, or the label the Unicode standard gives a code point without
		a name.

		A label is ``<type-XXXX>``, e.g. ``<control-0009>``, ``<private-use-E000>``, ``<reserved-0378>`` or
		``<noncharacter-FFFF>``: the code point's :attr:`Type`, and its hexadecimal value with at least four digits.

		:returns: The name, or the label.
		"""
		if (name := unicodeName(self._character, "")) != "":
			return name

		return f"<{self.Type}-{self._value:04X}>"

	@readonly
	def IsAssigned(self) -> bool:
		"""
		Read-only property to return whether the code point is assigned in the Unicode version of :mod:`unicodedata`.

		A noncharacter is assigned: Unicode reserves it permanently.

		:returns: ``True``, if the code point isn't reserved.
		"""
		return self.Type is not CodePointType.Reserved

	@readonly
	def IsNoncharacter(self) -> bool:
		"""
		Read-only property to return whether the code point is one of the 66 noncharacters, which Unicode reserves for a
		program's internal use.

		The noncharacters are U+FDD0 to U+FDEF, and the last two code points of every plane, e.g. U+FFFE and U+FFFF.

		:returns: ``True``, if the code point is a noncharacter.
		"""
		return 0xfdd0 <= self._value <= 0xfdef or self._value & 0xfffe == 0xfffe

	@readonly
	def IsSelector(self) -> bool:
		"""
		Read-only property to return whether the code point selects how its neighbours are drawn, instead of being drawn
		itself.

		Such a code point is a variation selector, e.g. U+FE0F selecting an emoji's colourful presentation, or the zero
		width joiner U+200D, which joins emoji into one, e.g. a man and a computer into a technologist.

		:returns: ``True``, if the code point is a variation selector or the zero width joiner.
		"""
		return 0xfe00 <= self._value <= 0xfe0f or 0xe0100 <= self._value <= 0xe01ef or self._value == 0x200d

	@readonly
	def Notation(self) -> str:
		"""
		Read-only property to return the code point in the standard's notation: ``U+<hex>`` with at least four digits.

		:returns: The code point, e.g. ``U+2699``.
		"""
		return f"U+{self._value:04X}"

	def __str__(self) -> str:
		"""
		Return the code point's character.

		:returns: The character, e.g. ``⚙``.
		"""
		return self._character

	def __repr__(self) -> str:
		"""
		Return a representation of the code point for debugging.

		:returns: The code point and its name, e.g. ``<CodePoint U+2699 GEAR>``.
		"""
		return f"<CodePoint {self.Notation} {self.Name}>"


@export
class UnicodeEntry(NamedTuple):
	"""
	An entry of a ``unicode-table``: an icon's characters, and the description written behind it.

	:attr:`Name` and :attr:`CodePointText` are computed from the characters, so they can't contradict the icon.
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
	def CodePoints(self) -> list[CodePoint]:
		"""
		Read-only property to return the code points of the icon's characters.

		:returns: The code points, in the order written.
		"""
		return [CodePoint.FromCharacter(character) for character in self.characters]

	@readonly
	def Name(self) -> str:
		"""
		Read-only property to return the icon's name: the names of its characters, joined by ``+``.

		Variation selectors and the zero width joiner select how the characters are drawn and aren't named, unless the
		icon consists of nothing else: ``U+2699 U+FE0F`` is named ``GEAR``. A character without a name contributes its
		label - see :attr:`CodePoint.Name`.

		:returns: The name, e.g. ``GEAR`` or ``MAN + PERSONAL COMPUTER``.
		"""
		codePoints = self.CodePoints
		named = [codePoint for codePoint in codePoints if not codePoint.IsSelector]
		return " + ".join(codePoint.Name for codePoint in (named if len(named) > 0 else codePoints))

	@readonly
	def CodePointText(self) -> str:
		"""
		Read-only property to return the icon's code points, as the icon options of the ``tree`` directive take them.

		:returns: The code points ``U+<hex>`` with at least four digits, separated by spaces, e.g. ``U+2699 U+FE0F``.
		"""
		return " ".join(codePoint.Notation for codePoint in self.CodePoints)

	@readonly
	def UnassignedCodePoints(self) -> list[CodePoint]:
		"""
		Read-only property to return the code points, which aren't assigned in the Unicode version of :mod:`unicodedata`.

		Such a code point is a typo - or newer than the Python running the build: Python 3.12 knows Unicode 15.0.

		:returns: The unassigned code points, in the order written.
		"""
		return [codePoint for codePoint in self.CodePoints if not codePoint.IsAssigned]


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
			if len(unassigned := entry.UnassignedCodePoints) > 0:
				codePoints = ", ".join(codePoint.Notation for codePoint in unassigned)
				messages.append(self.state.document.reporter.warning(
					f"{self.directiveName}: {codePoints} isn't assigned in Unicode {unidata_version}, which Python's "
					f"'unicodedata' knows; its name is unknown.",
					line=line
				))

			name =          entry.Name
			codePointText = entry.CodePointText
			tableBody += (row := nodes.row())
			row += nodes.entry("", nodes.paragraph(
				"", "",
				nodes.inline(entry.characters, entry.characters, classes=["unicode-glyph"]),
				CopyButton("", copy=entry.characters, label=f"Copy the icon {name}")
			))
			row += nodes.entry("", nodes.paragraph(name, name))
			row += nodes.entry("", nodes.paragraph(
				"", "",
				nodes.literal(codePointText, codePointText),
				CopyButton("", copy=codePointText, label=f"Copy the code points of {name}")
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
