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
A page per testsuite and per testcase of a unit test report, generated without a source file.

A report declared in ``pyTooling_Unittest_Testsuites`` with the key ``pages`` gets a document per testsuite and per
testcase, named below that key's document name:

* a testsuite: ``<pages>/<testsuite>/<testsuite>/...``, the names of the testsuites from the report's summary down;
* a testcase: ``<pages>/<testsuite>/.../<testcase>``.

The pages are built from the report :class:`~pyTooling.Sphinx.Unittest.UnittestSummary` read, by the machinery of
:class:`~pyTooling.Sphinx.Pages.ReportPages`: a testsuite's page lists its testsuites and testcases in a hidden table
of contents, as the directive ``report:unittest-summary`` lists the top-level testsuites, so the pages are in the
navigation below the summary's document. Every testsuite and testcase with a page is an object of domain ``report``,
referred to by the roles ``:ts:`` and ``:tc:``.

.. seealso::

   :ref:`DIR/UnittestSummary/Pages`
      |rarr| The pages and the roles, with examples.
   :mod:`pyTooling.Sphinx.Pages`
      |rarr| The pages of a report: document names, registration, generation and navigation.
"""
from __future__                 import annotations

from textwrap                   import dedent
from typing                     import TYPE_CHECKING, ClassVar, Iterable, Optional as Nullable

from docutils                   import nodes
from sphinx.application         import Sphinx
from sphinx.util.logging        import getLogger

from pyTooling.Decorators       import export

from pyTooling.Sphinx           import ReportExtensionError
from pyTooling.Sphinx.Pages     import ReportPages
from pyTooling.Sphinx.Unittest  import UnittestSummary

if TYPE_CHECKING:  # pragma: no cover
	# pyEDAA.Reports is an optional dependency (extra 'reports'), imported where a report is read.
	from pathlib                  import Path

	from pyEDAA.Reports.Unittesting import Testcase, Testsuite, TestsuiteSummary


@export
class UnittestReportPages(ReportPages):
	"""
	The pages of one unit test report: a page per testsuite and per testcase.
	"""

	_reportPages: ClassVar[dict[str, ReportPages]] = {}  #: The pages of every unit test report with pages, by report ID.
	_separator:   ClassVar[str] = "."                    #: Separator of the names in a qualified name.

	_summary: TestsuiteSummary  #: The report's testsuite summary.

	def __init__(self, reportID: str, prefix: str, xmlReport: Path, summary: TestsuiteSummary) -> None:
		"""
		Compute the document names and entries of a report's testsuites and testcases.

		A testsuite or testcase whose qualified name is already taken by another of the same kind gets no page; this
		is logged as a warning.

		:param reportID:  Identifier of the report.
		:param prefix:    Document name the pages are generated below.
		:param xmlReport: The report file.
		:param summary:   The report's testsuite summary.
		"""
		topLevel = [("ts", testsuite) for testsuite in sorted(summary._testsuites.values(), key=lambda item: item._name)]
		super().__init__(reportID, prefix, xmlReport, topLevel)

		self._summary = summary

	@classmethod
	def CreatePages(cls, sphinxApplication: Sphinx) -> None:
		"""
		Call-back for Sphinx' ``builder-inited`` event, after the reports are read: compute and register the pages.

		Only a report with the key ``pages`` gets pages. A report that couldn't be read gets none; this is logged as an
		error.

		:param sphinxApplication: Sphinx application instance.
		"""
		cls._reportPages = {}
		for reportID, testSummary in UnittestSummary._testSummaries.items():
			if (prefix := testSummary["pages"]) is None:
				continue

			try:
				summary = UnittestSummary.GetReport(reportID)
			except ReportExtensionError as ex:
				cause = ex if ex.__cause__ is None else ex.__cause__
				getLogger(__name__).error(
					f"Caught {ex.__class__.__name__} when generating the pages of unittest report '{reportID}'.\n"
					f"  {cause.__class__.__name__}: {cause}"
				)
				continue

			pages = cls(reportID, prefix, testSummary["xml_report"], summary)
			cls._reportPages[reportID] = pages
			pages.Register(sphinxApplication.env)

	def _Name(self, entity: Testsuite | Testcase) -> str:
		"""
		Return a testsuite's or testcase's name.

		:param entity: The testsuite or testcase.
		:returns:      The name.
		"""
		return entity._name

	def _Title(self, entity: Testsuite | Testcase) -> Nullable[str]:
		"""
		Return a testsuite's or testcase's title written for a reader, if it differs from its name.

		:param entity: The testsuite or testcase.
		:returns:      The title, or ``None``.
		"""
		return None if entity._title == entity._name else entity._title

	def _Children(self, roleName: str, entity: Testsuite | Testcase) -> Iterable[tuple[str, Testsuite | Testcase]]:
		"""
		Return a testsuite's testsuites, then its testcases, each sorted by name; a testcase has none.

		:param roleName: The role referring to the object: ``ts`` or ``tc``.
		:param entity:   The testsuite or testcase.
		:returns:        The children as ``(role name, object)`` pairs.
		"""
		if roleName == "tc":
			return []

		return [
			*(("ts", testsuite) for testsuite in sorted(entity._testsuites.values(), key=lambda item: item._name)),
			*(("tc", testcase) for testcase in sorted(entity._testcases.values(), key=lambda item: item._name))
		]

	def _Page(self, docName: str, roleName: str, entity: Testsuite | Testcase) -> nodes.section:
		"""
		Build a testsuite's or testcase's page.

		:param docName:  Name of the page's document.
		:param roleName: The role referring to the object: ``ts`` or ``tc``.
		:param entity:   The testsuite or testcase.
		:returns:        The page's top section.
		"""
		if roleName == "ts":
			return self._TestsuitePage(docName, entity)
		else:
			return self._TestcasePage(docName, entity)

	def _PageSection(self, entity: Testsuite | Testcase) -> nodes.section:
		"""
		Create a page's top section: the name as title, then the title, summary and description of the report, if any.

		The title is shown as a lead line, if it differs from the name. The summary is shown, if it differs from the
		title. The description is shown without its first paragraph, if that is the summary. The texts are shown as
		plain text: a paragraph per block, and a literal block for an indented block.

		:param entity: The testsuite or testcase.
		:returns:      The section.
		"""
		section = nodes.section("", nodes.title(entity._name, entity._name), ids=["report-unittest-page"])

		title, summary, description = entity._title, entity._summary, entity._description
		if title is not None and title != entity._name:
			section += nodes.paragraph("", "", nodes.strong(title, title), classes=["report-unittest-title"])

		if summary is not None and summary != title:
			section += nodes.paragraph(summary, summary, classes=["report-unittest-summary"])

		if description is not None:
			if summary is not None and description.startswith(summary):
				description = description[len(summary):]

			for block in description.strip("\n").split("\n\n"):
				lines = [line for line in block.split("\n") if line.strip() != ""]
				if len(lines) == 0:
					continue
				elif all(line[0] in " \t" for line in lines):
					text = dedent("\n".join(lines))
					section += nodes.literal_block(text, text, language="text", classes=["report-unittest-description"])
				else:
					text = " ".join(line.strip() for line in lines)
					section += nodes.paragraph(text, text, classes=["report-unittest-description"])

		return section

	def _TestcasePage(self, docName: str, testcase: Testcase) -> nodes.section:
		"""
		Build a testcase's page: its status, duration, assertions and testsuite, its message and its captured output.

		:param docName:  Name of the page's document.
		:param testcase: The testcase.
		:returns:        The page's top section.
		"""
		page = self._PageSection(testcase)
		status = testcase._status

		page += (summarySection := nodes.section("", nodes.title("Summary", "Summary"), ids=["summary"]))
		summarySection += (fieldList := nodes.field_list(classes=["report-unittest-fields"]))
		symbol = UnittestSummary._ConvertTestcaseStatusToSymbol(status)
		self._Field(fieldList, "Status", nodes.Text(f"{symbol} {status.name}"))
		self._Field(fieldList, "Duration", nodes.Text(UnittestSummary._FormatTimedelta(testcase._totalDuration)))
		if testcase._assertionCount is not None:
			self._Field(fieldList, "Assertions", nodes.Text(f"{testcase._assertionCount}"))
		self._Field(fieldList, "Testsuite", self._Reference("ts", testcase._parent, docName))

		for identifier, title, texts in (
			("message",         "Message",         (testcase._message, testcase._details)),
			("standard-output", "Standard Output", (testcase._standardOutput, )),
			("standard-error",  "Standard Error",  (testcase._standardError, )),
		):
			if all(text is None for text in texts):
				continue

			page += (section := nodes.section("", nodes.title(title, title), ids=[identifier]))
			for text in texts:
				if text is not None:
					section += nodes.literal_block(text, text, language="text", classes=[f"report-unittest-{identifier}"])

		return page

	def _TestsuitePage(self, docName: str, testsuite: Testsuite) -> nodes.section:
		"""
		Build a testsuite's page: its status, counts, duration and assertions, then tables of its testsuites and
		testcases, each linked to its page.

		:param docName:   Name of the page's document.
		:param testsuite: The testsuite.
		:returns:         The page's top section.
		"""
		page = self._PageSection(testsuite)
		status = testsuite._status
		testcases = list(testsuite.IterateTestcases())
		withAssertions = any(testcase._assertionCount is not None for testcase in testcases)

		page += (summarySection := nodes.section("", nodes.title("Summary", "Summary"), ids=["summary"]))
		summarySection += (fieldList := nodes.field_list(classes=["report-unittest-fields"]))
		symbol = UnittestSummary._ConvertTestsuiteStatusToSymbol(status)
		self._Field(fieldList, "Status", nodes.Text(f"{symbol} {status.name}"))
		self._Field(
			fieldList, "Testcases",
			nodes.Text(
				f"{testsuite.TestcaseCount} - {testsuite.Passed} passed, {testsuite.Failed} failed, "
				f"{testsuite.Errored} errored, {testsuite.Skipped} skipped"
			)
		)
		self._Field(fieldList, "Duration", nodes.Text(UnittestSummary._FormatTimedelta(testsuite._totalDuration)))
		if withAssertions:
			self._Field(fieldList, "Assertions", nodes.Text(f"{testsuite.AssertionCount}"))

		if (parent := testsuite._parent) is not None and parent is not self._summary:
			self._Field(fieldList, "Testsuite", self._Reference("ts", parent, docName))

		children: list[str] = []
		if len(testsuite._testsuites) > 0:
			page += (section := nodes.section("", nodes.title("Testsuites", "Testsuites"), ids=["testsuites"]))
			table, tableBody = self._Table(
				[("Testsuite", 6), ("Status", 2), ("Testcases", 1), ("Duration", 2)], ["report-unittest-testsuites"]
			)
			section += table
			for nested in sorted(testsuite._testsuites.values(), key=lambda item: item._name):
				symbol = UnittestSummary._ConvertTestsuiteStatusToSymbol(nested._status)
				tableBody += (row := nodes.row("", classes=[f"testsuite-{nested._status.name.lower()}"]))
				row += nodes.entry("", nodes.paragraph("", "", self._Reference("ts", nested, docName)))
				row += nodes.entry("", nodes.paragraph("", f"{symbol} {nested._status.name}"))
				row += nodes.entry("", nodes.paragraph("", f"{nested.TestcaseCount}"))
				row += nodes.entry("", nodes.paragraph("", UnittestSummary._FormatTimedelta(nested._totalDuration)))
				if (entry := self.Entry(nested)) is not None:
					children.append(entry.docName)

		if len(testsuite._testcases) > 0:
			page += (section := nodes.section("", nodes.title("Testcases", "Testcases"), ids=["testcases"]))
			columns = [("Testcase", 6), ("Status", 2), ("Duration", 2)]
			if withAssertions:
				columns.append(("Assertions", 1))
			table, tableBody = self._Table(columns, ["report-unittest-testcases"])
			section += table
			for testcase in sorted(testsuite._testcases.values(), key=lambda item: item._name):
				symbol = UnittestSummary._ConvertTestcaseStatusToSymbol(testcase._status)
				tableBody += (row := nodes.row("", classes=[f"testcase-{testcase._status.name.lower()}"]))
				row += nodes.entry("", nodes.paragraph("", "", self._Reference("tc", testcase, docName)))
				row += nodes.entry("", nodes.paragraph("", f"{symbol} {testcase._status.name}"))
				row += nodes.entry("", nodes.paragraph("", UnittestSummary._FormatTimedelta(testcase._totalDuration)))
				if withAssertions:
					assertions = "" if testcase._assertionCount is None else f"{testcase._assertionCount}"
					row += nodes.entry("", nodes.paragraph("", assertions))

				if (entry := self.Entry(testcase)) is not None:
					children.append(entry.docName)

		if len(children) > 0:
			# body elements precede a section's subsections, so the hidden table of contents goes before 'Summary'
			page.insert(page.index(summarySection), self._TableOfContents(docName, children))

		return page
