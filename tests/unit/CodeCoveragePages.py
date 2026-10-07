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
Unit tests for :mod:`pyTooling.Sphinx.CodeCoveragePages`: pages per directory and source file, and role ``:cov:``.

The directive ``report:file-coverage`` and the syntax highlighting are tested too, each built in a small Sphinx project.
"""
from pathlib                           import Path
from textwrap                          import dedent
from typing                            import Any

from docutils                          import nodes
from sphinx                            import addnodes
from sphinx.testing.util               import SphinxTestApp

from pyTooling.Testing                 import testsuite, testcase

from pyTooling.Sphinx                  import ReportDomain
from pyTooling.Sphinx.CodeCoveragePages import tokenClass, tokenizeSource

from tests.unit.Extension              import Project


if __name__ == "__main__":  # pragma: no cover
	print("ERROR: you called a testcase declaration file as an executable module.")
	print("Use: 'python -m unittest <testcase module>'")
	exit(1)


DATA = Path(__file__).parent.parent / "data" / "CodeCoverage"
"""Directory of the code coverage reports and their sources."""

PYTHON_PAGES = "coverage/py/myPackage"
"""Document name of the generated page of directory 'myPackage' in the coverage.py report."""

VHDL_PAGES = "coverage/vhdl/src"
"""Document name of the generated page of directory 'src' in the VHDL report."""


class CoverageProject(Project):
	"""Base-class of the testcases: a project with a coverage.py report of Python and a Cobertura report of VHDL."""

	def _buildPages(self, index: str, builder: str = "html", **config: Any) -> SphinxTestApp:
		"""
		Write the document and build the project, with both reports declared with pages.

		:param index:   Content of the document ``index``.
		:param builder: Optional, name of the builder. Default: ``"html"``.
		:param config:  Configuration values overriding the defaults.
		:returns:       The Sphinx application after the build.
		"""
		packages = {
			"py": {
				"name": "myPackage", "json_report": str(DATA / "Python" / "coverage.json"), "sources": str(DATA / "Python"),
				"pages": "coverage/py", "fail_below": 80, "levels": "default"
			},
			"vhdl": {
				"name": "myDesign", "xml_report": str(DATA / "VHDL" / "Cobertura.xml"), "sources": str(DATA / "VHDL"),
				"pages": "/coverage/vhdl/", "fail_below": 80, "levels": "default"
			},
		}
		return self._build(index, builder, **({"pyTooling_CodeCoverage_Packages": packages} | config))

	def _body(self, name: str) -> str:
		"""
		Read the body of a built page, without the navigation.

		:param name: Name of the document.
		:returns:    The page's body.
		"""
		html = self._html(name)
		return html[html.index('<div class="body"'):html.index('<div class="sphinxsidebar"')]


@testsuite("Generated pages")
class Pages(CoverageProject):
	"""The pages per directory and source file, generated from a report declared with the key 'pages'."""

	@testcase("Document names")
	def DocNames(self) -> None:
		"""
		A page's document name is the 'pages' prefix followed by the path of its directory or file.

		Builds the project and checks the written files of both reports.
		"""
		self._buildPages("Index\n#####\n")

		self.assertEqual([], self._warningLines())
		html = self._path / "build" / "html"
		for docName in (
			PYTHON_PAGES, f"{PYTHON_PAGES}/Shapes.py", f"{PYTHON_PAGES}/Units", f"{PYTHON_PAGES}/Units/Length.py",
			VHDL_PAGES, f"{VHDL_PAGES}/Counter.vhdl", f"{VHDL_PAGES}/Utilities/Functions.vhdl"
		):
			with self.subTest(docName=docName):
				self.assertTrue((html / f"{docName}.html").exists())

	@testcase("Compacted directories")
	def CompactedDirectories(self) -> None:
		"""
		A chain of directories holding no file and one directory each is one page, named by the joined names.

		Builds a project with a Cobertura report of a file three directories deep, and checks its pages and the table.
		"""
		report = self._path / "coverage.xml"
		report.write_text(dedent("""\
			<coverage><packages><package name="p"><classes>
			<class filename="a/b/c/x.c"><lines><line number="1" hits="1"/></lines></class>
			<class filename="a/b/c/d/y.c"><lines><line number="1" hits="0"/></lines></class>
			</classes></package></packages></coverage>
			"""), encoding="utf-8")
		(self._path / "a" / "b" / "c" / "d").mkdir(parents=True)
		for name in ("a/b/c/x.c", "a/b/c/d/y.c"):
			(self._path / name).write_text("int main() {}\n", encoding="utf-8")

		self._build(
			"Index\n#####\n\n.. report:code-coverage::\n   :reportid: c\n",
			pyTooling_CodeCoverage_Packages={"c": {
				"name": "C", "xml_report": str(report), "sources": str(self._path), "pages": "cov", "fail_below": 80,
				"levels": "default"
			}}
		)

		self.assertEqual([], self._warningLines())
		html = self._path / "build" / "html"
		for docName in ("cov/a_b_c", "cov/a_b_c/x.c", "cov/a_b_c/d", "cov/a_b_c/d/y.c"):
			with self.subTest(docName=docName):
				self.assertTrue((html / f"{docName}.html").exists())
		self.assertIn(">a/b/c</span>", self._body("index"))
		self.assertIn("<h1>a/b/c", self._body("cov/a_b_c"))

	@testcase("File page")
	def FilePage(self) -> None:
		"""
		A file's page shows its counters, its missed lines and its listing: each line marked, with its number and ID.

		Builds the project and checks the page of 'Counter.vhdl', which has hits, a missed line and partial branches.
		"""
		self._buildPages("Index\n#####\n")

		body = self._body(f"{VHDL_PAGES}/Counter.vhdl")
		self.assertIn("<h1>Counter.vhdl", body)
		self.assertIn("7 of 8 covered (87.5%)", body)
		self.assertIn("6 of 8 taken (75.0%), 2 lines partially", body)
		self.assertIn("<p>27</p>", body)
		self.assertIn('href="../src.html"', body)
		self.assertIn('<div class="highlight-default notranslate report-coverage-listing', body)
		self.assertIn(
			'<div class="report-coverage-header"><span class="report-coverage-path">src/Counter.vhdl</span>'
			'<span class="report-coverage-legend"><span class="report-coverage-legend-covered">covered</span>', body
		)
		self.assertIn('<span class="report-coverage-legend-none">not executable</span></span></div>', body)
		self.assertIn(
			'<span class="report-line report-line-partial" id="L26" title="1 of 2 branches taken">'
			'<span class="linenos">26</span><span class="linenos report-hits">1024</span>', body
		)
		self.assertIn('<span class="report-line report-line-uncovered" id="L27">', body)
		self.assertIn(
			'<span class="report-line" id="L1"><span class="linenos">1</span><span class="linenos report-hits">', body
		)
		self.assertIn('<span class="k">library</span>', body)

	@testcase("File page of coverage.py")
	def FilePageCoveragePy(self) -> None:
		"""
		A coverage.py report has no hits, so the listing has no column of them; excluded lines are marked.

		Builds the project and checks the page of 'Shapes.py'.
		"""
		self._buildPages("Index\n#####\n")

		body = self._body(f"{PYTHON_PAGES}/Shapes.py")
		self.assertIn("<p>8, 25</p>", body)
		self.assertIn("Excluded lines", body)
		self.assertIn('<span class="report-line report-line-excluded" id="L28">', body)
		self.assertNotIn("report-hits", body)

	@testcase("Directory page")
	def DirectoryPage(self) -> None:
		"""
		A directory's page shows its counters, and tables of its directories and files, linked to their pages.

		Builds the project and checks the page of 'src'.
		"""
		self._buildPages("Index\n#####\n")

		body = self._body(VHDL_PAGES)
		self.assertIn("<h1>src", body)
		self.assertIn("<h2>Directories", body)
		self.assertIn("<h2>Files", body)
		self.assertIn('href="src/Utilities.html"><span class="xref report report-cov">Utilities</span>', body)
		self.assertIn('href="src/Counter.vhdl.html"><span class="xref report report-cov">Counter.vhdl</span>', body)

	@testcase("Summary table")
	def SummaryTable(self) -> None:
		"""
		The table of 'report:code-coverage' links every directory and file to its page.

		Builds the project with the VHDL report's table and checks its links.
		"""
		self._buildPages("Index\n#####\n\n.. report:code-coverage::\n   :reportid: vhdl\n")

		body = self._body("index")
		self.assertIn('class="report-directory report-cov-below80', body)
		for docName, name in (
			(VHDL_PAGES, "src"), (f"{VHDL_PAGES}/Utilities", "Utilities"),
			(f"{VHDL_PAGES}/Utilities/Functions.vhdl", "Functions.vhdl"), (f"{VHDL_PAGES}/Counter.vhdl", "Counter.vhdl")
		):
			with self.subTest(docName=docName):
				self.assertIn(f'href="{docName}.html"><span class="xref report report-cov">{name}</span>', body)

	@testcase("Navigation")
	def Navigation(self) -> None:
		"""
		The table's directive lists the top-level pages, a directory's page its children; sections aren't listed.

		Builds the project and checks the environment's table of contents.
		"""
		app = self._buildPages("Index\n#####\n\n.. report:code-coverage::\n   :reportid: vhdl\n")

		self.assertEqual([VHDL_PAGES], app.env.toctree_includes["index"])
		self.assertEqual(
			[f"{VHDL_PAGES}/Utilities", f"{VHDL_PAGES}/Counter.vhdl"], app.env.toctree_includes[VHDL_PAGES]
		)
		toc = app.env.tocs[f"{VHDL_PAGES}/Counter.vhdl"]
		self.assertEqual(1, len(list(toc.findall(nodes.reference))))
		self.assertNotIn("Summary", toc.astext())
		self.assertEqual(1, len(list(app.env.tocs[VHDL_PAGES].findall(addnodes.toctree))))

	@testcase("Stale source")
	def StaleSource(self) -> None:
		"""
		A report naming a line beyond the source file's end is warned about.

		Builds a project whose report names line 9 of a file with one line.
		"""
		report = self._path / "coverage.xml"
		report.write_text(
			'<coverage><packages><package name="p"><classes><class filename="x.c"><lines>'
			'<line number="9" hits="1"/></lines></class></classes></package></packages></coverage>',
			encoding="utf-8"
		)
		(self._path / "x.c").write_text("int main() {}\n", encoding="utf-8")

		self._build("Index\n#####\n", pyTooling_CodeCoverage_Packages={"c": {
			"name": "C", "xml_report": str(report), "sources": str(self._path), "pages": "cov", "fail_below": 80,
			"levels": "default"
		}})

		self.assertEqual(
			["WARNING: The code coverage report names line 9 of 'x.c', which has 1 lines: the report wasn't measured on "
			 "this version of the file."],
			self._warningLines()
		)

	@testcase("LaTeX")
	def LaTeX(self) -> None:
		"""
		A LaTeX build writes a listing as Sphinx writes highlighted code, each line's number colored by its state.

		Builds the VHDL report's table as LaTeX.
		"""
		self._buildPages("Index\n#####\n\n.. report:code-coverage::\n   :reportid: vhdl\n", "latex")

		self.assertEqual([], self._warningLines())
		latex = next((self._path / "build" / "latex").glob("*.tex")).read_text(encoding="utf-8")
		self.assertIn("\\begin{sphinxVerbatim}[commandchars=\\\\\\{\\}]", latex)
		self.assertIn("\\textcolor{orange}{26 ~} ", latex)
		self.assertIn("\\textcolor{red}{27 -} ", latex)
		self.assertIn("\\sphinxcode{src/Counter.vhdl}\\hfill{}", latex)
		self.assertIn("\\textcolor{orange}{\\texttt{\\PYGZti{}}}~partial", latex)
		self.assertIn("\\PYG{k}{if}", latex)


@testsuite("Role ':cov:'")
class Role(CoverageProject):
	"""The role referring to a directory or file, by path or a suffix of it, optionally to a line."""

	_document = dedent("""\
		Index
		#####

		* :cov:`Shapes.py`
		* :cov:`vhdl:Counter.vhdl`
		* :cov:`vhdl:Utilities/Functions.vhdl`
		* :cov:`vhdl:src/Utilities`
		* :cov:`vhdl:Counter.vhdl#27`
		* :cov:`the counter <vhdl:src/Counter.vhdl#26>`
		* :report:cov:`Units/Length.py`
		""")

	@testcase("Resolution")
	def Resolution(self) -> None:
		"""
		A reference names a path or a suffix of it, with or without report ID, and may link to a line.

		Builds the document and checks every link.
		"""
		self._buildPages(self._document)

		self.assertEqual([], self._warningLines())
		body = self._body("index")
		for href, text in (
			(f"{PYTHON_PAGES}/Shapes.py.html", "Shapes.py"),
			(f"{VHDL_PAGES}/Counter.vhdl.html", "Counter.vhdl"),
			(f"{VHDL_PAGES}/Utilities/Functions.vhdl.html", "Functions.vhdl"),
			(f"{VHDL_PAGES}/Utilities.html", "Utilities"),
			(f"{VHDL_PAGES}/Counter.vhdl.html#L27", "Counter.vhdl:27"),
			(f"{VHDL_PAGES}/Counter.vhdl.html#L26", "the counter"),
			(f"{PYTHON_PAGES}/Units/Length.py.html", "Length.py"),
		):
			with self.subTest(text=text):
				self.assertIn(f'href="{href}"><span class="xref report report-cov">{text}</span>', body)

	@testcase("Unknown and ambiguous")
	def UnknownAndAmbiguous(self) -> None:
		"""
		An unknown path and a name of two files are warned about.

		Builds a document with both references and checks the warnings.
		"""
		self._buildPages("Index\n#####\n\n* :cov:`Missing.py`\n* :cov:`__init__.py`\n")

		warnings = self._warningLines()
		self.assertEqual(2, len(warnings))
		self.assertIn("source 'Missing.py' not found in the code coverage reports", warnings[0])
		self.assertIn(
			"source '__init__.py' is ambiguous, candidates: py:myPackage/Units/__init__.py, py:myPackage/__init__.py",
			warnings[1]
		)

	@testcase("Domain objects")
	def DomainObjects(self) -> None:
		"""
		Every directory and file with a page is an object of type 'source', named by report ID and path.

		Builds the project and checks the domain's objects.
		"""
		app = self._buildPages("Index\n#####\n")
		domain: ReportDomain = app.env.domains[ReportDomain.name]

		objects = {name: (objectType, docName) for name, _, objectType, docName, _, _ in domain.get_objects()}
		self.assertEqual(("source", f"{VHDL_PAGES}/Counter.vhdl"), objects["vhdl:src/Counter.vhdl"])
		self.assertEqual(("source", PYTHON_PAGES), objects["py:myPackage"])
		self.assertEqual(6 + 4, sum(1 for name in objects if name.startswith(("py:", "vhdl:"))))


@testsuite("Directive 'report:file-coverage'")
class FileCoverage(CoverageProject):
	"""A source file's listing, written where the directive is."""

	@testcase("Listing")
	def Listing(self) -> None:
		"""
		The directive writes a file's listing, without line IDs, from a report without pages.

		Builds the Python Cobertura report's file 'Units/Length.py'.
		"""
		self._build(
			"Index\n#####\n\n.. report:file-coverage:: Units/Length.py\n   :reportid: pyx\n",
			pyTooling_CodeCoverage_Packages={"pyx": {
				"name": "myPackage", "xml_report": str(DATA / "Python" / "coverage.xml"),
				"sources": str(DATA / "Python" / "myPackage"), "fail_below": 80, "levels": "default"
			}}
		)

		self.assertEqual([], self._warningLines())
		body = self._body("index")
		self.assertIn('<span class="report-line report-line-uncovered"><span class="linenos">14</span>', body)
		self.assertNotIn('id="L', body)

	@testcase("Unknown file")
	def UnknownFile(self) -> None:
		"""
		A file the report doesn't have is reported as an error on the page.

		Builds the directive naming a file the report doesn't have.
		"""
		self._buildPages("Index\n#####\n\n.. report:file-coverage:: Missing.py\n   :reportid: py\n")

		self.assertIn("ERROR: Code coverage report has no file 'Missing.py'.", "\n".join(self._warningLines()))


