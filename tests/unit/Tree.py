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
Unit tests for :mod:`pyTooling.Sphinx.Tree`: reading the directive's content, and its icon options.
"""
from pyTooling.Sphinx      import SphinxExtensionError
from pyTooling.Sphinx.Tree import Tree, icon
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

	@testcase("Trailing colon")
	def Colon(self) -> None:
		"""
		A trailing colon marks a node and isn't part of the text; an escaped colon is.

		Parses an entry with a trailing colon, one with a role and a colon, and one with an escaped colon.
		"""
		roots = Tree._ParseEntries(["- empty :", "- :file:`doc`:", "- Note\\:"])

		self.assertEqual(["empty", ":file:`doc`", "Note\\:"], [root.Value for root in roots])
		self.assertEqual([True, True, False], [root["colon"] for root in roots])

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

		Parses a line without a dash and one with a dash but no space, and checks the message.
		"""
		for line in ("pyTooling", "-pyTooling"):
			with self.subTest(line=line), self.assertRaises(SphinxExtensionError) as context:
				Tree._ParseEntries([line])

			self.assertEqual(f"'{line}' is not an entry, which starts with '- '.", str(context.exception))

	@testcase("Entry without text")
	def NoText(self) -> None:
		"""
		An entry needs a text; a trailing colon alone isn't one.

		Parses a dash alone and a dash with a colon, and checks the message.
		"""
		for line in ("-", "- :"):
			with self.subTest(line=line), self.assertRaises(SphinxExtensionError) as context:
				Tree._ParseEntries([line])

			self.assertEqual(f"'{line}' is an entry without text.", str(context.exception))

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
