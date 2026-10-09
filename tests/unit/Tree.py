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
Unit tests for :mod:`pyTooling.Sphinx.Tree`: reading the directive's content, its descriptions, and its icon options.
"""
from pyTooling.Sphinx      import SphinxExtensionError
from pyTooling.Sphinx.Tree import Tree, icon, markerIcons
from pyTooling.Testing     import Testcase, testsuite, testcase


if __name__ == "__main__":  # pragma: no cover
	print("ERROR: you called a testcase declaration file as an executable module.")
	print("Use: 'python -m unittest <testcase module>'")
	exit(1)


@testsuite("Tree content")
class TreeContent(Testcase):
	"""The directive's content: an entry per line, an entry indented deeper being a child."""

	@testcase("Hierarchy")
	def Hierarchy(self) -> None:
		"""
		An entry indented deeper than the one above is its child; an entry indented alike is its sibling.

		Parses a root with a node and a leaf below it and checks values, parents and levels.
		"""
		roots = Tree._ParseEntries(["- root", "  - node", "    - leaf", "  - sibling"])

		self.assertEqual(1, len(roots))
		root = roots[0]
		self.assertEqual("root", root.Value)
		self.assertEqual(["node", "sibling"], [child.Value for child in root.GetChildren()])
		leaf = next(next(root.GetChildren()).GetChildren())
		self.assertEqual("leaf", leaf.Value)
		self.assertEqual(2, leaf.Level)

	@testcase("Several roots")
	def Roots(self) -> None:
		"""
		Every entry without a parent is a root of its own tree.

		Parses two roots, the first with a child, and checks both are returned in the order written.
		"""
		roots = Tree._ParseEntries(["- first", "  - child", "- second"])

		self.assertEqual(["first", "second"], [root.Value for root in roots])
		self.assertTrue(roots[1].IsRoot)

	@testcase("Indentation depth")
	def Indentation(self) -> None:
		"""
		How deep a child is indented doesn't matter.

		Parses children indented by four spaces below a root indented by two, and checks both are children.
		"""
		roots = Tree._ParseEntries(["  - root", "      - first", "      - second"])

		self.assertEqual(["first", "second"], [child.Value for child in roots[0].GetChildren()])

	@testcase("Line index and blank lines")
	def Index(self) -> None:
		"""
		Blank lines are skipped, and each entry remembers its line's index in the content.

		Parses two entries separated by a blank line and checks the indices 0 and 2.
		"""
		roots = Tree._ParseEntries(["- root", "", "  - child"])

		self.assertEqual(0, roots[0]["index"])
		self.assertEqual(2, next(roots[0].GetChildren())["index"])

	@testcase("Markers")
	def Markers(self) -> None:
		"""
		An entry starts with one of the given markers, which it remembers.

		Parses a root marked '-' with children marked '>' and '*', and checks each entry's marker.
		"""
		roots = Tree._ParseEntries(["- root", "  > directory", "  * file"], ("-", ">", "*"))

		self.assertEqual("-", roots[0]["marker"])
		self.assertEqual(
			[(">", "directory"), ("*", "file")],
			[(child["marker"], child.Value) for child in roots[0].GetChildren()]
		)

	@testcase("Text ending in a colon")
	def Colon(self) -> None:
		"""
		A colon at the end of an entry's text is part of the text.

		Parses an entry ending in a colon and checks its value.
		"""
		self.assertEqual("Note:", Tree._ParseEntries(["- Note:"])[0].Value)

	@testcase("Empty content")
	def Empty(self) -> None:
		"""
		Content without an entry is rejected.

		Parses an empty and a blank line and checks the message.
		"""
		with self.assertRaises(SphinxExtensionError) as context:
			Tree._ParseEntries(["", "  "])

		self.assertEqual("The directive's content holds no entry.", str(context.exception))

	@testcase("Not an entry")
	def NotAnEntry(self) -> None:
		"""
		A line not starting with '- ' is rejected.

		Parses a line without a dash, one with a dash but no space, and one with an undeclared marker, and checks the
		message names the declared markers.
		"""
		for line in ("pyTooling", "-pyTooling", "* pyTooling"):
			with self.subTest(line=line), self.assertRaises(SphinxExtensionError) as context:
				Tree._ParseEntries([line], ("-", ">"))

			self.assertEqual(f"'{line}' is not an entry, which starts with '- ', '> '.", str(context.exception))

	@testcase("Entry without text")
	def NoText(self) -> None:
		"""
		An entry needs a text; a trailing colon alone isn't one.

		Parses a dash alone and a dash followed by spaces, and checks the message.
		"""
		for line in ("-", "-   "):
			with self.subTest(line=line), self.assertRaises(SphinxExtensionError) as context:
				Tree._ParseEntries([line])

			self.assertEqual(f"'{line.rstrip()}' is an entry without text.", str(context.exception))

	@testcase("Mismatching indentation")
	def Indentation_Mismatch(self) -> None:
		"""
		An entry indented less than the entry above has to be indented like one of its ancestors.

		Parses a child indented by four spaces followed by a sibling indented by two, and checks the message.
		"""
		with self.assertRaises(SphinxExtensionError) as context:
			Tree._ParseEntries(["- a", "    - b", "  - c"])

		self.assertEqual(
			"'- c' is indented less than the entry above, but not as deep as one of its ancestors.",
			str(context.exception)
		)


