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

The table's columns after the first are :class:`Column` and :class:`ColumnGroup` instances. A directive of another kind
of test report - e.g. a simulation framework's build summary - derives from :class:`UnittestSummaryBase`, which renders
the rows, and declares its own columns.

.. seealso::

   :ref:`DIR/UnittestSummary`
      |rarr| The directive's options and configuration, with examples.
"""
from __future__                         import annotations

from datetime                           import timedelta
from enum                               import Flag
from pathlib                            import Path
from typing                             import TYPE_CHECKING, Any, Callable, ClassVar, Generator, Iterable, Mapping, \
                                               Optional as Nullable, TypedDict
from xml.etree.ElementTree              import iterparse  # nosec B405 - reads the root element of the project's report

from docutils                           import nodes
from docutils.parsers.rst.directives    import flag
from sphinx.application                 import Sphinx
from sphinx.config                      import Config
from sphinx.util.logging                import getLogger

from pyTooling.Common                   import getFullyQualifiedName, getTypeName
from pyTooling.Decorators               import export, notimplemented, readonly
from pyTooling.MetaClasses              import ExtendedType

from pyTooling.Sphinx                   import BaseDirective, ReportExtensionError, ReportsPackageMissingError, \
                                               SphinxExtensionError, strip, stripAndNormalize
from pyTooling.Sphinx.Node              import Landscape, ReportIndentation
from pyTooling.Sphinx.Pages             import ReportPages

if TYPE_CHECKING:  # pragma: no cover
	# pyEDAA.Reports is an optional dependency (extra 'reports'), imported where a report is read.
	from pyEDAA.Reports.Unittesting       import TestcaseStatus, TestsuiteStatus, Testcase, Testsuite, TestsuiteBase, \
	                                             TestsuiteSummary


__all__ = ["CONFIG_PREFIX", "REPORT_FORMATS"]

CONFIG_PREFIX = "pyTooling_Unittest"
"""Prefix every configuration value of the unit test directive carries in :file:`conf.py`."""

REPORT_FORMATS = {
	"testsuites": "JUnit",
	"testsuite":  "JUnit",
	"TestReport": "pyTooling",
}
"""The report formats, by the root element of a report file."""


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
class Column(metaclass=ExtendedType, slots=True):
	"""
	A column of a unit test summary table: its title, its width, and the cells it adds to the rows.

	A row shows a testsuite summary, a testsuite or a testcase. A column names a function per kind of row, which returns
	the cell's content: a text, a node, or the cell itself - an :class:`~docutils.nodes.entry`, e.g. to give it a CSS
	class. A column without a function for a kind of row leaves the cell of such a row empty.
	"""

	_title:     str                                                         #: Title of the column.
	_width:     Nullable[int]                                               #: Relative width, or ``None``.
	_testsuite: Nullable[Callable[[TestsuiteBase[Any]], str | nodes.Node]]  #: Content of a testsuite('s summary) row.
	_testcase:  Nullable[Callable[[Testcase], str | nodes.Node]]            #: Content of a testcase's row.

	def __init__(
		self,
		title: str,
		width: Nullable[int] = None,
		*,
		testsuite: Nullable[Callable[[TestsuiteBase[Any]], str | nodes.Node]] = None,
		testcase: Nullable[Callable[[Testcase], str | nodes.Node]] = None
	) -> None:
		"""
		Initializes a column of a unit test summary table.

		:param title:       Title of the column.
		:param width:       Optional, relative width of the column; ``None`` leaves it to the writer. Default: ``None``.
		:param testsuite:   Optional, function returning the content of the cell of a testsuite's row and of a testsuite
		                    summary's rows. Default: ``None``.
		:param testcase:    Optional, function returning the content of the cell of a testcase's row. Default: ``None``.
		:raises ValueError: If parameter 'title' is None.
		:raises TypeError:  If parameter 'title' is not of type :class:`str`.
		:raises TypeError:  If parameter 'width' is not of type :class:`int`.
		:raises TypeError:  If parameter 'testsuite' is not callable.
		:raises TypeError:  If parameter 'testcase' is not callable.
		"""
		if title is None:
			raise ValueError("Parameter 'title' is None.")
		elif not isinstance(title, str):
			ex = TypeError("Parameter 'title' is not of type 'str'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(title)}'.")
			raise ex

		if width is not None and not isinstance(width, int):
			ex = TypeError("Parameter 'width' is not of type 'int'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(width)}'.")
			raise ex

		for parameterName, function in (
			("testsuite", testsuite),
			("testcase",  testcase)
		):
			if function is not None and not callable(function):
				ex = TypeError(f"Parameter '{parameterName}' is not callable.")
				ex.add_note(f"Got type '{getFullyQualifiedName(function)}'.")
				raise ex

		self._title =     title
		self._width =     width
		self._testsuite = testsuite
		self._testcase =  testcase

	@readonly
	def Title(self) -> str:
		"""
		Read-only property to access the column's title (:attr:`_title`).

		:returns: The title.
		"""
		return self._title

	@readonly
	def Width(self) -> Nullable[int]:
		"""
		Read-only property to access the column's relative width (:attr:`_width`).

		:returns: The width, or ``None`` if the writer chooses it.
		"""
		return self._width

	def TestsuiteCell(self, testsuite: TestsuiteBase[Any]) -> nodes.entry:
		"""
		Create the column's cell of a testsuite's row, or of a testsuite summary's row.

		:param testsuite: The testsuite or testsuite summary.
		:returns:         The cell.
		"""
		return self._Cell(self._testsuite, testsuite)

	def TestcaseCell(self, testcase: Testcase) -> nodes.entry:
		"""
		Create the column's cell of a testcase's row.

		:param testcase: The testcase.
		:returns:        The cell.
		"""
		return self._Cell(self._testcase, testcase)

	@staticmethod
	def _Cell(function: Nullable[Callable[[Any], str | nodes.Node]], entity: Any) -> nodes.entry:
		"""
		Create a cell from the content a function returns for a row's testsuite or testcase.

		:param function: The function, or ``None`` for an empty cell.
		:param entity:   The row's testsuite, testsuite summary or testcase.
		:returns:        The cell.
		"""
		if function is None:
			return nodes.entry("", nodes.Text(""))

		content = function(entity)
		if isinstance(content, nodes.entry):
			return content
		elif isinstance(content, str):
			return nodes.entry("", nodes.Text(content))

		return nodes.entry("", content)


@export
class ColumnGroup(metaclass=ExtendedType, slots=True):
	"""
	A group of columns of a unit test summary table, under a common title: the table's header gets a second row.
	"""

	_title:   str                 #: Title of the group.
	_columns: tuple[Column, ...]  #: The grouped columns.

	def __init__(self, title: str, columns: Iterable[Column]) -> None:
		"""
		Initializes a group of columns.

		:param title:       Title of the group.
		:param columns:     The grouped columns.
		:raises ValueError: If parameter 'title' is None.
		:raises TypeError:  If parameter 'title' is not of type :class:`str`.
		:raises ValueError: If parameter 'columns' is None.
		:raises TypeError:  If parameter 'columns' is not iterable.
		:raises TypeError:  If parameter 'columns' contains an element not of type :class:`Column`.
		:raises ValueError: If parameter 'columns' is empty.
		"""
		if title is None:
			raise ValueError("Parameter 'title' is None.")
		elif not isinstance(title, str):
			ex = TypeError("Parameter 'title' is not of type 'str'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(title)}'.")
			raise ex

		if columns is None:
			raise ValueError("Parameter 'columns' is None.")
		elif not isinstance(columns, Iterable):
			ex = TypeError("Parameter 'columns' is not iterable.")
			ex.add_note(f"Got type '{getFullyQualifiedName(columns)}'.")
			raise ex

		columnList = []
		for column in columns:
			if not isinstance(column, Column):
				ex = TypeError("Parameter 'columns' contains an element not of type 'Column'.")
				ex.add_note(f"Got type '{getFullyQualifiedName(column)}'.")
				raise ex

			columnList.append(column)

		if len(columnList) == 0:
			raise ValueError("Parameter 'columns' is empty.")

		self._title =   title
		self._columns = tuple(columnList)

	@readonly
	def Title(self) -> str:
		"""
		Read-only property to access the group's title (:attr:`_title`).

		:returns: The title.
		"""
		return self._title

	@readonly
	def Columns(self) -> tuple[Column, ...]:
		"""
		Read-only property to access the grouped columns (:attr:`_columns`).

		:returns: The columns, in their order in the table.
		"""
		return self._columns


@export
class UnittestSummaryBase(BaseDirective):
	"""
	Base-class of a directive rendering a testsuite summary - unit test results - as a table, per testsuite and testcase.

	The table has a row per testsuite and listed testcase, indented by its depth, optionally a row of the testsuite
	summary above them, and a row of the overall status below them. Its first column names the row - linked to the
	row's page, if the report has pages -, the other columns are the :class:`Column` and :class:`ColumnGroup` instances
	:meth:`_Columns` returns.

	The report files are declared in a configuration value of :file:`conf.py` (:attr:`_CONFIG_VALUE`), each with an
	identifier, the report file (key :attr:`_REPORT_KEY`) and optionally the key ``pages``. A derived class names them,
	declares its own class variables :attr:`_testSummaries`, :attr:`_reports` and :attr:`_readErrors`, reads a report
	file by :meth:`_ReadReport`, reads its options in :meth:`_CheckOptions`, and returns its pages by :meth:`_Pages`.
	"""

	_CONFIG_VALUE: ClassVar[str]                                         #: Configuration value declaring the reports.
	_REPORT_KEY:   ClassVar[str]                                         #: Key of a report's file, e.g. ``xml_report``.
	_REPORT_KIND:  ClassVar[str]                                         #: Kind of report, e.g. ``Unittest report``.
	_NAME_COLUMN:  ClassVar[Column] = Column("Testsuite / Testcase", 6)  #: The first column, naming the rows.

	_testSummaries: ClassVar[dict[str, dict[str, Any]]]    #: Report configurations, by report ID.
	_reports:       ClassVar[dict[str, TestsuiteSummary]]  #: Reports read by :meth:`ReadReports`, by ID.
	_readErrors:    ClassVar[dict[str, Exception]]         #: Why a report couldn't be read, by report ID.

	_cssClasses:           list[str]         #: Additional CSS classes of the table.
	_reportID:             str               #: Identifier of the report in the configuration.
	_reportFile:           Path              #: The report file.
	_hideTestsuiteSummary: bool              #: Whether the testsuite summary's row is left out.
	_testsuiteSummaryName: str               #: Name replacing the testsuite summary's name, or ``""``.
	_showTestcases:        ShowTestcases     #: Which testcases are listed.
	_testsuite:            TestsuiteSummary  #: The report's testsuite summary.

	@notimplemented("A derived directive implements '_CheckOptions'.")
	def _CheckOptions(self) -> None:
		"""
		Parse all directive options or use default values.

		A derived class sets :attr:`_cssClasses`, :attr:`_reportID`, :attr:`_reportFile`, :attr:`_hideTestsuiteSummary`,
		:attr:`_testsuiteSummaryName` and :attr:`_showTestcases`.
		"""

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
		Read every configured report, once per build.

		A report that can't be read keeps the exception, which a directive or a report's pages show when they need it.

		:param sphinxApplication: Sphinx application instance.
		"""
		getLogger(__name__).info(f"[REPORT] Reading {cls._REPORT_KIND.lower()}s ...")

		cls._reports =    {}
		cls._readErrors = {}
		for reportID, testSummary in cls._testSummaries.items():
			try:
				cls._reports[reportID] = cls._ReadReport(testSummary[cls._REPORT_KEY])
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
			raise ReportExtensionError(f"{cls._REPORT_KIND} '{reportID}' wasn't read.") from cause

	@classmethod
	@notimplemented("A derived directive implements '_ReadReport'.")
	def _ReadReport(cls, reportFile: Path) -> TestsuiteSummary:
		"""
		Read a report file.

		:param reportFile: The report file.
		:returns:          The report's testsuite summary, aggregated.
		"""

	@classmethod
	def _CheckConfiguration(cls, sphinxConfiguration: Config) -> None:
		"""
		Check and load the report configurations from the configuration value :attr:`_CONFIG_VALUE`.

		:param sphinxConfiguration:   Sphinx configuration instance.
		:raises ReportExtensionError: If the configuration value isn't registered.
		:raises ReportExtensionError: If a report configuration has no report file (key :attr:`_REPORT_KEY`).
		:raises ReportExtensionError: If the report file doesn't exist.
		:raises ReportExtensionError: If ``pages`` isn't a string.
		:raises ReportExtensionError: If ``pages`` isn't a relative document name. |br|
		                              Use a name like 'unittests/src', separated by '/', without '.' or '..'.
		"""
		variableName = cls._CONFIG_VALUE
		cls._testSummaries = {}

		try:
			allTestsuites: dict[str, dict[str, Any]] = sphinxConfiguration[variableName]
		except (KeyError, AttributeError) as ex:
			raise ReportExtensionError(f"Configuration option '{variableName}' is not configured.") from ex

		for reportID, testSummary in allTestsuites.items():
			summaryName = f"conf.py: {variableName}:[{reportID}]"

			try:
				reportFile = Path(testSummary[cls._REPORT_KEY])
			except KeyError as ex:
				raise ReportExtensionError(f"{summaryName}.{cls._REPORT_KEY}: Configuration is missing.") from ex

			if not reportFile.exists():
				raise ReportExtensionError(
					f"{summaryName}.{cls._REPORT_KEY}: {cls._REPORT_KIND} file '{reportFile}' doesn't exist."
				) from FileNotFoundError(reportFile)

			if (pages := testSummary.get("pages", None)) is not None:
				pages = ReportPages.CheckPagesConfiguration(summaryName, pages)

			cls._testSummaries[reportID] = {
				cls._REPORT_KEY: reportFile,
				"pages":         pages
			}

	@notimplemented("A derived directive implements '_Columns'.")
	def _Columns(self) -> list[Column | ColumnGroup]:
		"""
		Return the table's columns after the first one, which names the rows.

		:returns: The columns and groups of columns, in their order in the table.
		"""

	def _Pages(self) -> Nullable[ReportPages[Any]]:
		"""
		Return the pages of the report, which the first column links to.

		:returns: The report's pages, or ``None`` if it has none.
		"""
		return None

	def _TableClasses(self) -> list[str]:
		"""
		Return the CSS classes of the table: ``report-unittest-table``, ``report-unittest-<report ID>`` and the classes of
		option ``:class:``.

		:returns: The CSS classes.
		"""
		return ["report-unittest-table", f"report-unittest-{self._reportID}", *self._cssClasses]

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
		Build the table: a header of the columns, a row per testsuite and listed testcase, and a summary row.

		A header has a second row, if a column is a :class:`ColumnGroup`.

		:returns: The table.
		"""
		columns: list[Column] = []
		groups = False
		headerColumns: list[tuple[str, Nullable[list[tuple[str, int]]], Nullable[int]]] = [
			(self._NAME_COLUMN._title, None, self._NAME_COLUMN._width)
		]
		for column in self._Columns():
			if isinstance(column, ColumnGroup):
				groups = True
				columns.extend(column._columns)
				headerColumns.append((column._title, [(c._title, c._width) for c in column._columns], None))
			else:
				columns.append(column)
				headerColumns.append((column._title, None, column._width))

		if groups:
			tableGroup = self._CreateDoubleRowTableHeader(
				identifier=self._reportID,
				columns=headerColumns,
				classes=self._TableClasses()
			)
		else:
			tableGroup = self._CreateSingleRowTableHeader(
				identifier=self._reportID,
				columns=[(title, width) for title, _, width in headerColumns],
				classes=self._TableClasses()
			)

		tableBody = nodes.tbody()
		tableGroup += tableBody

		self._RenderRoot(tableBody, columns, self._testsuite, not self._hideTestsuiteSummary, self._testsuiteSummaryName)

		return tableGroup.parent

	def _RenderRoot(
		self,
		tableBody: nodes.tbody,
		columns: list[Column],
		testsuiteSummary: TestsuiteSummary,
		includeRoot: bool = True,
		testsuiteSummaryName: Nullable[str] = None
	) -> None:
		"""
		Add the rows of a testsuite summary: optionally its own row, its testsuites' rows, and the summary row.

		:param tableBody:            The table body the rows are added to.
		:param columns:              The columns after the first one.
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
			for column in columns:
				tableRow += column.TestsuiteCell(testsuiteSummary)

		for ts in self._SortedValues(testsuiteSummary._testsuites):
			self._RenderTestsuite(tableBody, columns, ts, level)

		self._RenderSummary(tableBody, columns, testsuiteSummary)

	def _RenderTestsuite(self, tableBody: nodes.tbody, columns: list[Column], testsuite: Testsuite, level: int) -> None:
		"""
		Add a row for a testsuite, then - recursively - rows for its testsuites and its listed testcases.

		:param tableBody: The table body the rows are added to.
		:param columns:   The columns after the first one.
		:param testsuite: The testsuite.
		:param level:     The testsuite's depth in the hierarchy, shown by indentation.
		"""
		state = self._ConvertTestsuiteStatusToSymbol(testsuite._status)

		tableRow = nodes.row("", classes=["report-testsuite", f"testsuite-{testsuite._status.name.lower()}"])
		tableBody += tableRow

		tableRow += self._NameEntry(2 * level, state, testsuite, "ts")
		for column in columns:
			tableRow += column.TestsuiteCell(testsuite)

		for ts in self._SortedValues(testsuite._testsuites):
			self._RenderTestsuite(tableBody, columns, ts, level + 1)

		for testcase in self._SortedValues(testsuite._testcases):
			if testcase._status == self._showTestcases:
				self._RenderTestcase(tableBody, columns, testcase, level + 1)

	def _RenderTestcase(self, tableBody: nodes.tbody, columns: list[Column], testcase: Testcase, level: int) -> None:
		"""
		Add a row for a testcase.

		:param tableBody: The table body the row is added to.
		:param columns:   The columns after the first one.
		:param testcase:  The testcase.
		:param level:     The testcase's depth in the hierarchy, shown by indentation.
		"""
		state = self._ConvertTestcaseStatusToSymbol(testcase._status)

		tableRow = nodes.row("", classes=["report-testcase", f"testcase-{testcase._status.name.lower()}"])
		tableBody += tableRow

		tableRow += self._NameEntry(2 * level, state, testcase, "tc")
		for column in columns:
			tableRow += column.TestcaseCell(testcase)

	def _NameEntry(self, level: int, state: str, entity: Testsuite | Testcase, roleName: str) -> nodes.entry:
		"""
		Create the cell naming a testsuite or testcase, indented, and linked to its page if the report has pages.

		:param level:    The number of indentation steps.
		:param state:    The status symbol written before the name.
		:param entity:   The testsuite or testcase.
		:param roleName: The role referring to it: ``ts`` for a testsuite, ``tc`` for a testcase.
		:returns:        The table cell.
		"""
		if (pages := self._Pages()) is not None and (entry := pages.Entry(entity)) is not None:
			# a reference has to be inside a text element; an inline keeps the cell free of a paragraph, as the others are
			reference = pages.CreateReference(roleName, entry, self.env.docname)
			return nodes.entry("", ReportIndentation("", "", nodes.Text(state), reference, level=level))

		return nodes.entry("", ReportIndentation("", f"{state}{entity.Name}", level=level))

	def _RenderSummary(self, tableBody: nodes.tbody, columns: list[Column], testsuiteSummary: TestsuiteSummary) -> None:
		"""
		Add the summary row: the overall status and counts.

		:param tableBody:        The table body the row is added to.
		:param columns:          The columns after the first one.
		:param testsuiteSummary: The testsuite summary.
		"""
		state = self._ConvertTestsuiteStatusToSymbol(testsuiteSummary._status)

		tableRow = nodes.row(
			"", classes=["report-summary", f"testsuitesummary-{testsuiteSummary._status.name.lower()}"]
		)
		tableBody += tableRow

		tableRow += nodes.entry("", nodes.Text(f"{state} {testsuiteSummary.Status.name.upper()}"))
		for column in columns:
			tableRow += column.TestsuiteCell(testsuiteSummary)

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
			message = f"Caught {getTypeName(ex)} when checking options for directive '{self.directiveName}'."
			return self._internalError(container, __name__, message, ex)

		if (readError := self._readErrors.get(self._reportID, None)) is not None:
			if isinstance(readError, ReportsPackageMissingError):
				message = f"Caught {getTypeName(readError)} when reading '{self._reportFile}'."
			else:
				message = f"Caught {getTypeName(readError)} when reading and parsing '{self._reportFile}'."
			return self._internalError(container, __name__, message, readError)

		try:
			self._testsuite = self.GetReport(self._reportID)
			container += self._GenerateTestSummaryTable()
		except Exception as ex:
			message = (
				f"Caught {getTypeName(ex)} when generating the document structure for {self._REPORT_KIND.lower()} "
				f"'{self._reportFile}'."
			)
			return self._internalError(container, __name__, message, ex)

		if (pages := self._Pages()) is None:
			return [container]

		return [container, pages.TableOfContents(self.env.docname)]


