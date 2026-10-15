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
Unit tests for :mod:`pyTooling.Sphinx.UnicodeTable`: reading the directive's content, and the names and code points
computed for an icon.
"""
from pyTooling.Sphinx              import SphinxExtensionError
from pyTooling.Sphinx.UnicodeTable import CodePoint, CodePointType, UnicodeEntry, UnicodeTable
from pyTooling.Testing             import Testcase, testsuite, testcase


if __name__ == "__main__":  # pragma: no cover
	print("ERROR: you called a testcase declaration file as an executable module.")
	print("Use: 'python -m unittest <testcase module>'")
	exit(1)


@testsuite("Unicode table content")
class UnicodeTableContent(Testcase):
	"""The directive's content: an icon per line, as characters or code points, optionally with a description."""

	@testcase("Characters")
	def Characters(self) -> None:
		"""
		An icon written as characters is used as written.

		Parses a package emoji and checks its characters, the empty description and the line's index.
		"""
		entry = UnicodeEntry.Parse("\U0001f4e6", 3)

		self.assertEqual("\U0001f4e6", entry.characters)
		self.assertEqual("", entry.description)
		self.assertEqual(3, entry.lineIndex)

	@testcase("Code points")
	def CodePoints(self) -> None:
		"""
		A word 'U+<hex>' is the code point it names, in upper or lower case.

		Parses 'U+1F4C1' and 'u+1f4c1', and checks the folder emoji.
		"""
		self.assertEqual("\U0001f4c1", UnicodeEntry.Parse("U+1F4C1", 0).characters)
		self.assertEqual("\U0001f4c1", UnicodeEntry.Parse("U+1f4c1", 0).characters)

	@testcase("Sequence")
	def Sequence(self) -> None:
		"""
		Several words form one icon; characters and code points may be mixed.

		Parses the gear with variation selector 16 written as code points and as a character followed by a code point,
		and checks both are the same two characters.
		"""
		self.assertEqual("\u2699\ufe0f", UnicodeEntry.Parse("U+2699 U+FE0F", 0).characters)
		self.assertEqual("\u2699\ufe0f", UnicodeEntry.Parse("\u2699 U+FE0F", 0).characters)

	@testcase("Description")
	def Description(self) -> None:
		"""
		A '|' between spaces separates the icon from its description; spaces around both are dropped.

		Parses an icon with a description aligned by spaces, and one whose description holds a '|' in a literal.
		"""
		entry = UnicodeEntry.Parse("  U+1F40D    |   a Python *module*  ", 0)
		self.assertEqual("\U0001f40d", entry.characters)
		self.assertEqual("a Python *module*", entry.description)

		self.assertEqual("``int | None``", UnicodeEntry.Parse("\U0001f4c4 | ``int | None``", 0).description)

	@testcase("Lines")
	def Lines(self) -> None:
		"""
		Every line not blank is an entry, which remembers its line's index.

		Parses three lines with a blank one between, and checks the characters and indices.
		"""
		entries = UnicodeTable._ParseContent(["\U0001f4e6 | package", "", "U+1F4C1"])

		self.assertEqual([("\U0001f4e6", 0), ("\U0001f4c1", 2)], [(entry.characters, entry.lineIndex) for entry in entries])

	@testcase("Empty content")
	def Empty(self) -> None:
		"""
		Content without an entry is rejected.

		Parses an empty and a blank line and checks the message.
		"""
		with self.assertRaises(SphinxExtensionError) as context:
			UnicodeTable._ParseContent(["", "  "])

		self.assertEqual("The directive's content holds no entry.", str(context.exception))

	@testcase("Beyond Unicode")
	def BeyondUnicode(self) -> None:
		"""
		A code point beyond U+10FFFF is rejected.

		Parses 'U+110000' and checks the message names the line and the reason.
		"""
		with self.assertRaises(SphinxExtensionError) as context:
			UnicodeEntry.Parse("U+110000 | too far", 0)

		self.assertEqual(
			"'U+110000 | too far' has an invalid icon: 'U+110000' is beyond the last code point U+10FFFF.",
			str(context.exception)
		)

	@testcase("Surrogate")
	def Surrogate(self) -> None:
		"""
		A surrogate code point is no character, and is rejected.

		Parses 'U+D800' and checks the message.
		"""
		with self.assertRaises(SphinxExtensionError) as context:
			UnicodeEntry.Parse("U+D800", 0)

		self.assertEqual(
			"'U+D800' has an invalid icon: 'U+D800' is a surrogate code point, which is no character.",
			str(context.exception)
		)

	@testcase("Description without icon")
	def NoIcon(self) -> None:
		"""
		A description needs an icon.

		Parses a line starting with the separator and checks the message.
		"""
		with self.assertRaises(SphinxExtensionError) as context:
			UnicodeEntry.Parse("| a package", 0)

		self.assertEqual("'| a package' has a description, but no icon.", str(context.exception))

	@testcase("Two separators")
	def Separators(self) -> None:
		"""
		A line has at most one separator.

		Parses a line with two separators and checks the message.
		"""
		with self.assertRaises(SphinxExtensionError) as context:
			UnicodeEntry.Parse("\U0001f4e6 | a | b", 0)

		self.assertEqual(
			"'\U0001f4e6 | a | b' has more than one separator ' | '; a '|' in a text is escaped as '\\|'.",
			str(context.exception)
		)


