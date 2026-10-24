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
Unit tests for :mod:`pyTooling.Sphinx.Unittest`: which testcases are listed, how a runtime is written, and the columns
of a table a derived directive declares.
"""
from datetime                  import timedelta
from pathlib                   import Path
from textwrap                  import dedent

from docutils                  import nodes

from pyEDAA.Reports            import Unittesting
from pyTooling.Sphinx.Unittest import CONFIG_PREFIX, Column, ColumnGroup, ShowTestcases, UnittestSummary
from pyTooling.Testing         import Testcase, testsuite, testcase

from tests.unit.Extension      import Project


if __name__ == "__main__":  # pragma: no cover
	print("ERROR: you called a testcase declaration file as an executable module.")
	print("Use: 'python -m unittest <testcase module>'")
	exit(1)


@testsuite("Listed testcases")
class ListedTestcases(Testcase):
	"""Option ':show-testcases:' as the flag 'ShowTestcases', compared with a testcase's status."""

	@testcase("All")
	def All(self) -> None:
		"""
		'all' includes the statuses a summary distinguishes, and not 'Unknown'.

		Compares 'all' with 'Passed', 'Failed', 'Skipped', 'Excluded', 'Errored', 'SetupError', 'Aborted' and 'Unknown'.
		"""
		status = Unittesting.TestcaseStatus
		for included in (
			status.Passed, status.Failed, status.Skipped, status.Excluded, status.Errored, status.SetupError, status.Aborted
		):
			with self.subTest(status=included):
				self.assertTrue(ShowTestcases.all == included)

		self.assertFalse(ShowTestcases.all == status.Unknown)

	@testcase("Not passed")
	def NotPassed(self) -> None:
		"""
		'not_passed' includes a failed testcase, but not a passed one.

		Compares 'not_passed' with 'Passed', 'Failed', 'Errored' and 'SetupError'.
		"""
		self.assertFalse(ShowTestcases.not_passed == Unittesting.TestcaseStatus.Passed)
		self.assertTrue(ShowTestcases.not_passed == Unittesting.TestcaseStatus.Failed)
		self.assertTrue(ShowTestcases.not_passed == Unittesting.TestcaseStatus.Errored)
		self.assertTrue(ShowTestcases.not_passed == Unittesting.TestcaseStatus.SetupError)

	@testcase("Other types")
	def OtherTypes(self) -> None:
		"""
		A member doesn't compare equal to anything but a testcase status.

		Compares 'all' with a testsuite status and a string.
		"""
		self.assertFalse(ShowTestcases.all == Unittesting.TestsuiteStatus.Passed)
		self.assertFalse(ShowTestcases.all == "passed")


@testsuite("Unit test summary")
class Summary(Testcase):
	"""The directive's configuration value, runtimes and symbols."""

	@testcase("Configuration value name")
	def Names(self) -> None:
		"""
		The configuration value is 'pyTooling_Unittest_Testsuites'.

		Checks the prefix and the name in 'configValues'.
		"""
		self.assertEqual("pyTooling_Unittest", CONFIG_PREFIX)
		self.assertEqual({"Testsuites"}, set(UnittestSummary.configValues))

	@testcase("Runtime")
	def FormatTimedelta(self) -> None:
		"""
		A runtime is written as 'HH:MM:SS.sss', rounded to milliseconds; no runtime is written as an empty string.

		Formats 1 h 2 min 3.4567 s, and None.
		"""
		directive = UnittestSummary.__new__(UnittestSummary)

		self.assertEqual(
			"01:02:03.457", directive._FormatTimedelta(timedelta(hours=1, minutes=2, seconds=3, microseconds=456_700))
		)
		self.assertEqual("", directive._FormatTimedelta(None))

	@testcase("Status symbols")
	def Symbols(self) -> None:
		"""
		A passed testcase or testsuite is shown as ✅ and a failed one as ❌.

		Converts 'Passed' and 'Failed' of both enumerations.
		"""
		directive = UnittestSummary.__new__(UnittestSummary)

		self.assertEqual("✅", directive._ConvertTestcaseStatusToSymbol(Unittesting.TestcaseStatus.Passed))
		self.assertEqual("❌", directive._ConvertTestcaseStatusToSymbol(Unittesting.TestcaseStatus.Failed))
		self.assertEqual("✅", directive._ConvertTestsuiteStatusToSymbol(Unittesting.TestsuiteStatus.Passed))
		self.assertEqual("❌", directive._ConvertTestsuiteStatusToSymbol(Unittesting.TestsuiteStatus.Failed))

	@testcase("Legend symbols")
	def LegendSymbols(self) -> None:
		"""
		The legend names every symbol a testcase or testsuite can be shown with, each once.

		Converts every member of both enumerations and looks the symbol up in the legend.
		"""
		directive = UnittestSummary.__new__(UnittestSummary)
		legendSymbols = [symbol for symbol, _ in UnittestSummary._LEGEND]

		self.assertEqual(len(set(legendSymbols)), len(legendSymbols))
		for status in Unittesting.TestcaseStatus:
			with self.subTest(testcaseStatus=status):
				self.assertIn(directive._ConvertTestcaseStatusToSymbol(status), legendSymbols)

		for status in Unittesting.TestsuiteStatus:
			with self.subTest(testsuiteStatus=status):
				self.assertIn(directive._ConvertTestsuiteStatusToSymbol(status), legendSymbols)


DATA = Path(__file__).parent.parent / "data" / "Report"
"""Directory of the report files the testcases read."""


