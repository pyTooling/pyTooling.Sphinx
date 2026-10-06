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
Unit tests for :mod:`pyTooling.Sphinx.UnittestPages`: the pages per testsuite and testcase, and the roles ``:tc:`` and
``:ts:`` referring to them, each built in a small Sphinx project.
"""
from pathlib                       import Path
from textwrap                      import dedent
from typing                        import Any

from sphinx.testing.util           import SphinxTestApp

from pyTooling.Sphinx              import ReportDomain, UnittestEntry
from pyTooling.Sphinx.Unittest     import UnittestSummary
from pyTooling.Sphinx.UnittestPages import UnittestReportPages
from pyTooling.Testing             import testsuite, testcase

from tests.unit.Extension          import Project


if __name__ == "__main__":  # pragma: no cover
	print("ERROR: you called a testcase declaration file as an executable module.")
	print("Use: 'python -m unittest <testcase module>'")
	exit(1)


DATA = Path(__file__).parent.parent / "data" / "Report"
"""Directory of the report files the testcases read."""

JUNIT_PAGES = "unittests/ut/pytest/tests/unit/Arithmetic"
"""Document name of the generated page of testsuite 'Arithmetic' in the JUnit report."""

PYTOOLING_PAGES = "unittests/pyt/tests/unit/Arithmetic"
"""Document name of the generated page of testsuite 'Arithmetic' in the pyTooling report."""


class PagesProject(Project):
	"""Base-class of the testcases: a Sphinx project with a JUnit and a pyTooling report, both with pages."""

	def _buildPages(self, index: str, builder: str = "html", **config: Any) -> SphinxTestApp:
		"""
		Write the document and build the project, with the two reports declared with pages.

		:param index:   Content of the document ``index``.
		:param builder: Optional, name of the builder. Default: ``"html"``.
		:param config:  Configuration values overriding the defaults.
		:returns:       The Sphinx application after the build.
		"""
		testsuites = {
			"ut":  {"xml_report": str(DATA / "unittest.xml"),   "pages": "unittests/ut"},
			"pyt": {"xml_report": str(DATA / "TestReport.xml"), "pages": "/unittests/pyt/"},
		}
		return self._build(index, builder, **({"pyTooling_Unittest_Testsuites": testsuites} | config))

	def _body(self, name: str) -> str:
		"""
		Read the body of a built page, without the navigation.

		:param name: Name of the document.
		:returns:    The page's body.
		"""
		html = self._html(name)
		return html[html.index('<div class="body"'):html.index('<div class="sphinxsidebar"')]


@testsuite("Generated pages")
class Pages(PagesProject):
	"""The pages per testsuite and testcase, generated from a report declared with the key 'pages'."""

	@testcase("Document names")
	def DocNames(self) -> None:
		"""
		A page's document name is the 'pages' prefix followed by the names of its testsuites, and its own name.

		Builds the project and checks the written files of both reports.
		"""
		self._buildPages("Index\n#####\n")

		self.assertEqual([], self._warningLines())
		html = self._path / "build" / "html"
		for docName in (
			"unittests/ut/pytest", f"{JUNIT_PAGES}", f"{JUNIT_PAGES}/Division", f"{JUNIT_PAGES}/Division/test_ByZero",
			f"{PYTOOLING_PAGES}/Addition/OnePlusOne"
		):
			with self.subTest(docName=docName):
				self.assertTrue((html / f"{docName}.html").exists())

		self.assertFalse((html / "_sources" / f"{JUNIT_PAGES}.html.txt").exists())

	@testcase("Testcase page")
	def TestcasePage(self) -> None:
		"""
		A testcase's page shows its status, duration and testsuite, its message and its captured output.

		Builds the project and checks the page of a failed testcase with output.
		"""
		self._buildPages("Index\n#####\n")

		body = self._body(f"{JUNIT_PAGES}/Division/test_ByZero")
		self.assertIn("<h1>test_ByZero", body)
		self.assertIn("<h2>Summary", body)
		self.assertIn("❌ Failed", body)
		self.assertIn("00:00:00.070", body)
		self.assertIn(
			'<a class="reference internal" href="../Division.html"><span class="xref report report-ts">Division</span></a>',
			body
		)
		self.assertIn("AssertionError: ZeroDivisionError not raised", body)
		self.assertIn("Traceback (most recent call last): ...", body)
		self.assertIn("<h2>Output", body)
		self.assertIn("dividing 1 by 0", body)
		self.assertIn("<h2>Error Output", body)
		self.assertIn("warning: division by zero", body)
		self.assertNotIn("Assertions", body)

	@testcase("Testcase page without output")
	def TestcasePageWithoutOutput(self) -> None:
		"""
		A passed testcase's page has no message and no output sections.

		Builds the project and checks the page of a passed testcase without output.
		"""
		self._buildPages("Index\n#####\n")

		body = self._body(f"{JUNIT_PAGES}/Addition/test_Negative")
		self.assertIn("✅ Passed", body)
		self.assertNotIn("<h2>Message", body)
		self.assertNotIn("<h2>Output", body)
		self.assertNotIn("<h2>Error Output", body)

	@testcase("Testsuite page")
	def TestsuitePage(self) -> None:
		"""
		A testsuite's page shows its status and counts, and tables of its testsuites and testcases linked to their pages.

		Builds the project and checks the pages of 'Division' and 'Arithmetic'.
		"""
		self._buildPages("Index\n#####\n")

		body = self._body(f"{JUNIT_PAGES}/Division")
		self.assertIn("❗ Errored", body)
		self.assertIn("3 - 0 passed, 1 failed, 1 errored, 1 skipped", body)
		self.assertIn("<h2>Testcases", body)
		for testcaseName in ("test_ByZero", "test_Fraction", "test_Rounding"):
			with self.subTest(testcase=testcaseName):
				self.assertIn(
					f'href="Division/{testcaseName}.html"><span class="xref report report-tc">{testcaseName}</span>', body
				)

		body = self._body(JUNIT_PAGES)
		self.assertIn("<h2>Testsuites", body)
		self.assertIn('href="Arithmetic/Addition.html"><span class="xref report report-ts">Addition</span>', body)
		self.assertIn('href="Arithmetic/Division.html"><span class="xref report report-ts">Division</span>', body)

	@testcase("Navigation")
	def Navigation(self) -> None:
		"""
		A testsuite's page lists its children in a hidden table of contents, so the navigation works below it.

		Builds the project and checks the environment's table of contents and the pages' metadata.
		"""
		app = self._buildPages("Index\n#####\n")

		self.assertEqual(
			[f"{JUNIT_PAGES}/Division/{name}" for name in ("test_ByZero", "test_Fraction", "test_Rounding")],
			app.env.toctree_includes[f"{JUNIT_PAGES}/Division"]
		)
		self.assertIn("orphan", app.env.metadata[f"{JUNIT_PAGES}/Division/test_ByZero"])
		self.assertEqual("test_ByZero", app.env.titles[f"{JUNIT_PAGES}/Division/test_ByZero"].astext())

	@testcase("pyTooling report")
	def pyToolingReport(self) -> None:
		"""
		A page of a pyTooling report shows the title, summary and description below the name.

		Builds the project and checks the pages of testsuite 'Addition' and testcase 'OnePlusOne'.
		"""
		self._buildPages("Index\n#####\n")

		body = self._body(f"{PYTOOLING_PAGES}/Addition")
		self.assertIn("<h1>Addition", body)
		self.assertIn('<p class="report-unittest-title"><strong>Addition of integers</strong></p>', body)
		self.assertIn('<p class="report-unittest-summary">Add two integers.</p>', body)
		self.assertIn(
			'<p class="report-unittest-description">Every testcase adds two small integers and checks the sum.</p>', body
		)

		body = self._body(f"{PYTOOLING_PAGES}/Addition/OnePlusOne")
		self.assertIn('<p class="report-unittest-title"><strong>One plus one is two.</strong></p>', body)
		self.assertNotIn('class="report-unittest-summary"', body)
		self.assertIn('<p class="report-unittest-description">The simplest addition there is.</p>', body)

		body = self._body(f"{PYTOOLING_PAGES}/Addition/OnePlusTwo")
		self.assertIn("E    AssertionError: 4 != 3", body)

	@testcase("No pages without the key 'pages'")
	def NoPages(self) -> None:
		"""
		A report without the key 'pages' gets neither pages nor objects, and its summary table doesn't link.

		Builds a unit test summary of a report declared without 'pages'.
		"""
		app = self._build(
			"Index\n#####\n\n.. report:unittest-summary::\n   :reportid: ut\n",
			pyTooling_Unittest_Testsuites={"ut": {"xml_report": str(DATA / "unittest.xml")}}
		)

		self.assertEqual([], self._warningLines())
		self.assertFalse((self._path / "build" / "html" / "unittests").exists())
		domainData = app.env.domains[ReportDomain.name].data
		self.assertEqual({}, domainData["testcases"])
		self.assertEqual({}, domainData["testsuites"])
		self.assertNotIn("report-tc", self._html("index"))

	@testcase("Unreadable report")
	def UnreadableReport(self) -> None:
		"""
		A report with pages that can't be read gets no pages; the error is logged, and the summary shows it.

		Builds a unit test summary of a file whose root element is no report format.
		"""
		report = self._path / "unknown.xml"
		report.write_text("<results />\n", encoding="utf-8")

		self._build(
			"Index\n#####\n\n.. report:unittest-summary::\n   :reportid: bad\n",
			pyTooling_Unittest_Testsuites={"bad": {"xml_report": str(report), "pages": "unittests/bad"}}
		)

		warnings = self._warningLines()
		self.assertEqual(
			"ERROR: Caught ReportExtensionError when generating the pages of unittest report 'bad'.", warnings[0]
		)
		self.assertEqual("  ReportExtensionError: Unittest report 'unknown.xml' has an unknown format.", warnings[1])
		self.assertIn("ERROR: Caught ReportExtensionError when reading and parsing 'unknown.xml'.", warnings)
		self.assertIn("ERROR:     Got root element '<results>'; supported: testsuites, testsuite, TestReport", warnings)
		self.assertFalse((self._path / "build" / "html" / "unittests").exists())

	@testcase("Summary table links")
	def SummaryLinks(self) -> None:
		"""
		The unit test summary links a testsuite's and a testcase's name to its page, showing the title on hover.

		Builds a unit test summary of both reports.
		"""
		self._buildPages(dedent("""\
			Index
			#####

			.. report:unittest-summary::
			   :reportid: ut

			.. report:unittest-summary::
			   :reportid: pyt
		"""))

		self.assertEqual([], self._warningLines())
		body = self._body("index")
		self.assertIn(
			f'❌<a class="reference internal" href="{JUNIT_PAGES}/Division/test_ByZero.html">'
			f'<span class="xref report report-tc">test_ByZero</span></a>',
			body
		)
		self.assertIn(
			f'<a class="reference internal" href="{PYTOOLING_PAGES}/Addition.html" title="Addition of integers">', body
		)

	@testcase("LaTeX")
	def LaTeX(self) -> None:
		"""
		A LaTeX build succeeds; it doesn't write the pages, so a reference to one shows the name without a link.

		Builds the summary and a role as LaTeX.
		"""
		self._buildPages(
			"Index\n#####\n\n.. report:unittest-summary::\n   :reportid: ut\n\nSee :tc:`ut:Division.test_ByZero`.\n", "latex"
		)

		self.assertEqual([], self._warningLines())
		latex = next((self._path / "build" / "latex").glob("*.tex")).read_text(encoding="utf-8")
		self.assertIn("See \\DUrole{xref}{\\DUrole{report}{\\DUrole{report-tc}{test\\_ByZero}}}.", latex)


@testsuite("Roles ':tc:' and ':ts:'")
class Roles(PagesProject):
	"""The roles referring to a testcase or testsuite, with or without a report ID, and in domain 'report'."""

	_document = dedent("""\
		Index
		#####

		* :tc:`test_ByZero`
		* :tc:`ut:Division.test_Fraction`
		* :tc:`ut:pytest.tests.unit.Arithmetic.Division.test_Rounding`
		* :ts:`Arithmetic`
		* :tc:`pyt:OnePlusTwo`
		* :report:ts:`pyt:Addition`
		* :report:tc:`Positive case <test_Positive>`
	""")

	@testcase("Resolution")
	def Resolution(self) -> None:
		"""
		A reference resolves by qualified name or unique suffix, in the default report or the one named by its ID.

		Builds a document with references to both reports and checks the links.
		"""
		self._buildPages(self._document)

		self.assertEqual([], self._warningLines())
		body = self._body("index")
		for href, text in (
			(f"{JUNIT_PAGES}/Division/test_ByZero.html", '<span class="xref report report-tc">test_ByZero</span>'),
			(f"{JUNIT_PAGES}/Division/test_Fraction.html", '<span class="xref report report-tc">test_Fraction</span>'),
			(f"{JUNIT_PAGES}/Division/test_Rounding.html", '<span class="xref report report-tc">test_Rounding</span>'),
			(f"{JUNIT_PAGES}.html", '<span class="xref report report-ts">Arithmetic</span>'),
			(f"{PYTOOLING_PAGES}/Addition/OnePlusTwo.html", '<span class="xref report report-tc">OnePlusTwo</span>'),
			(f"{PYTOOLING_PAGES}/Addition.html", '<span class="xref report report-ts">Addition</span>'),
			(f"{JUNIT_PAGES}/Addition/test_Positive.html", '<span class="xref report report-tc">Positive case</span>'),
		):
			with self.subTest(href=href):
				self.assertRegex(body, rf'<a class="reference internal" href="{href}"( title="[^"]*")?>{text}</a>')

	@testcase("Unknown target")
	def Unknown(self) -> None:
		"""
		A reference to an unknown testcase or testsuite is warned about; a testcase of another report needs its ID.

		Builds a document with an unknown testcase, a testcase of the second report without ID, and an unknown testsuite.
		"""
		self._buildPages("Index\n#####\n\n:tc:`test_Unknown` :tc:`OnePlusOne` :ts:`pyt:Unknown`\n")

		self.assertEqual(
			[
				"src/index.rst:4: WARNING: testcase 'test_Unknown' not found in the unit test reports [ref.tc]",
				"src/index.rst:4: WARNING: testcase 'OnePlusOne' not found in the unit test reports [ref.tc]",
				"src/index.rst:4: WARNING: testsuite 'pyt:Unknown' not found in the unit test reports [ref.ts]",
			],
			self._warningLines()
		)

	@testcase("Ambiguous target")
	def Ambiguous(self) -> None:
		"""
		A suffix matching several testcases is warned about, naming the candidates, and shown as text.

		Builds a document referring to a testcase name two testsuites have.
		"""
		report = self._path / "ambiguous.xml"
		report.write_text(dedent("""\
			<?xml version="1.0" encoding="utf-8"?>
			<testsuites name="pytest tests">
			  <testsuite name="pytest" tests="2" failures="0" errors="0" skipped="0" time="0.1" hostname="localhost">
			    <testcase classname="tests.First" name="test_Same" time="0.050"/>
			    <testcase classname="tests.Second" name="test_Same" time="0.050"/>
			  </testsuite>
			</testsuites>
		"""), encoding="utf-8")

		self._build(
			"Index\n#####\n\n:tc:`test_Same` :tc:`First.test_Same`\n",
			pyTooling_Unittest_Testsuites={"amb": {"xml_report": str(report), "pages": "unittests/amb"}}
		)

		self.assertEqual(
			[
				"src/index.rst:4: WARNING: testcase 'test_Same' is ambiguous, candidates: "
				"amb:pytest.tests.First.test_Same, amb:pytest.tests.Second.test_Same [ref.tc]"
			],
			self._warningLines()
		)
		self.assertIn('href="unittests/amb/pytest/tests/First/test_Same.html"', self._html("index"))

	@testcase("Objects")
	def Objects(self) -> None:
		"""
		The testsuites and testcases with pages are objects of domain 'report', named '<report ID>:<qualified name>'.

		Builds the project and checks the domain's objects.
		"""
		app = self._buildPages("Index\n#####\n")

		domain: ReportDomain = app.env.domains[ReportDomain.name]
		objects = {name: (objectType, docName) for name, _, objectType, docName, _, _ in domain.get_objects()}
		self.assertEqual(
			("testcase", f"{JUNIT_PAGES}/Division/test_ByZero"),
			objects["ut:pytest.tests.unit.Arithmetic.Division.test_ByZero"]
		)
		self.assertEqual(("testsuite", PYTOOLING_PAGES), objects["pyt:tests.unit.Arithmetic"])
		self.assertEqual(5 + 6, sum(1 for objectType, _ in objects.values() if objectType == "testcase"))


@testsuite("Domain data")
class DomainData(PagesProject):
	"""The objects in the domain's data, forgotten per document and merged from a parallel reader."""

	@testcase("Clear a document")
	def ClearDoc(self) -> None:
		"""
		Clearing a generated document forgets its object, and only that one.

		Builds the project and clears the page of one testcase.
		"""
		app = self._buildPages("Index\n#####\n")
		domain: ReportDomain = app.env.domains[ReportDomain.name]

		domain.clear_doc(f"{JUNIT_PAGES}/Division/test_ByZero")

		self.assertEqual([], domain.FindUnittestEntries("tc", "test_ByZero"))
		self.assertEqual(1, len(domain.FindUnittestEntries("tc", "test_Fraction")))

	@testcase("Merge a parallel reader's data")
	def MergeDomainData(self) -> None:
		"""
		Merging takes over the objects of the documents the other reader read, and only those.

		Builds the project, and merges data holding two testcases, of which one document was read.
		"""
		app = self._buildPages("Index\n#####\n")
		domain: ReportDomain = app.env.domains[ReportDomain.name]

		read = UnittestEntry("other/read", "ut", ("other", "test_Read"), None)
		unread = UnittestEntry("other/unread", "ut", ("other", "test_Unread"), None)
		domain.merge_domaindata(
			["other/read"],
			{"testcases": {"ut": {"other.test_Read": read, "other.test_Unread": unread}}, "testsuites": {}}
		)

		self.assertEqual([read], domain.FindUnittestEntries("tc", "test_Read"))
		self.assertEqual([], domain.FindUnittestEntries("tc", "test_Unread"))