@testsuite("Tree descriptions")
class TreeDescriptions(Testcase):
	"""An entry's description: the text behind a '|' between spaces."""

	@testcase("Description")
	def Description(self) -> None:
		"""
		A '|' between spaces separates the entry's text from its description; spaces around both are dropped.

		Parses an entry with a description aligned by spaces and checks text and description.
		"""
		entry = Tree._ParseEntries(["- Directory      |   e.g. ``myPackage/``  "])[0]

		self.assertEqual("Directory", entry.Value)
		self.assertEqual("e.g. ``myPackage/``", entry["description"])

	@testcase("Without description")
	def NoDescription(self) -> None:
		"""
		An entry without a separator has an empty description.

		Parses an entry without a separator and checks its description is empty.
		"""
		self.assertEqual("", Tree._ParseEntries(["- Directory"])[0]["description"])

	@testcase("Empty description")
	def EmptyDescription(self) -> None:
		"""
		A separator at the line's end leaves the description empty, as if there were none.

		Parses an entry ending in a separator, with and without trailing spaces, and checks text and description.
		"""
		for line in ("- Directory |", "- Directory |   "):
			with self.subTest(line=line):
				entry = Tree._ParseEntries([line])[0]

				self.assertEqual("Directory", entry.Value)
				self.assertEqual("", entry["description"])

	@testcase("Not a separator")
	def NotASeparator(self) -> None:
		"""
		A '|' in a literal, in interpreted text, escaped, or delimiting a substitution reference separates nothing.

		Parses lines whose text contains a '|' that isn't a separator, some followed by a separator, and checks text and
		description.
		"""
		for line, text, description in (
			("- ``int | None``",                 "``int | None``",                 ""),
			("- ``int | None`` | type",          "``int | None``",                 "type"),
			("- :code:`a | b` | code",           ":code:`a | b`",                  "code"),
			("- `a | b <https://example.org>`_", "`a | b <https://example.org>`_", ""),
			("- a \\| b",                        "a \\| b",                        ""),
			("- a |br| b | c",                   "a |br| b",                       "c"),
			("- a|b",                            "a|b",                            ""),
		):
			with self.subTest(line=line):
				entry = Tree._ParseEntries([line])[0]

				self.assertEqual(text, entry.Value)
				self.assertEqual(description, entry["description"])

	@testcase("Separator as marker")
	def Marker(self) -> None:
		"""
		A marker '|' declared by ':icons:' is no separator, as no whitespace precedes it.

		Parses an entry marked '|' with a description and checks marker, text and description.
		"""
		entry = Tree._ParseEntries(["| directory | empty"], ("-", "|"))[0]

		self.assertEqual("|", entry["marker"])
		self.assertEqual("directory", entry.Value)
		self.assertEqual("empty", entry["description"])

	@testcase("Nesting")
	def Nesting(self) -> None:
		"""
		Descriptions don't change the hierarchy, and entries with and without one may be mixed at every level.

		Parses a root with a description, a child without one and a grandchild with one, and checks each entry.
		"""
		roots = Tree._ParseEntries(["- root   | the root", "  - node", "    - leaf | a leaf", "  - sibling | last"])

		self.assertEqual(
			[("root", "the root", 0), ("node", "", 1), ("leaf", "a leaf", 2), ("sibling", "last", 1)],
			[(entry.Value, entry["description"], entry.Level) for entry in roots[0].IteratePreOrder()]
		)

	@testcase("Several separators")
	def Separators(self) -> None:
		"""
		A line with more than one separator is rejected; the message tells how to write a '|' in a text.

		Parses a line with two separators and checks the message.
		"""
		with self.assertRaises(SphinxExtensionError) as context:
			Tree._ParseEntries(["- a | b | c"])

		self.assertEqual(
			"'- a | b | c' has more than one separator ' | '; a '|' in a text is escaped as '\\|'.", str(context.exception)
		)

	@testcase("Description without text")
	def NoText(self) -> None:
		"""
		An entry needs a text, even if it has a description.

		Parses a description behind the marker and checks the message.
		"""
		with self.assertRaises(SphinxExtensionError) as context:
			Tree._ParseEntries(["- | description"])

		self.assertEqual("'- | description' is an entry without text.", str(context.exception))


