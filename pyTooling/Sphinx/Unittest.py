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

The reports are read by :mod:`pyEDAA.Reports`: a JUnit XML file in any dialect - e.g. the reports of pytest or
OSVVM -, or a test report in pyTooling's own XML format, recognized by its root element ``<TestReport>``. The report
files are declared in :file:`conf.py` under ``pyTooling_Unittest_Testsuites``, each with an identifier a directive
names in its ``:reportid:`` option. An entry with the key ``pages`` gets a page per testsuite and testcase, generated
below that document name (see :mod:`pyTooling.Sphinx.UnittestPages`):

.. code-block:: Python

   # doc/conf.py
   pyTooling_Unittest_Testsuites = {
     "src": {
       "xml_report": "../report/unit/unittest.xml",
       "pages":      "unittests/src",
     }
   }

The reports are read once, when the builder is initialized, and shared by every directive and page using them.

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
from xml.etree.ElementTree              import iterparse  # nosec B405 - reads the root element of the project's report

from docutils                           import nodes
from docutils.parsers.rst.directives    import flag
from sphinx.application                 import Sphinx
from sphinx.config                      import Config
from sphinx.util.logging                import getLogger

from pyTooling.Common                   import getFullyQualifiedName
from pyTooling.Decorators               import export

from pyTooling.Sphinx                   import INDENTATION, BaseDirective, ReportExtensionError
from pyTooling.Sphinx                   import ReportsPackageMissingError, SphinxExtensionError
from pyTooling.Sphinx                   import strip, stripAndNormalize
from pyTooling.Sphinx.Node              import Landscape

if TYPE_CHECKING:  # pragma: no cover
	# pyEDAA.Reports is an optional dependency (extra 'reports'), imported where a report is read.
	from pyEDAA.Reports.Unittesting       import TestcaseStatus, TestsuiteStatus
	from pyEDAA.Reports.Unittesting       import Testcase, Testsuite, TestsuiteSummary


__all__ = ["CONFIG_PREFIX", "REPORT_FORMATS"]

#: Prefix every configuration value of the unit test directive carries in :file:`conf.py`.
CONFIG_PREFIX = "pyTooling_Unittest"

#: The report formats, by the root element of a report file.
REPORT_FORMATS = {
	"testsuites": "JUnit",
	"testsuite":  "JUnit",
	"TestReport": "pyTooling",
}


@export
class TestsuiteConfiguration(TypedDict):
	"""An entry of ``pyTooling_Unittest_Testsuites``, after :meth:`UnittestSummary.CheckConfiguration` read it."""

	xml_report: Path           #: The unit test report, in JUnit XML or pyTooling's XML format.
	pages:      Nullable[str]  #: Document name the pages per testsuite and testcase are generated below, if any.