@testsuite("Configuration key 'pages'")
class Configuration(Project):
	"""The key 'pages' of a report's configuration."""

	def _check(self, pages: Any) -> list[str]:
		"""
		Build a project declaring a report with the given 'pages' and return the warnings.

		:param pages: The value of the key 'pages'.
		:returns:     The warnings.
		"""
		self._build(
			"Index\n#####\n", pyTooling_Unittest_Testsuites={"ut": {"xml_report": str(DATA / "unittest.xml"), "pages": pages}}
		)
		return self._warningLines()

	@testcase("Normalized")
	def Normalized(self) -> None:
		"""
		Surrounding slashes are removed from the document name.

		Checks the loaded configuration after a build with '/unittests/ut/'.
		"""
		self.assertEqual([], self._check("/unittests/ut/"))
		self.assertEqual("unittests/ut", UnittestSummary._testSummaries["ut"]["pages"])
		self.assertIsNotNone(UnittestReportPages.GetPages("ut"))

	@testcase("Not a relative document name")
	def Invalid(self) -> None:
		"""
		A document name with '..', an empty part or a backslash is logged as an error.

		Builds projects with 'unittests/../ut', 'unittests//ut' and 'unittests\\ut'.
		"""
		for pages in ("unittests/../ut", "unittests//ut", "unittests\\ut"):
			with self.subTest(pages=pages):
				self.assertEqual(
					[
						"ERROR: Caught ReportExtensionError when checking configuration variables.",
						f"  conf.py: pyTooling_Unittest_Testsuites:[ut].pages: '{pages}' is not a relative document name."
					],
					self._check(pages)
				)

	@testcase("Not a string")
	def NotAString(self) -> None:
		"""
		A document name that isn't a string is logged as an error.

		Builds a project with 'pages' set to a number.
		"""
		self.assertEqual(
			[
				"ERROR: Caught ReportExtensionError when checking configuration variables.",
				"  conf.py: pyTooling_Unittest_Testsuites:[ut].pages: Document name is not a string."
			],
			self._check(1)
		)