@testsuite("Tree icons")
class TreeIcons(Testcase):
	"""The icon options: characters as written, and code points."""

	@testcase("Characters")
	def Characters(self) -> None:
		"""
		Characters are used as written.

		Converts a folder emoji and checks it is unchanged.
		"""
		self.assertEqual("\U0001f4c1", icon("\U0001f4c1"))

	@testcase("Code points")
	def CodePoints(self) -> None:
		"""
		A word 'U+<hex>' is the code point it names; several words form one icon.

		Converts 'U+1F4C1' alone, and together with 'U+FE0F', and checks the characters.
		"""
		self.assertEqual("\U0001f4c1", icon("U+1F4C1"))
		self.assertEqual("\U0001f4c1️", icon("U+1F4C1 U+FE0F"))

	@testcase("No value")
	def NoValue(self) -> None:
		"""
		An option without a value draws no icon.

		Converts None and checks the empty string.
		"""
		self.assertEqual("", icon(None))

	@testcase("Beyond Unicode")
	def BeyondUnicode(self) -> None:
		"""
		A code point beyond U+10FFFF is rejected.

		Converts 'U+110000' and checks the ValueError.
		"""
		with self.assertRaises(ValueError) as context:
			icon("U+110000")

		self.assertEqual("'U+110000' is beyond the last code point U+10FFFF.", str(context.exception))


@testsuite("Tree markers")
class TreeMarkers(Testcase):
	"""Option ':icons:': the markers an entry may start with, each with its icon."""

	@testcase("Markers and icons")
	def MarkerIcons(self) -> None:
		"""
		Each item is a marker and its icon; items are separated by commas, also across lines.

		Converts three items, the last on its own line and as a code point, and checks the mapping.
		"""
		self.assertEqual(
			{"*": "\U0001f4e6", "-": "\U0001f4c1", ">": "\U0001f4c4"},
			markerIcons("* \U0001f4e6, - \U0001f4c1,\n> U+1F4C4")
		)

	@testcase("No value")
	def NoValue(self) -> None:
		"""
		An option without a value declares no marker.

		Converts None and checks the empty mapping.
		"""
		self.assertEqual({}, markerIcons(None))

	@testcase("Invalid items")
	def Invalid(self) -> None:
		"""
		An item is a marker, a space and an icon; a marker isn't a letter or a digit, and is declared once.

		Converts an item without a space, one without an icon, one with a letter, and a marker declared twice, and checks
		each message.
		"""
		for option, message in (
			("*\U0001f4e6",  "'*\U0001f4e6' is not a marker followed by a space and an icon."),
			("* ",           "'*' is not a marker followed by a space and an icon."),
			("a \U0001f4e6", "Marker 'a' is a letter or a digit."),
			("* a, * b",     "Marker '*' is declared twice."),
		):
			with self.subTest(option=option), self.assertRaises(ValueError) as context:
				markerIcons(option)

			self.assertEqual(message, str(context.exception))