@testsuite("Unicode names and code points")
class UnicodeNames(Testcase):
	"""The name and code points computed for an icon."""

	@testcase("Character")
	def Character(self) -> None:
		"""
		A single character is named as Python's 'unicodedata' names it; its code point has at least four digits.

		Checks the package emoji and the black right-pointing small triangle.
		"""
		package = UnicodeEntry("\U0001f4e6", "", 0)
		self.assertEqual("PACKAGE", package.Name)
		self.assertEqual("U+1F4E6", package.CodePointText)

		triangle = UnicodeEntry("\u25b8", "", 0)
		self.assertEqual("BLACK RIGHT-POINTING SMALL TRIANGLE", triangle.Name)
		self.assertEqual("U+25B8", triangle.CodePointText)

	@testcase("Variation selector")
	def VariationSelector(self) -> None:
		"""
		A sequence of a character and a variation selector is named by the character, and lists both code points.

		Checks the gear with variation selector 16.
		"""
		gear = UnicodeEntry("\u2699\ufe0f", "", 0)

		self.assertEqual("GEAR", gear.Name)
		self.assertEqual("U+2699 U+FE0F", gear.CodePointText)

	@testcase("Joined sequence")
	def Joiner(self) -> None:
		"""
		A sequence joined by the zero width joiner is named by its characters, joined by '+'.

		Checks the technologist: a man, the joiner and a personal computer.
		"""
		technologist = UnicodeEntry("\U0001f468\u200d\U0001f4bb", "", 0)

		self.assertEqual("MAN + PERSONAL COMPUTER", technologist.Name)
		self.assertEqual("U+1F468 U+200D U+1F4BB", technologist.CodePointText)

	@testcase("Selector alone")
	def SelectorOnly(self) -> None:
		"""
		An icon of nothing but a selector is named by the selector.

		Checks variation selector 16 alone.
		"""
		self.assertEqual("VARIATION SELECTOR-16", UnicodeEntry("\ufe0f", "", 0).Name)

	@testcase("Unassigned character")
	def Unassigned(self) -> None:
		"""
		A code point without a character has no name, but the label 'reserved', and is listed as unassigned.

		Checks U+0378, unassigned in every Unicode version Python 3.12 to 3.15 knows.
		"""
		entry = UnicodeEntry("\u0378", "", 0)

		self.assertEqual("<reserved-0378>", entry.Name)
		self.assertEqual(["U+0378"], [codePoint.Notation for codePoint in entry.UnassignedCodePoints])

	@testcase("Characters without a name")
	def Labels(self) -> None:
		"""
		A control character, a private-use character and a noncharacter have no name, but a label; none of them is
		unassigned.

		Checks the label and the unassigned characters of a tab, U+E000 and U+FFFF.
		"""
		labels = {
			"\t":     "<control-0009>",
			"\ue000": "<private-use-E000>",
			"\uffff": "<noncharacter-FFFF>",
		}
		for character, label in labels.items():
			with self.subTest(label=label):
				entry = UnicodeEntry(character, "", 0)
				self.assertEqual(label, entry.Name)
				self.assertEqual([], entry.UnassignedCodePoints)