@export
class UnittestSummary(UnittestSummaryBase):
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

	_CONFIG_VALUE: ClassVar[str] = f"{CONFIG_PREFIX}_Testsuites"   #: Configuration value declaring the reports.
	_REPORT_KEY:   ClassVar[str] = "xml_report"                    #: Key of a report's file in its configuration.
	_REPORT_KIND:  ClassVar[str] = "Unittest report"               #: The kind of report, as a message names it.

	_testSummaries: ClassVar[dict[str, TestsuiteConfiguration]] = {}  #: Report configurations, by report ID.
	_reports:       ClassVar[dict[str, TestsuiteSummary]] = {}        #: Reports read by :meth:`ReadReports`, by ID.
	_readErrors:    ClassVar[dict[str, Exception]] = {}               #: Why a report couldn't be read, by report ID.

	_noAssertions: bool  #: Whether the assertion column is left out.

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
		self._reportFile = testSummary["xml_report"]

	def _Columns(self) -> list[Column | ColumnGroup]:
		"""
		Return the columns after the first one: the counts of testcases, skipped, errored, failed and passed ones, the
		assertions - unless option ``:no-assertions:`` is given -, and the runtime.

		:returns: The columns.
		"""
		def runtime(entity: TestsuiteBase[Any] | Testcase) -> str:
			"""
			Nested function formatting the runtime of a testsuite, testsuite summary or testcase.

			:param entity: The testsuite, testsuite summary or testcase.
			:returns:      The runtime.
			"""
			return self._FormatTimedelta(entity.TotalDuration)

		columns: list[Column | ColumnGroup] = [
			Column("Testcases", 1, testsuite=lambda testsuite: f"{testsuite.TestcaseCount}"),
			Column("Skipped",   1, testsuite=lambda testsuite: f"{testsuite.Skipped}"),
			Column("Errored",   1, testsuite=lambda testsuite: f"{testsuite.Errored}"),
			Column("Failed",    1, testsuite=lambda testsuite: f"{testsuite.Failed}"),
			Column("Passed",    1, testsuite=lambda testsuite: f"{testsuite.Passed}"),
		]
		if not self._noAssertions:
			columns.append(Column("Assertions", 1, testcase=lambda testcase: f"{testcase.AssertionCount}"))
		columns.append(Column("Runtime (HH:MM:SS.sss)", 2, testsuite=runtime, testcase=runtime))

		return columns

	def _Pages(self) -> Nullable[ReportPages[Any]]:
		"""
		Return the pages of the report, if it was declared with the key ``pages``.

		:returns: The report's pages, or ``None`` if it has none.
		"""
		from pyTooling.Sphinx.UnittestPages import UnittestReportPages

		if not UnittestReportPages.HasPages(self._reportID):
			return None

		return UnittestReportPages.GetPages(self._reportID)

	@classmethod
	def _ReadReport(cls, xmlReport: Path) -> TestsuiteSummary:
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
		testsuiteSummary = document.ToTestsuiteSummary()
		testsuiteSummary.Aggregate()

		return testsuiteSummary
