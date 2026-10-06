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
# Copyright 2023-2026 Patrick Lehmann - Bötzingen, Germany                                                             #
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
A directive rendering a unit test report as a table: per testsuite and testcase, the counts and the runtime.

The reports are read by :mod:`pyEDAA.Reports` in the Any JUnit XML format, so any JUnit dialect is accepted - e.g.
the reports of pytest or OSVVM. The report files are declared in :file:`conf.py` under
``pyTooling_Unittest_Testsuites``, each with an identifier a directive names in its ``:reportid:`` option:

.. code-block:: Python

   # doc/conf.py
   pyTooling_Unittest_Testsuites = {
     "src": {
       "xml_report": "../report/unit/unittest.xml",
     }
   }

.. seealso::

   :ref:`DIR/UnittestSummary`
      |rarr| The directive's options and configuration, with examples.
"""
from __future__                         import annotations

from datetime                           import timedelta
from enum                               import Flag
from pathlib                            import Path
from typing                             import TYPE_CHECKING, Any, ClassVar, Generator, Mapping, Optional as Nullable
from typing                             import TypedDict

from docutils                           import nodes
from docutils.parsers.rst.directives    import flag
from sphinx.application                 import Sphinx
from sphinx.config                      import Config
from sphinx.util.logging                import getLogger

from pyTooling.Decorators               import export

from pyTooling.Sphinx                   import INDENTATION, BaseDirective, ReportExtensionError
from pyTooling.Sphinx                   import ReportsPackageMissingError, SphinxExtensionError, strip
from pyTooling.Sphinx                   import stripAndNormalize
from pyTooling.Sphinx.Node              import Landscape

if TYPE_CHECKING:  # pragma: no cover
	# pyEDAA.Reports is an optional dependency (extra 'reports'), imported where a report is read.
	from pyEDAA.Reports.Unittesting       import TestcaseStatus, TestsuiteStatus
	from pyEDAA.Reports.Unittesting.JUnit import Testcase, Testsuite, TestsuiteSummary


__all__ = ["CONFIG_PREFIX"]

#: Prefix every configuration value of the unit test directive carries in :file:`conf.py`.
CONFIG_PREFIX = "pyTooling_Unittest"


@export
class TestsuiteConfiguration(TypedDict):
	"""An entry of ``pyTooling_Unittest_Testsuites``, after :meth:`UnittestSummary.CheckConfiguration` read it."""

	xml_report: Path  #: The unit test report, in Any JUnit XML format.


@export
class ShowTestcases(Flag):
	"""
	Which testcases a unit test summary lists, by their status.

	A member compares equal to a :class:`~pyEDAA.Reports.Unittesting.TestcaseStatus` it includes.
	"""

	passed =    1  #: Passed testcases.
	failed =    2  #: Failed testcases.
	skipped =   4  #: Skipped testcases.
	excluded =  8  #: Excluded testcases.
	errors =   16  #: Errored testcases, and testcases whose setup failed.
	aborted =  32  #: Aborted testcases.

	all = passed | failed | skipped | excluded | errors | aborted  #: Every testcase.
	not_passed = all & ~passed                                     #: Every testcase but the passed ones.

	def __eq__(self, other: Any) -> bool:
		"""
		Check whether a testcase status is included.

		:param other: A testcase status.
		:returns:     ``True`` if ``other`` is a :class:`~pyEDAA.Reports.Unittesting.TestcaseStatus` this member includes.
		"""
		from pyEDAA.Reports.Unittesting import TestcaseStatus

		if isinstance(other, TestcaseStatus):
			if other is TestcaseStatus.Passed:
				return ShowTestcases.passed in self
			elif other is TestcaseStatus.Failed:
				return ShowTestcases.failed in self
			elif other is TestcaseStatus.Skipped:
				return ShowTestcases.skipped in self
			elif other is TestcaseStatus.Excluded:
				return ShowTestcases.excluded in self
			elif other is TestcaseStatus.Errored or other is TestcaseStatus.SetupError:
				return ShowTestcases.errors in self
			elif other is TestcaseStatus.Aborted:
				return ShowTestcases.aborted in self

		return False


@export
class UnittestSummary(BaseDirective):
	"""
	The ``report:unittest-summary`` directive: a table of a unit test report, per testsuite and testcase.
	"""

	directiveName: str = "unittest-summary"  #: Name the directive is invoked by.

	has_content =        False  #: A boolean; ``True`` if content is allowed.
	required_arguments = 0      #: Number of required directive arguments.
	optional_arguments = 6      #: Number of optional arguments.

	option_spec: dict[str, Any] = {  # type: ignore[misc]
		"class":                  strip,
		"reportid":               stripAndNormalize,
		"testsuite-summary-name": strip,
		"show-testcases":         stripAndNormalize,
		"no-assertions":          flag,
		"hide-testsuite-summary": flag
	}  #: Mapping of option names to validator functions.

	configValues: ClassVar[dict[str, tuple[Any, str, Any]]] = {
		"Testsuites": ({}, "env", dict)
	}  #: Values added to :file:`conf.py`, as ``name: (default, rebuild, types)``, prefixed by :data:`CONFIG_PREFIX`.

	_testSummaries: ClassVar[dict[str, TestsuiteConfiguration]] = {}  #: Report configurations, by report ID.

	_cssClasses:           list[str]         #: Additional CSS classes of the table.
	_reportID:             str               #: Identifier of the report in the configuration.
	_noAssertions:         bool              #: Whether the assertion column is left out.
	_hideTestsuiteSummary: bool              #: Whether the testsuite summary's row is left out.
	_testsuiteSummaryName: Nullable[str]     #: Name replacing the testsuite summary's name, or ``""``.
	_showTestcases:        ShowTestcases     #: Which testcases are listed.
	_xmlReport:            Path              #: The unit test report.
	_testsuite:            TestsuiteSummary  #: The report's testsuite summary.

	def _CheckOptions(self) -> None:
		"""
		Parse all directive options or use default values.

		:raises SphinxExtensionError: If option ``:class:`` isn't a list of CSS class names.
		:raises SphinxExtensionError: If option ``:show-testcases:`` is neither ``all`` nor ``not-passed``.
		:raises SphinxExtensionError: If option ``:reportid:`` is missing.
		:raises ReportExtensionError: If ``pyTooling_Unittest_Testsuites`` has no entry for the report ID.
		"""
		cssClasses = self._ParseStringOption("class", "", r"(\w+)?( +\w+)*")
		showTestcases = self._ParseStringOption("show-testcases", "all", r"all|not-passed")

		self._cssClasses = [] if cssClasses == "" else cssClasses.split(" ")
		self._reportID = self._ParseStringOption("reportid")
		self._testsuiteSummaryName = self._ParseStringOption("testsuite-summary-name", "", r".+")
		self._showTestcases = ShowTestcases[showTestcases.replace("-", "_")]
		self._noAssertions = "no-assertions" in self.options
		self._hideTestsuiteSummary = "hide-testsuite-summary" in self.options

		try:
			testSummary = self._testSummaries[self._reportID]
		except KeyError as ex:
			raise ReportExtensionError(f"No unit testing configuration item for '{self._reportID}'.") from ex
		self._xmlReport = testSummary["xml_report"]

	@classmethod
	def CheckConfiguration(cls, sphinxApplication: Sphinx, sphinxConfiguration: Config) -> None:
		"""
		Check the configuration value and load the report configurations.

		:param sphinxApplication:   Sphinx application instance.
		:param sphinxConfiguration: Sphinx configuration instance.
		"""
		cls._CheckConfiguration(sphinxConfiguration)

	@classmethod
	def ReadReports(cls, sphinxApplication: Sphinx) -> None:
		"""
		Read unittest report files.

		So far, this only logs that the reports are read; each directive reads its report when it runs.

		:param sphinxApplication: Sphinx application instance.
		"""
		getLogger(__name__).info("[REPORT] Reading unittest reports ...")

	@classmethod
	def _CheckConfiguration(cls, sphinxConfiguration: Config) -> None:
		"""
		Check and load the report configurations from ``pyTooling_Unittest_Testsuites``.

		:param sphinxConfiguration:   Sphinx configuration instance.
		:raises ReportExtensionError: If the configuration value isn't registered.
		:raises ReportExtensionError: If a report configuration has no ``xml_report``.
		:raises ReportExtensionError: If the ``xml_report`` file doesn't exist.
		"""
		variableName = f"{CONFIG_PREFIX}_Testsuites"

		try:
			allTestsuites: dict[str, TestsuiteConfiguration] = sphinxConfiguration[variableName]
		except (KeyError, AttributeError) as ex:
			raise ReportExtensionError(f"Configuration option '{variableName}' is not configured.") from ex

		for reportID, testSummary in allTestsuites.items():
			summaryName = f"conf.py: {variableName}:[{reportID}]"

			try:
				xmlReport = Path(testSummary["xml_report"])
			except KeyError as ex:
				raise ReportExtensionError(f"{summaryName}.xml_report: Configuration is missing.") from ex

			if not xmlReport.exists():
				raise ReportExtensionError(
					f"{summaryName}.xml_report: Unittest report file '{xmlReport}' doesn't exist."
				) from FileNotFoundError(xmlReport)

			cls._testSummaries[reportID] = {
				"xml_report": xmlReport
			}

	def _SortedValues(self, d: Mapping[str, Any]) -> Generator[Any, None, None]:
		"""
		Yield the values of a mapping, sorted by key.

		:param d: The mapping, e.g. a testsuite's testcases by name.
		:returns: A generator of the values, sorted by their keys.
		"""
		for key in sorted(d.keys()):
			yield d[key]

	def _ConvertTestcaseStatusToSymbol(self, status: TestcaseStatus) -> str:
		"""
		Return the symbol shown for a testcase's status.

		:param status: The testcase's status.
		:returns:      An emoji, e.g. ✅ for a passed testcase.
		"""
		from pyEDAA.Reports.Unittesting import TestcaseStatus

		if status is TestcaseStatus.Passed:
			return "✅"
		elif status is TestcaseStatus.Failed:
			return "❌"
		elif status is TestcaseStatus.Skipped:
			return "⚠️"
		elif status is TestcaseStatus.Aborted:
			return "🚫"
		elif status is TestcaseStatus.Excluded:
			return "➖"
		elif status is TestcaseStatus.Errored:
			return "❗"
		elif status is TestcaseStatus.SetupError:
			return "⛔"
		elif status is TestcaseStatus.Unknown:
			return "❓"
		else:
			return "❌"

	def _ConvertTestsuiteStatusToSymbol(self, status: TestsuiteStatus) -> str:
		"""
		Return the symbol shown for a testsuite's status.

		:param status: The testsuite's status.
		:returns:      An emoji, e.g. ✅ for a passed testsuite.
		"""
		from pyEDAA.Reports.Unittesting import TestsuiteStatus

		if status is TestsuiteStatus.Passed:
			return "✅"
		elif status is TestsuiteStatus.Failed:
			return "❌"
		elif status is TestsuiteStatus.Skipped:
			return "⚠️"
		elif status is TestsuiteStatus.Aborted:
			return "🚫"
		elif status is TestsuiteStatus.Excluded:
			return "➖"
		elif status is TestsuiteStatus.Errored:
			return "❗"
		elif status is TestsuiteStatus.SetupError:
			return "⛔"
		elif status is TestsuiteStatus.Unknown:
			return "❓"
		else:
			return "❌"

	def _FormatTimedelta(self, delta: Nullable[timedelta]) -> str:
		"""
		Format a duration as ``HH:MM:SS.sss``, rounded to milliseconds.

		:param delta: The duration, or ``None``.
		:returns:     The formatted duration, or ``""`` for ``None``.
		"""
		if delta is None:
			return ""

		# Compute by hand, because timedelta._to_microseconds is not officially documented
		microseconds = (delta.days * 86_400 + delta.seconds) * 1_000_000 + delta.microseconds
		milliseconds = (microseconds + 500) // 1000
		seconds = milliseconds // 1000
		minutes = seconds // 60
		hours = minutes // 60
		return f"{hours:02}:{minutes % 60:02}:{seconds % 60:02}.{milliseconds % 1000:03}"

	def _GenerateTestSummaryTable(self) -> nodes.table:
		"""
		Build the table: a row per testsuite and listed testcase, and a summary row.

		:returns: The table.
		"""
		# Create a table and table header with 8 columns
		columns: list[tuple[str, Nullable[int]]] = [
			("Testsuite / Testcase", 6),
			("Testcases", 1),
			("Skipped", 1),
			("Errored", 1),
			("Failed", 1),
			("Passed", 1),
			("Assertions", 1),
			("Runtime (HH:MM:SS.sss)", 2),
		]

		# If assertions shouldn't be displayed, remove column from columns list
		if self._noAssertions:
			columns.pop(6)

		cssClasses = ["report-unittest-table", f"report-unittest-{self._reportID}"]
		cssClasses.extend(self._cssClasses)

		tableGroup = self._CreateSingleRowTableHeader(
			identifier=self._reportID,
			columns=columns,
			classes=cssClasses
		)
		tableBody = nodes.tbody()
		tableGroup += tableBody

		self._RenderRoot(tableBody, self._testsuite, not self._hideTestsuiteSummary, self._testsuiteSummaryName)

		return tableGroup.parent

	def _RenderRoot(
		self,
		tableBody: nodes.tbody,
		testsuiteSummary: TestsuiteSummary,
		includeRoot: bool = True,
		testsuiteSummaryName: Nullable[str] = None
	) -> None:
		"""
		Add the rows of a testsuite summary: optionally its own row, its testsuites' rows, and the summary row.

		:param tableBody:            The table body the rows are added to.
		:param testsuiteSummary:     The testsuite summary.
		:param includeRoot:          Optional, whether the testsuite summary gets a row of its own. Default: ``True``.
		:param testsuiteSummaryName: Optional, name replacing the testsuite summary's name; ``""`` keeps it.
		                             Default: ``None``.
		"""
		level = 0

		if includeRoot:
			level += 1
			state = self._ConvertTestsuiteStatusToSymbol(testsuiteSummary._status)

			tableRow = nodes.row(
				"", classes=["report-testsuitesummary", f"testsuitesummary-{testsuiteSummary._status.name.lower()}"]
			)
			tableBody += tableRow

			name = testsuiteSummary.Name if testsuiteSummaryName == "" else testsuiteSummaryName
			tableRow += nodes.entry("", nodes.Text(f"{state}{name}"))
			tableRow += nodes.entry("", nodes.Text(f"{testsuiteSummary.TestcaseCount}"))
			tableRow += nodes.entry("", nodes.Text(f"{testsuiteSummary.Skipped}"))
			tableRow += nodes.entry("", nodes.Text(f"{testsuiteSummary.Errored}"))
			tableRow += nodes.entry("", nodes.Text(f"{testsuiteSummary.Failed}"))
			tableRow += nodes.entry("", nodes.Text(f"{testsuiteSummary.Passed}"))
			if not self._noAssertions:
				tableRow += nodes.entry("", nodes.Text(""))
			tableRow += nodes.entry("", nodes.Text(f"{self._FormatTimedelta(testsuiteSummary.TotalDuration)}"))

		for ts in self._SortedValues(testsuiteSummary._testsuites):
			self._RenderTestsuite(tableBody, ts, level)

		self._RenderSummary(tableBody, testsuiteSummary)

	def _RenderTestsuite(self, tableBody: nodes.tbody, testsuite: Testsuite, level: int) -> None:
		"""
		Add a row for a testsuite, then - recursively - rows for its testsuites and its listed testcases.

		:param tableBody: The table body the rows are added to.
		:param testsuite: The testsuite.
		:param level:     The testsuite's depth in the hierarchy, shown by indentation.
		"""
		state = self._ConvertTestsuiteStatusToSymbol(testsuite._status)

		tableRow = nodes.row("", classes=["report-testsuite", f"testsuite-{testsuite._status.name.lower()}"])
		tableBody += tableRow

		tableRow += nodes.entry("", nodes.Text(f"{INDENTATION * 2 * level}{state}{testsuite.Name}"))
		tableRow += nodes.entry("", nodes.Text(f"{testsuite.TestcaseCount}"))
		tableRow += nodes.entry("", nodes.Text(f"{testsuite.Skipped}"))
		tableRow += nodes.entry("", nodes.Text(f"{testsuite.Errored}"))
		tableRow += nodes.entry("", nodes.Text(f"{testsuite.Failed}"))
		tableRow += nodes.entry("", nodes.Text(f"{testsuite.Passed}"))
		if not self._noAssertions:
			tableRow += nodes.entry("", nodes.Text(""))
		tableRow += nodes.entry("", nodes.Text(f"{self._FormatTimedelta(testsuite.TotalDuration)}"))

		for ts in self._SortedValues(testsuite._testsuites):
			self._RenderTestsuite(tableBody, ts, level + 1)

		for testcase in self._SortedValues(testsuite._testcases):
			if testcase._status == self._showTestcases:
				self._RenderTestcase(tableBody, testcase, level + 1)

	def _RenderTestcase(self, tableBody: nodes.tbody, testcase: Testcase, level: int) -> None:
		"""
		Add a row for a testcase.

		:param tableBody: The table body the row is added to.
		:param testcase:  The testcase.
		:param level:     The testcase's depth in the hierarchy, shown by indentation.
		"""
		state = self._ConvertTestcaseStatusToSymbol(testcase._status)

		tableRow = nodes.row("", classes=["report-testcase", f"testcase-{testcase._status.name.lower()}"])
		tableBody += tableRow

		tableRow += nodes.entry("", nodes.Text(f"{INDENTATION * 2 * level}{state}{testcase.Name}"))
		tableRow += nodes.entry("", nodes.Text(""))
		tableRow += nodes.entry("", nodes.Text(""))
		tableRow += nodes.entry("", nodes.Text(""))
		tableRow += nodes.entry("", nodes.Text(""))
		tableRow += nodes.entry("", nodes.Text(""))
		if not self._noAssertions:
			tableRow += nodes.entry("", nodes.Text(f"{testcase.AssertionCount}"))
		tableRow += nodes.entry("", nodes.Text(f"{self._FormatTimedelta(testcase.TotalDuration)}"))

	def _RenderSummary(self, tableBody: nodes.tbody, testsuiteSummary: TestsuiteSummary) -> None:
		"""
		Add the summary row: the overall status and counts.

		:param tableBody:        The table body the row is added to.
		:param testsuiteSummary: The testsuite summary.
		"""
		state = self._ConvertTestsuiteStatusToSymbol(testsuiteSummary._status)

		tableRow = nodes.row(
			"", classes=["report-summary", f"testsuitesummary-{testsuiteSummary._status.name.lower()}"]
		)
		tableBody += tableRow

		tableRow += nodes.entry("", nodes.Text(f"{state} {testsuiteSummary.Status.name.upper()}"))
		tableRow += nodes.entry("", nodes.Text(f"{testsuiteSummary.TestcaseCount}"))
		tableRow += nodes.entry("", nodes.Text(f"{testsuiteSummary.Skipped}"))
		tableRow += nodes.entry("", nodes.Text(f"{testsuiteSummary.Errored}"))
		tableRow += nodes.entry("", nodes.Text(f"{testsuiteSummary.Failed}"))
		tableRow += nodes.entry("", nodes.Text(f"{testsuiteSummary.Passed}"))
		if not self._noAssertions:
			tableRow += nodes.entry("", nodes.Text(""))
		tableRow += nodes.entry("", nodes.Text(f"{self._FormatTimedelta(testsuiteSummary.TotalDuration)}"))

	def run(self) -> list[nodes.Node]:
		"""
		Read the configured report and return it as a table, on landscape pages in LaTeX.

		:returns: A :class:`~pyTooling.Sphinx.Node.Landscape` container holding the table, or the error message.
		"""
		container = Landscape()

		try:
			self._CheckOptions()
		except SphinxExtensionError as ex:
			message = f"Caught {ex.__class__.__name__} when checking options for directive '{self.directiveName}'."
			return self._internalError(container, __name__, message, ex)

		try:
			from pyEDAA.Reports.Unittesting.JUnit import Document
		except ImportError as cause:
			ex = ReportsPackageMissingError("Reading a unit test report")
			ex.__cause__ = cause
			message = f"Caught {ex.__class__.__name__} when reading '{self._xmlReport}'."
			return self._internalError(container, __name__, message, ex)

		try:
			doc = Document(self._xmlReport, analyzeAndConvert=True)
		except Exception as ex:
			message = f"Caught {ex.__class__.__name__} when reading and parsing '{self._xmlReport}'."
			return self._internalError(container, __name__, message, ex)

		doc.Aggregate()

		try:
			self._testsuite = doc.ToTestsuiteSummary()
		except Exception as ex:
			message = (
				f"Caught {ex.__class__.__name__} when converting to a TestsuiteSummary for JUnit document "
				f"'{self._xmlReport}'."
			)
			return self._internalError(container, __name__, message, ex)

		self._testsuite.Aggregate()

		try:
			container += self._GenerateTestSummaryTable()
		except Exception as ex:
			message = (
				f"Caught {ex.__class__.__name__} when generating the document structure for JUnit document "
				f"'{self._xmlReport}'."
			)
			return self._internalError(container, __name__, message, ex)

		return [container]