@testsuite("Syntax highlighting")
class Highlighting(CoverageProject):
	"""Lexing a source file with Pygments, into lines of tokens with Pygments' CSS classes."""

	@testcase("Token classes")
	def TokenClasses(self) -> None:
		"""
		A token type gets its short class, or its nearest parent's extended by the names below it.

		Checks a keyword, plain text and a token type without a class of its own.
		"""
		from pygments.token import Keyword, Name, Text

		self.assertEqual("k", tokenClass(Keyword))
		self.assertEqual("", tokenClass(Text))
		self.assertEqual("n-Unknown", tokenClass(Name.Unknown))

	@testcase("Multi-line token")
	def MultiLineToken(self) -> None:
		"""
		A doc-string spanning lines is split at the line ends, each part keeping its class.

		Lexes a function with a two-line doc-string.
		"""
		lines = tokenizeSource('def f():\n\t"""One.\n\tTwo."""\n', "x.py")

		self.assertEqual(3, len(lines))
		self.assertIn(("sd", "Two.\"\"\""), [(cssClass, text.strip()) for cssClass, text in lines[2]])

	@testcase("Unknown file type")
	def UnknownFileType(self) -> None:
		"""
		A file name without a lexer is lexed as plain text.

		Lexes a file with an unknown extension.
		"""
		self.assertEqual([[("", "some text")]], tokenizeSource("some text\n", "x.unknown-extension"))