@testsuite("Code points")
class CodePoints(Testcase):
	"""A code point: its value, character, type and name."""

	@testcase("Value and character")
	def ValueAndCharacter(self) -> None:
		"""
		A code point created from a character has the character's value; its notation is 'U+<hex>', four digits or more.

		Checks the gear and the package emoji.
		"""
		gear = CodePoint.FromCharacter("\u2699")
		self.assertEqual(0x2699, gear.Value)
		self.assertEqual("\u2699", gear.Character)
		self.assertEqual("U+2699", gear.Notation)
		self.assertEqual("\u2699", str(gear))
		self.assertEqual("U+1F4E6", CodePoint(0x1f4e6).Notation)

	@testcase("Invalid values")
	def InvalidValues(self) -> None:
		"""
		A value of no code point, or a text, which isn't a single character, is rejected.

		Checks None, a string, a negative value, a value beyond U+10FFFF, and texts of zero and two characters.
		"""
		with self.assertRaises(ValueError):
			CodePoint(None)

		with self.assertRaises(TypeError):
			CodePoint("A")

		with self.assertRaises(ValueError):
			CodePoint(-1)

		with self.assertRaises(ValueError):
			CodePoint(0x110000)

		with self.assertRaises(ValueError):
			CodePoint.FromCharacter("")

		with self.assertRaises(ValueError):
			CodePoint.FromCharacter("AB")

	@testcase("Types")
	def Types(self) -> None:
		"""
		A code point's type is derived from its general category; a noncharacter is told apart from a reserved code point.

		Checks a code point of every type.
		"""
		types = {
			0x0041: CodePointType.Graphic,
			0x0020: CodePointType.Graphic,
			0x200d: CodePointType.Format,
			0x2028: CodePointType.Format,
			0x0009: CodePointType.Control,
			0xe000: CodePointType.PrivateUse,
			0xd800: CodePointType.Surrogate,
			0xffff: CodePointType.Noncharacter,
			0x0378: CodePointType.Reserved,
		}
		for value, codePointType in types.items():
			with self.subTest(codePoint=f"U+{value:04X}"):
				self.assertIs(codePointType, CodePoint(value).Type)
				self.assertEqual(codePointType is not CodePointType.Reserved, CodePoint(value).IsAssigned)

	@testcase("Names and labels")
	def Names(self) -> None:
		"""
		A code point with a name is named; every other one gets a label of its type.

		Checks a letter, a surrogate and a noncharacter of plane 1.
		"""
		self.assertEqual("LATIN CAPITAL LETTER A", CodePoint(0x41).Name)
		self.assertEqual("<surrogate-D800>", CodePoint(0xd800).Name)
		self.assertEqual("<noncharacter-1FFFE>", CodePoint(0x1fffe).Name)

	@testcase("Noncharacters")
	def Noncharacters(self) -> None:
		"""
		The noncharacters are U+FDD0 to U+FDEF, and the last two code points of every plane.

		Checks the bounds of the range and of a plane, and their neighbours.
		"""
		for value in (0xfdd0, 0xfdef, 0xfffe, 0xffff, 0x10fffe, 0x10ffff):
			with self.subTest(codePoint=f"U+{value:04X}"):
				self.assertTrue(CodePoint(value).IsNoncharacter)

		for value in (0xfdcf, 0xfdf0, 0xfffd, 0x10000):
			with self.subTest(codePoint=f"U+{value:04X}"):
				self.assertFalse(CodePoint(value).IsNoncharacter)

	@testcase("Selectors")
	def Selectors(self) -> None:
		"""
		The variation selectors and the zero width joiner are selectors; the zero width non-joiner is none.

		Checks the bounds of both ranges of variation selectors, the joiner and the non-joiner.
		"""
		for value in (0xfe00, 0xfe0f, 0xe0100, 0xe01ef, 0x200d):
			with self.subTest(codePoint=f"U+{value:04X}"):
				self.assertTrue(CodePoint(value).IsSelector)

		for value in (0x200c, 0xfe10, 0xe01f0):
			with self.subTest(codePoint=f"U+{value:04X}"):
				self.assertFalse(CodePoint(value).IsSelector)