@testsuite("Table columns")
class Columns(Testcase):
	"""A column's parameters, and the cells it creates from the content its functions return."""

	@testcase("Cells")
	def Cells(self) -> None:
		"""
		A text becomes the cell's text, a node the cell's child, a cell is taken as is, and no function leaves it empty.

		Creates the testsuite and testcase cells of four columns.
		"""
		testsuite = Unittesting.Testsuite("Suite")
		testcase = Unittesting.Testcase("Case", parent=testsuite)
		ownCell = nodes.entry("", nodes.Text("own"), classes=["mismatch"])

		textCell = Column("Text", testsuite=lambda entity: entity.Name).TestsuiteCell(testsuite)
		nodeCell = Column("Node", testcase=lambda entity: nodes.strong("", entity.Name)).TestcaseCell(testcase)
		entryCell = Column("Entry", testcase=lambda entity: ownCell).TestcaseCell(testcase)
		emptyCell = Column("Empty").TestsuiteCell(testsuite)

		self.assertEqual("<entry>Suite</entry>", str(textCell))
		self.assertEqual("<entry><strong>Case</strong></entry>", str(nodeCell))
		self.assertIs(ownCell, entryCell)
		self.assertEqual("", emptyCell.astext())

	@testcase("Column parameters")
	def ColumnParameters(self) -> None:
		"""
		A column's title is a string, its width an integer, and its functions callable.

		Creates columns with a missing title, a title, width and function of a wrong type.
		"""
		with self.assertRaises(ValueError) as context:
			_ = Column(None)
		self.assertEqual("Parameter 'title' is None.", str(context.exception))

		with self.assertRaises(TypeError) as context:
			_ = Column(1)
		self.assertEqual("Parameter 'title' is not of type 'str'.", str(context.exception))

		with self.assertRaises(TypeError) as context:
			_ = Column("Count", "1")
		self.assertEqual("Parameter 'width' is not of type 'int'.", str(context.exception))

		with self.assertRaises(TypeError) as context:
			_ = Column("Count", testcase="Count")
		self.assertEqual("Parameter 'testcase' is not callable.", str(context.exception))

		column = Column("Count", 2)
		self.assertEqual("Count", column.Title)
		self.assertEqual(2, column.Width)

	@testcase("Group parameters")
	def GroupParameters(self) -> None:
		"""
		A group has a title and at least one column.

		Creates groups without columns, with no iterable and with an element not being a column.
		"""
		with self.assertRaises(ValueError) as context:
			_ = ColumnGroup("Alerts", [])
		self.assertEqual("Parameter 'columns' is empty.", str(context.exception))

		with self.assertRaises(TypeError) as context:
			_ = ColumnGroup("Alerts", 1)
		self.assertEqual("Parameter 'columns' is not iterable.", str(context.exception))

		with self.assertRaises(TypeError) as context:
			_ = ColumnGroup("Alerts", ["Errors"])
		self.assertEqual("Parameter 'columns' contains an element not of type 'Column'.", str(context.exception))

		group = ColumnGroup("Alerts", [Column("Errors"), Column("Warnings")])
		self.assertEqual("Alerts", group.Title)
		self.assertEqual(("Errors", "Warnings"), tuple(column.Title for column in group.Columns))


@testsuite("Derived summary table")
class DerivedTable(Project):
	"""A directive derived from 'UnittestSummary' declaring its own columns, one of them a group."""

	_conf = dedent("""\
		from pyTooling.Sphinx.Unittest import Column, ColumnGroup, UnittestSummary

		class OwnSummary(UnittestSummary):
			directiveName = "own-summary"

			def _Columns(self):
				return [
					Column("Testcases", 1, testsuite=lambda testsuite: f"{testsuite.TestcaseCount}"),
					ColumnGroup("Assertions", [
						Column("Passed", 1, testcase=lambda testcase: f"{testcase.PassedAssertionCount}"),
						Column("Total",  1, testcase=lambda testcase: f"{testcase.AssertionCount}")
					])
				]

		def setup(app):
			app.add_directive_to_domain("report", "own-summary", OwnSummary)
	""")

	@testcase("Grouped columns")
	def GroupedColumns(self) -> None:
		"""
		A group of columns gives the header a second row; a column outside a group spans both rows.

		Builds a document with the derived directive and checks the header cells and a testsuite's cell.
		"""
		self._build(
			"Index\n#####\n\n.. report:own-summary::\n   :reportid: ut\n", conf=self._conf,
			pyTooling_Unittest_Testsuites={"ut": {"xml_report": str(DATA / "unittest.xml")}}
		)

		self.assertEqual([], self._warningLines())
		html = self._html("index")
		header = html[html.index("<thead>"):html.index("</thead>")]
		self.assertEqual(2, header.count("<tr"))
		self.assertIn('<th class="head" rowspan="2">Testsuite / Testcase</th>', header)
		self.assertIn('<th class="head" rowspan="2">Testcases</th>', header)
		self.assertIn('<th class="head" colspan="2">Assertions</th>', header)
		self.assertIn('<th class="head">Passed</th>', header)
		self.assertIn('class="report-unittest-table report-unittest-ut docutils', html)

	@testcase("Legend")
	def Legend(self) -> None:
		"""
		A derived table gets the legend of the status symbols below it.

		Builds a document with the derived directive and checks the legend's class and its place.
		"""
		self._build(
			"Index\n#####\n\n.. report:own-summary::\n   :reportid: ut\n", conf=self._conf,
			pyTooling_Unittest_Testsuites={"ut": {"xml_report": str(DATA / "unittest.xml")}}
		)

		self.assertEqual([], self._warningLines())
		html = self._html("index")
		self.assertIn('<p class="report-unittest-legend report-unittest-legend-bottom">Legend: ', html)
		self.assertLess(html.index('class="report-unittest-table'), html.index('class="report-unittest-legend'))
