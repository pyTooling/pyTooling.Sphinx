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

A name's characters other than letters, digits, ``_``, ``-`` and ``.`` - e.g. the brackets of a parametrized pytest
testcase - are replaced by ``_``, and a name colliding with a sibling's (also when differing only in case) gets the
suffix ``-2``, ``-3``, ...

The pages are built as docutils node trees from the report :class:`UnittestSummary` read, and handed to Sphinx as if
they were read from a file: their names are registered when the builder is initialized and again before the
documents are read - :meth:`sphinx.project.Project.discover` forgets them in between -, and the file Sphinx sees as
their source is the report, so a changed report rebuilds them. A page carries the metadata ``:orphan:``; a testsuite's
page links its testsuites and testcases in a hidden table of contents. Every testsuite and testcase with a page is an
object of domain ``report``, referred to by the roles ``:ts:`` and ``:tc:``.

.. seealso::

   :ref:`DIR/UnittestSummary/Pages`
      |rarr| The pages and the roles, with examples.
"""
from __future__                 import annotations

from re                         import compile as re_compile
from textwrap                   import dedent
from time                       import time_ns
from typing                     import TYPE_CHECKING, ClassVar, Iterable, Optional as Nullable

from docutils                   import nodes
from docutils.utils             import DependencyList
from sphinx                     import addnodes
from sphinx.application         import Sphinx
from sphinx.environment         import BuildEnvironment
from sphinx.util.docutils       import new_document
from sphinx.util.logging        import getLogger

from pyTooling.Decorators       import export, readonly
from pyTooling.MetaClasses      import ExtendedType

from pyTooling.Sphinx           import ReportDomain, ReportExtensionError, UnittestEntry
from pyTooling.Sphinx.Unittest  import UnittestSummary

if TYPE_CHECKING:  # pragma: no cover
	# pyEDAA.Reports is an optional dependency (extra 'reports'), imported where a report is read.
	from pathlib                  import Path

	from pyEDAA.Reports.Unittesting import Testcase, Testsuite, TestsuiteSummary


__all__ = ["UNSAFE_CHARACTERS"]

#: Characters of a testsuite's or testcase's name, which are replaced in its document name.
UNSAFE_CHARACTERS = re_compile(r"[^A-Za-z0-9_.\-]+")


@export
class UnittestReportPages(metaclass=ExtendedType, slots=True):
	"""
	The pages of one unit test report: a document name and an entry of domain ``report`` per testsuite and testcase.

	The document names are computed once, when the report's pages are created, so the summary table, the roles and the
	pages agree on them.
	"""

	_reportPages: ClassVar[dict[str, UnittestReportPages]] = {}  #: The pages of every report with pages, by report ID.

	_reportID:   str                                                #: Identifier of the report.
	_xmlReport:  Path                                               #: The report file, the pages' source for Sphinx.
	_summary:    TestsuiteSummary                                   #: The report's testsuite summary.
	_entries:    dict[int, UnittestEntry]                           #: The entries, by the ``id()`` of their entity.
	_documents:  dict[str, tuple[str, Testsuite | Testcase]]        #: Role name and entity, by document name.

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
		self._reportID =  reportID
		self._xmlReport = xmlReport.resolve()
		self._summary =   summary
		self._entries =   {}
		self._documents = {}

		qualifiedNames: dict[str, set[str]] = {"ts": set(), "tc": set()}

		def addEntities(
			entities: Iterable[Testsuite | Testcase],
			roleName: str,
			path: tuple[str, ...],
			directory: str,
			siblings: set[str]
		) -> None:
			"""
			Nested function adding a document name and entry per testsuite or testcase, recursing into testsuites.

			:param entities:  The testsuites or testcases of one parent.
			:param roleName:  The role referring to them: ``ts`` or ``tc``.
			:param path:      The parent's path below the summary.
			:param directory: The parent's document name, the directory of its children's documents.
			:param siblings:  The document names used below that directory so far, in lower case.
			"""
			for entity in sorted(entities, key=lambda item: item._name):
				entityPath = (*path, entity._name)
				qualifiedName = ".".join(entityPath)
				if qualifiedName in qualifiedNames[roleName]:
					getLogger(__name__).warning(
						f"Unittest report '{reportID}': the qualified name '{qualifiedName}' is not unique, "
						f"so the second one gets no page."
					)
					continue

				qualifiedNames[roleName].add(qualifiedName)

				baseName = UNSAFE_CHARACTERS.sub("_", entity._name).strip("_.") or "_"
				fileName, counter = baseName, 1
				while fileName.lower() in siblings:
					counter += 1
					fileName = f"{baseName}-{counter}"
				siblings.add(fileName.lower())

				docName = f"{directory}/{fileName}"
				title = None if entity._title == entity._name else entity._title
				self._entries[id(entity)] = UnittestEntry(docName, reportID, entityPath, title)
				self._documents[docName] = (roleName, entity)

				if roleName == "ts":
					children: set[str] = set()
					addEntities(entity._testsuites.values(), "ts", entityPath, docName, children)
					addEntities(entity._testcases.values(), "tc", entityPath, docName, children)

		addEntities(summary._testsuites.values(), "ts", (), prefix, set())

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

	@classmethod
	def GetPages(cls, reportID: str) -> Nullable[UnittestReportPages]:
		"""
		Return the pages of a report.

		:param reportID: Identifier of the report.
		:returns:        The report's pages, or ``None`` if the report has none.
		"""
		return cls._reportPages.get(reportID, None)

	@classmethod
	def GenerateAll(cls, sphinxApplication: Sphinx, env: BuildEnvironment, docnames: list[str]) -> None:
		"""
		Call-back for Sphinx' ``env-before-read-docs`` event: generate the pages of every report.

		:param sphinxApplication: Sphinx application instance.
		:param env:               The build environment.
		:param docnames:          The documents to read, from which the generated pages are removed.
		"""
		for pages in cls._reportPages.values():
			pages.Generate(sphinxApplication)

			docnames[:] = [docname for docname in docnames if docname not in pages._documents]

	@classmethod
	def HideSource(
		cls,
		sphinxApplication: Sphinx,
		pagename: str,
		templatename: str,
		context: dict[str, object],
		doctree: Nullable[nodes.document]
	) -> None:
		"""
		Call-back for Sphinx' ``html-page-context`` event: a generated page has no source to copy or link.

		Without it, the HTML builder would copy the report file - the page's source for Sphinx - per page.

		:param sphinxApplication: Sphinx application instance.
		:param pagename:          Name of the page.
		:param templatename:      Name of the page's template.
		:param context:           The template's context.
		:param doctree:           The page's doctree.
		"""
		if any(pagename in pages._documents for pages in cls._reportPages.values()):
			context["sourcename"] = ""

	@readonly
	def ReportID(self) -> str:
		"""
		Read-only property to access the report's identifier (:attr:`_reportID`).

		:returns: The identifier of the report.
		"""
		return self._reportID

	@readonly
	def DocNames(self) -> list[str]:
		"""
		Read-only property to return the names of the generated documents.

		:returns: The document names, a testsuite before its testsuites and testcases.
		"""
		return list(self._documents)

	def Entry(self, entity: Testsuite | Testcase) -> Nullable[UnittestEntry]:
		"""
		Return the entry of a testsuite or testcase of this report.

		:param entity: The testsuite or testcase.
		:returns:      Its entry, or ``None`` if it has no page.
		"""
		return self._entries.get(id(entity), None)

	def Register(self, env: BuildEnvironment) -> None:
		"""
		Register the document names, with the report file as their source.

		:param env: The build environment.
		"""
		for docName in self._documents:
			env.project.docnames.add(docName)
			env.project._docname_to_path[docName] = self._xmlReport

	def Generate(self, sphinxApplication: Sphinx) -> None:
		"""
		Build the doctree of every page, have the environment collect it, and store it as if it was read.

		The event ``doctree-read`` is emitted per page, so the environment's collectors record its title, table of
		contents and metadata.

		:param sphinxApplication: Sphinx application instance.
		"""
		env = sphinxApplication.env
		domain: ReportDomain = env.domains[ReportDomain.name]  # type: ignore[assignment]

		self.Register(env)
		for docName, (roleName, entity) in self._documents.items():
			if roleName == "ts":
				section = self._TestsuitePage(docName, entity)
			else:
				section = self._TestcasePage(docName, entity)

			document = new_document(str(self._xmlReport))
			document.settings.env = env
			document.settings.record_dependencies = DependencyList()
			document += nodes.docinfo("", nodes.field("", nodes.field_name("", "orphan"), nodes.field_body()))
			document += section

			env.prepare_settings(docName)
			try:
				sphinxApplication.events.emit("doctree-read", document)
			finally:
				env.prepare_settings("")
				env.ref_context.clear()

			env.all_docs[docName] = time_ns() // 1_000
			domain.AddUnittestEntry(roleName, self._entries[id(entity)])
			sphinxApplication.builder.write_doctree(docName, document)

	def _Reference(self, roleName: str, entity: Testsuite | Testcase, docName: str) -> nodes.Node:
		"""
		Create a reference to the page of a testsuite or testcase, or its name if it has no page.

		:param roleName: The role referring to it: ``ts`` or ``tc``.
		:param entity:   The testsuite or testcase.
		:param docName:  Name of the document holding the reference.
		:returns:        The reference, or the name as text.
		"""
		if (entry := self.Entry(entity)) is None:
			return nodes.Text(entity._name)

		return UnittestSummary.CreateReference(roleName, entry, docName)

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

	def _Field(self, fieldList: nodes.field_list, name: str, *content: nodes.Node) -> None:
		"""
		Add a field to a page's summary.

		:param fieldList: The summary's field list.
		:param name:      The field's name.
		:param content:   The field's value.
		"""
		fieldList += nodes.field("", nodes.field_name(name, name), nodes.field_body("", nodes.paragraph("", "", *content)))

	def _Table(self, columns: list[tuple[str, int]], classes: list[str]) -> tuple[nodes.table, nodes.tbody]:
		"""
		Create a table with a header row.

		:param columns: One ``(title, width)`` pair per column.
		:param classes: CSS classes of the table.
		:returns:       The table, and its body the rows are added to.
		"""
		table = nodes.table("", classes=classes)
		table += (tableGroup := nodes.tgroup(cols=len(columns)))
		for _, width in columns:
			tableGroup += nodes.colspec(colwidth=width)

		tableGroup += (tableHeader := nodes.thead())
		tableHeader += (headerRow := nodes.row())
		for columnTitle, _ in columns:
			headerRow += nodes.entry("", nodes.paragraph(columnTitle, columnTitle))

		tableGroup += (tableBody := nodes.tbody())
		return table, tableBody

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
			toctree = addnodes.toctree(
				parent=docName, entries=[(None, child) for child in children], includefiles=children, maxdepth=1,
				caption=None, glob=False, hidden=True, includehidden=False, titlesonly=True, numbered=0
			)
			page.insert(page.index(summarySection), nodes.compound("", toctree, classes=["toctree-wrapper"]))

		return page