@export
class ShowTestcases(Flag):
	"""
	Which testcases a unit test summary lists, by their status.

	A member compares equal to a :class:`~pyEDAA.Reports.Unittesting.TestcaseStatus` it includes.
	"""

	passed =    1  #: Passed testcases, and testcases failing as expected.
	failed =    2  #: Failed testcases, and testcases passing unexpectedly.
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
			if other is TestcaseStatus.Passed or other is TestcaseStatus.ExpectedFailed:
				return ShowTestcases.passed in self
			elif other is TestcaseStatus.Failed or other is TestcaseStatus.UnexpectedPassed:
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
	_reports:       ClassVar[dict[str, TestsuiteSummary]] = {}        #: Reports read by :meth:`ReadReports`, by ID.
	_readErrors:    ClassVar[dict[str, Exception]] = {}               #: Why a report couldn't be read, by report ID.

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
		Read every configured unit test report, once per build.

		A report that can't be read keeps the exception, which a directive or a report's pages show when they need it.

		:param sphinxApplication: Sphinx application instance.
		"""
		getLogger(__name__).info("[REPORT] Reading unittest reports ...")

		cls._reports = {}
		cls._readErrors = {}
		for reportID, testSummary in cls._testSummaries.items():
			try:
				cls._reports[reportID] = cls._ReadReport(testSummary["xml_report"])
			except Exception as ex:
				cls._readErrors[reportID] = ex

	@classmethod
	def GetReport(cls, reportID: str) -> TestsuiteSummary:
		"""
		Return a report read by :meth:`ReadReports`.

		:param reportID:              Identifier of the report.
		:returns:                     The report's testsuite summary.
		:raises ReportExtensionError: If the report wasn't read, chained to the exception reading it raised.
		"""
		try:
			return cls._reports[reportID]
		except KeyError:
			cause = cls._readErrors.get(reportID, None)
			raise ReportExtensionError(f"Unittest report '{reportID}' wasn't read.") from cause

	@staticmethod
	def _ReadReport(xmlReport: Path) -> TestsuiteSummary:
		"""
		Read a report file, choosing the reader by the file's root element.

		:param xmlReport:                   The report file.
		:returns:                           The report's testsuite summary, aggregated.
		:raises ReportExtensionError:       If the file's root element is no known report format.
		:raises ReportsPackageMissingError: If pyEDAA.Reports, or its reader for the report's format, isn't installed.
		"""
		_, rootElement = next(iterparse(xmlReport, events=("start",)))  # nosec B314 - the project's own report
		try:
			reportFormat = REPORT_FORMATS[rootElement.tag]
		except KeyError:
			ex = ReportExtensionError(f"Unittest report '{xmlReport}' has an unknown format.")
			ex.add_note(f"Got root element '<{rootElement.tag}>'; supported: {', '.join(REPORT_FORMATS)}")
			raise ex from None

		if reportFormat == "pyTooling":
			try:
				from pyEDAA.Reports.Unittesting.pyTooling import Document as pyToolingDocument
			except ImportError as cause:
				raise ReportsPackageMissingError("Reading a pyTooling test report") from cause

			return pyToolingDocument(xmlReport, analyzeAndConvert=True)

		try:
			from pyEDAA.Reports.Unittesting.JUnit import Document as JUnitDocument
		except ImportError as cause:
			raise ReportsPackageMissingError("Reading a unit test report") from cause

		document = JUnitDocument(xmlReport, analyzeAndConvert=True)
		document.Aggregate()
		testsuiteSummary = document.ToTestsuiteSummary()
		testsuiteSummary.Aggregate()

		return testsuiteSummary

	@classmethod
	def _CheckConfiguration(cls, sphinxConfiguration: Config) -> None:
		"""
		Check and load the report configurations from ``pyTooling_Unittest_Testsuites``.

		:param sphinxConfiguration:   Sphinx configuration instance.
		:raises ReportExtensionError: If the configuration value isn't registered.
		:raises ReportExtensionError: If a report configuration has no ``xml_report``.
		:raises ReportExtensionError: If the ``xml_report`` file doesn't exist.
		:raises ReportExtensionError: If ``pages`` isn't a string.
		:raises ReportExtensionError: If ``pages`` isn't a relative document name. |br|
		                              Use a name like 'unittests/src', separated by '/', without '.' or '..'.
		"""
		variableName = f"{CONFIG_PREFIX}_Testsuites"
		cls._testSummaries = {}

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

			pages = testSummary.get("pages", None)
			if pages is not None:
				if not isinstance(pages, str):
					ex = ReportExtensionError(f"{summaryName}.pages: Document name is not a string.")
					ex.add_note(f"Got type '{getFullyQualifiedName(pages)}'.")
					raise ex

				parts = pages.strip("/").split("/")
				if "\\" in pages or any(part in ("", ".", "..") for part in parts):
					ex = ReportExtensionError(f"{summaryName}.pages: '{pages}' is not a relative document name.")
					ex.add_note("Use a name like 'unittests/src', separated by '/', without '.' or '..'.")
					raise ex

				pages = "/".join(parts)

			cls._testSummaries[reportID] = {
				"xml_report": xmlReport,
				"pages":      pages
			}

	def _SortedValues(self, d: Mapping[str, Any]) -> Generator[Any, None, None]:
		"""
		Yield the values of a mapping, sorted by key.

		:param d: The mapping, e.g. a testsuite's testcases by name.
		:returns: A generator of the values, sorted by their keys.
		"""
		for key in sorted(d.keys()):
			yield d[key]

	@staticmethod
	def _ConvertTestcaseStatusToSymbol(status: TestcaseStatus) -> str:
		"""
		Return the symbol shown for a testcase's status.

		:param status: The testcase's status.
		:returns:      An emoji, e.g. ✅ for a passed testcase.
		"""
		from pyEDAA.Reports.Unittesting import TestcaseStatus

		if status is TestcaseStatus.Passed or status is TestcaseStatus.ExpectedFailed:
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

	@staticmethod
	def _ConvertTestsuiteStatusToSymbol(status: TestsuiteStatus) -> str:
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

	@staticmethod
	def _FormatTimedelta(delta: Nullable[timedelta]) -> str:
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

		tableRow += self._NameEntry(f"{INDENTATION * 2 * level}{state}", testsuite, "ts")
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

		tableRow += self._NameEntry(f"{INDENTATION * 2 * level}{state}", testcase, "tc")
		tableRow += nodes.entry("", nodes.Text(""))
		tableRow += nodes.entry("", nodes.Text(""))
		tableRow += nodes.entry("", nodes.Text(""))
		tableRow += nodes.entry("", nodes.Text(""))
		tableRow += nodes.entry("", nodes.Text(""))
		if not self._noAssertions:
			tableRow += nodes.entry("", nodes.Text(f"{testcase.AssertionCount}"))
		tableRow += nodes.entry("", nodes.Text(f"{self._FormatTimedelta(testcase.TotalDuration)}"))

	def _NameEntry(self, prefix: str, entity: Testsuite | Testcase, roleName: str) -> nodes.entry:
		"""
		Create the cell naming a testsuite or testcase, linked to its page if the report has pages.

		:param prefix:   The indentation and the status symbol written before the name.
		:param entity:   The testsuite or testcase.
		:param roleName: The role referring to it: ``ts`` for a testsuite, ``tc`` for a testcase.
		:returns:        The table cell.
		"""
		from pyTooling.Sphinx.UnittestPages import UnittestReportPages

		if (pages := UnittestReportPages.GetPages(self._reportID)) is None or (entry := pages.Entry(entity)) is None:
			return nodes.entry("", nodes.Text(f"{prefix}{entity.Name}"))

		# a reference has to be inside a text element; an inline keeps the cell free of a paragraph, as the others are
		reference = pages.CreateReference(roleName, entry, self.env.docname)
		return nodes.entry("", nodes.inline("", "", nodes.Text(prefix), reference))

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

		A report with pages adds a hidden table of contents of its top-level testsuites, so the pages are below this
		document in the navigation.

		:returns: A :class:`~pyTooling.Sphinx.Node.Landscape` container holding the table, or the error message; then
		          the table of contents, if the report has pages.
		"""
		container = Landscape()

		try:
			self._CheckOptions()
		except SphinxExtensionError as ex:
			message = f"Caught {ex.__class__.__name__} when checking options for directive '{self.directiveName}'."
			return self._internalError(container, __name__, message, ex)

		if (readError := self._readErrors.get(self._reportID, None)) is not None:
			if isinstance(readError, ReportsPackageMissingError):
				message = f"Caught {readError.__class__.__name__} when reading '{self._xmlReport}'."
			else:
				message = f"Caught {readError.__class__.__name__} when reading and parsing '{self._xmlReport}'."
			return self._internalError(container, __name__, message, readError)

		try:
			self._testsuite = self.GetReport(self._reportID)
			container += self._GenerateTestSummaryTable()
		except Exception as ex:
			message = (
				f"Caught {ex.__class__.__name__} when generating the document structure for unittest report "
				f"'{self._xmlReport}'."
			)
			return self._internalError(container, __name__, message, ex)

		from pyTooling.Sphinx.UnittestPages import UnittestReportPages

		if (pages := UnittestReportPages.GetPages(self._reportID)) is None:
			return [container]

		return [container, pages.TableOfContents(self.env.docname)]
