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
Unit tests for :mod:`pyTooling.Sphinx.DocCoverage`: pages per package and module, the condensed listing, and role
``:doccov:``, each built in a small Sphinx project.
"""
from pathlib                          import Path
from textwrap                         import dedent
from typing                           import Any

from docutils                         import nodes
from sphinx                           import addnodes
from sphinx.testing.util              import SphinxTestApp

from pyTooling.Testing                import testsuite, testcase

from pyTooling.Sphinx                 import ReportDomain
from pyTooling.Sphinx.CondensedSource import CondensedSource, documentationState
from pyTooling.Sphinx.DocCoverage     import DocCoverageBase, DocCoverageReportPages

from tests.unit.Extension             import Project


if __name__ == "__main__":  # pragma: no cover
	print("ERROR: you called a testcase declaration file as an executable module.")
	print("Use: 'python -m unittest <testcase module>'")
	exit(1)


PACKAGE = Path(__file__).parent.parent / "data" / "DocCoverage" / "myPackage"
"""Directory of the fixture package, which the testcases analyze."""

PAGES = "doccov/myPackage"
"""Document name of the generated page of the fixture package."""


class DocCoverageProject(Project):
	"""Base-class of the testcases: a project analyzing the fixture package 'myPackage'."""

	def _buildPages(self, index: str, builder: str = "html", pages: Any = "doccov") -> SphinxTestApp:
		"""
		Write the document and build the project, with the fixture package declared with pages.

		:param index:   Content of the document ``index``.
		:param builder: Optional, name of the builder. Default: ``"html"``.
		:param pages:   Optional, the value of the key ``pages``. Default: ``"doccov"``.
		:returns:       The Sphinx application after the build.
		"""
		packages = {
			"doc": {"name": "myPackage", "directory": str(PACKAGE), "pages": pages, "fail_below": 80, "levels": "default"}
		}
		return self._build(index, builder, pyTooling_DocCoverage_Packages=packages)

	def _buildPackage(self, files: dict[str, bytes]) -> Path:
		"""
		Write a package's files and build the project with the package declared with pages below 'doccov'.

		:param files: The files' contents, by their path relative to the package's directory.
		:returns:     The package's directory, named 'pkg'.
		"""
		package = self._path / "pkg"
		for path, content in files.items():
			(package / path).parent.mkdir(parents=True, exist_ok=True)
			(package / path).write_bytes(content)

		self._build(
			"Index\n#####\n\n.. report:doc-coverage::\n   :reportid: doc\n",
			pyTooling_DocCoverage_Packages={
				"doc": {"name": "pkg", "directory": str(package), "pages": "doccov", "fail_below": 80, "levels": "default"}
			}
		)

		return package

	def _body(self, name: str) -> str:
		"""
		Read the body of a built page, without the navigation.

		:param name: Name of the document.
		:returns:    The page's body.
		"""
		html = self._html(name)
		return html[html.index('<div class="body"'):html.index('<div class="sphinxsidebar"')]


@testsuite("Generated pages")
class Pages(DocCoverageProject):
	"""The pages per package and module, generated for a package declared with the key 'pages'."""

	@testcase("Document names")
	def DocNames(self) -> None:
		"""
		A page's document name is the 'pages' prefix followed by the package's and module's names.

		Builds the project and checks the written files.
		"""
		self._buildPages("Index\n#####\n")

		self.assertEqual([], self._warningLines())
		html = self._path / "build" / "html"
		for docName in (PAGES, f"{PAGES}/Shapes", f"{PAGES}/Units", f"{PAGES}/Units/Length"):
			with self.subTest(docName=docName):
				self.assertTrue((html / f"{docName}.html").exists())

	@testcase("Package page")
	def PackagePage(self) -> None:
		"""
		A package's page shows its counters - its '__init__.py' and overall -, tables of its packages and modules linked
		to their pages, and its '__init__.py' condensed.

		Builds the project and checks the page of 'myPackage'.
		"""
		self._buildPages("Index\n#####\n")

		body = self._body(PAGES)
		self.assertIn("<h1>myPackage", body)
		self.assertIn("<h2>Packages", body)
		self.assertIn("<h2>Modules", body)
		self.assertIn('class="report-doccov-table report-doccov-summary docutils', body)
		self.assertIn('<tr class="report-cov-below100 row-even"><td><p>__init__.py</p></td>', body)
		self.assertIn('<tr class="report-summary report-cov-below70 row-odd"><td><p>Overall (4 files)</p></td>', body)
		self.assertIn('href="myPackage/Units.html"><span class="xref report report-doccov">Units</span>', body)
		self.assertIn('href="myPackage/Shapes.html"><span class="xref report report-doccov">Shapes</span>', body)
		self.assertIn('<span class="report-coverage-path">myPackage/__init__.py</span>', body)

	@testcase("Module page")
	def ModulePage(self) -> None:
		"""
		A module's page shows its package, its doc-string's state, its counters and its condensed listing with a legend.

		Builds the project and checks the page of 'Shapes'.
		"""
		self._buildPages("Index\n#####\n")

		body = self._body(f"{PAGES}/Shapes")
		self.assertIn("<h1>Shapes", body)
		self.assertIn('href="../myPackage.html"', body)
		self.assertIn("<p>documented</p>", body)
		self.assertIn(
			'<tr class="report-cov-below70 row-even"><td><p>Shapes.py</p></td>\n<td><p>14</p></td>\n<td><p>9</p></td>\n'
			'<td><p>5</p></td>\n<td><p>64.3%</p></td>', body
		)
		self.assertIn('<div class="highlight-default notranslate report-coverage-listing', body)
		self.assertIn(
			'<div class="report-coverage-header"><span class="report-coverage-path">myPackage/Shapes.py</span>'
			'<span class="report-coverage-legend"><span class="report-coverage-legend-documented">documented</span>', body
		)
		self.assertIn('<span class="report-coverage-legend-none">not counted</span></span></div>', body)
		self.assertNotIn("<h2>Modules", body)

	@testcase("Undocumented module doc-string")
	def UndocumentedDocString(self) -> None:
		"""
		A module without doc-string has a summary saying so.

		Builds the project and checks the page of 'Units', whose '__init__.py' has no doc-string.
		"""
		self._buildPages("Index\n#####\n")

		self.assertIn("<p>undocumented</p>", self._body(f"{PAGES}/Units"))

	@testcase("Summary table")
	def SummaryTable(self) -> None:
		"""
		The table of 'report:doc-coverage' links every package and module to its page.

		Builds the project with the table and checks its links.
		"""
		self._buildPages("Index\n#####\n\n.. report:doc-coverage::\n   :reportid: doc\n")

		self.assertEqual([], self._warningLines())
		body = self._body("index")
		for docName, name in (
			(PAGES, "myPackage"), (f"{PAGES}/Units", "Units"), (f"{PAGES}/Units/Length", "Length"),
			(f"{PAGES}/Shapes", "Shapes")
		):
			with self.subTest(docName=docName):
				self.assertIn(f'href="{docName}.html"><span class="xref report report-doccov">{name}</span>', body)

	@testcase("Dotted root name")
	def DottedRootName(self) -> None:
		"""
		A root package with a dotted name - e.g. a namespace package's sub-package - keeps it as one name.

		Builds the table of the fixture package named 'tests.myPackage' and a reference to one of its modules.
		"""
		self._build(
			"Index\n#####\n\n.. report:doc-coverage::\n   :reportid: doc\n\n* :doccov:`tests.myPackage.Shapes`\n",
			pyTooling_DocCoverage_Packages={"doc": {
				"name": "tests.myPackage", "directory": str(PACKAGE), "pages": "doccov", "fail_below": 80, "levels": "default"
			}}
		)

		self.assertEqual([], self._warningLines())
		body = self._body("index")
		for href, text in (
			("doccov/tests.myPackage.html", "tests.myPackage"), ("doccov/tests.myPackage/Shapes.html", "Shapes")
		):
			with self.subTest(text=text):
				self.assertIn(f'href="{href}"><span class="xref report report-doccov">{text}</span>', body)
		self.assertIn("<h1>tests.myPackage", self._body("doccov/tests.myPackage"))

	@testcase("Namespace package")
	def NamespacePackage(self) -> None:
		"""
		A namespace package - a directory without '__init__.py' - has nothing to document: its row counts no items, its
		page shows only the overall counters, and its directory is its page's source.

		Builds the table of a package with a namespace sub-package holding a module.
		"""
		package = self._path / "spaced"
		(package / "Space").mkdir(parents=True)
		(package / "__init__.py").write_text('"""A package."""\n', encoding="utf-8")
		(package / "Space" / "Inner.py").write_text('"""A module."""\nX = 1\n', encoding="utf-8")

		app = self._build(
			"Index\n#####\n\n.. report:doc-coverage::\n   :reportid: doc\n",
			pyTooling_DocCoverage_Packages={
				"doc": {"name": "spaced", "directory": str(package), "pages": "doccov", "fail_below": 80, "levels": "default"}
			}
		)

		self.assertEqual([], self._warningLines())
		self.assertIn(
			'<span class="xref report report-doccov">Space</span></a></span></td>\n<td>0</td>\n<td>0</td>\n<td>0</td>\n'
			'<td>100.0%</td>', self._body("index")
		)
		body = self._body("doccov/spaced/Space")
		self.assertIn('<tr class="report-summary report-cov-below60 row-even"><td><p>Overall (1 files)</p></td>', body)
		self.assertNotIn("Doc-string", body)
		self.assertNotIn('id="source"', body)
		self.assertEqual(package.resolve() / "Space", app.env.doc2path("doccov/spaced/Space"))

	@testcase("Navigation")
	def Navigation(self) -> None:
		"""
		The table's directive lists the package's page, a package's page its children; sections aren't listed.

		Builds the project and checks the environment's table of contents.
		"""
		app = self._buildPages("Index\n#####\n\n.. report:doc-coverage::\n   :reportid: doc\n")

		self.assertEqual([PAGES], app.env.toctree_includes["index"])
		self.assertEqual([f"{PAGES}/Units", f"{PAGES}/Shapes"], app.env.toctree_includes[PAGES])
		toc = app.env.tocs[f"{PAGES}/Shapes"]
		self.assertEqual(1, len(list(toc.findall(nodes.reference))))
		self.assertNotIn("Summary", toc.astext())
		self.assertEqual(1, len(list(app.env.tocs[PAGES].findall(addnodes.toctree))))

	@testcase("Source of a page")
	def Source(self) -> None:
		"""
		Sphinx regards a module's file as its page's source, a package's '__init__.py' as the package's.

		Builds the project and checks the registered paths.
		"""
		app = self._buildPages("Index\n#####\n")

		self.assertEqual(PACKAGE.resolve() / "Shapes.py", app.env.doc2path(f"{PAGES}/Shapes"))
		self.assertEqual(PACKAGE.resolve() / "Units" / "__init__.py", app.env.doc2path(f"{PAGES}/Units"))

	@testcase("LaTeX")
	def LaTeX(self) -> None:
		"""
		A LaTeX build writes a listing as Sphinx writes highlighted code, each line's number colored by its state.

		Builds the table as LaTeX.
		"""
		self._buildPages("Index\n#####\n\n.. report:doc-coverage::\n   :reportid: doc\n", "latex")

		self.assertEqual([], self._warningLines())
		latex = next((self._path / "build" / "latex").glob("*.tex")).read_text(encoding="utf-8")
		self.assertIn("\\sphinxcode{myPackage/Shapes.py}\\hfill{}", latex)
		self.assertIn("\\textcolor{green!50!black}{\\texttt{+}}~documented", latex)
		self.assertIn("\\textcolor{red}{39 -} ", latex)
		self.assertIn("\\textcolor{gray}{    } ", latex)
		self.assertIn("\\PYG{k}{class}", latex)


@testsuite("Condensed listing")
class Listing(DocCoverageProject):
	"""A module's source condensed to headers, doc-strings, fields and variables, each line marked by its state."""

	@testcase("Signatures and doc-strings")
	def Signatures(self) -> None:
		"""
		A class or function keeps its decorators, its header - a signature spanning lines too - and its doc-string, all
		marked by its state.

		Builds the project and checks the listing of 'Shapes'.
		"""
		self._buildPages("Index\n#####\n")

		body = self._body(f"{PAGES}/Shapes")
		for number in range(32, 39):
			with self.subTest(line=number):
				self.assertIn(f'<span class="report-line report-line-documented"><span class="linenos">{number}</span>', body)
		self.assertIn('<span class="c1"># keeps the circle</span>', body)
		self.assertIn("Initialize a circle.", body)
		self.assertIn('<span class="report-line report-line-documented"><span class="linenos">48</span>', body)
		self.assertIn('<span class="report-line report-line-undocumented"><span class="linenos">29</span>', body)
		self.assertIn('<span class="report-line report-line-undocumented"><span class="linenos">39</span>', body)

	@testcase("Elided bodies")
	def ElidedBodies(self) -> None:
		"""
		A body is elided to one '...' line at its indentation, without a line number; imports are elided too.

		Builds the project and checks the listing of 'Shapes'.
		"""
		self._buildPages("Index\n#####\n")

		body = self._body(f"{PAGES}/Shapes")
		ellipsis = '<span class="o">.</span><span class="o">.</span><span class="o">.</span>'
		self.assertIn(f'<span class="report-line report-line-elided"><span class="linenos"></span>{ellipsis}', body)
		self.assertIn(f'<span class="report-line report-line-elided"><span class="linenos"></span>\t\t{ellipsis}', body)
		self.assertIn(f'<span class="report-line report-line-elided"><span class="linenos"></span>\t\t\t{ellipsis}', body)
		self.assertNotIn("Negative radius.", body)
		self.assertNotIn('<span class="linenos">25</span>', body)
		self.assertNotIn('<span class="kn">import</span>', body)

	@testcase("Fields and variables")
	def FieldsAndVariables(self) -> None:
		"""
		Fields and variables are kept as written - with their '#:' comments and doc-string literals -, and marked by the
		states of their items.

		Builds the project and checks the listings of 'Shapes' and of the package's '__init__.py'.
		"""
		self._buildPages("Index\n#####\n")

		body = self._body(f"{PAGES}/Shapes")
		for number in (5, 6, 8, 9, 15, 17):
			with self.subTest(line=number):
				self.assertIn(f'<span class="report-line report-line-documented"><span class="linenos">{number}</span>', body)
		self.assertIn("#: The number of shapes created.", body)
		self.assertIn("The unit of a shape's dimensions.", body)
		self.assertIn('<span class="report-line report-line-ignored"><span class="linenos">2</span>', self._body(PAGES))

	@testcase("One-line definitions")
	def OneLiners(self) -> None:
		"""
		A definition written in one line is kept as written.

		Builds the project and checks the listing of 'Shapes'.
		"""
		self._buildPages("Index\n#####\n")

		body = self._body(f"{PAGES}/Shapes")
		self.assertIn('<span class="report-line report-line-undocumented"><span class="linenos">46</span>', body)
		self.assertIn('<span class="report-line report-line-undocumented"><span class="linenos">54</span>', body)
		self.assertIn('<span class="k">return</span>', body)

	@testcase("Compound statement")
	def Compound(self) -> None:
		"""
		A statement holding functions is kept as written, its functions condensed and marked.

		Builds the project and checks the listing of 'Length'.
		"""
		self._buildPages("Index\n#####\n")

		body = self._body(f"{PAGES}/Units/Length")
		self.assertIn('<span class="report-line"><span class="linenos">4</span><span class="k">if</span>', body)
		self.assertIn('<span class="report-line report-line-documented"><span class="linenos">5</span>', body)
		self.assertIn('<span class="report-line"><span class="linenos">8</span><span class="k">else</span>', body)
		self.assertIn('<span class="report-line report-line-undocumented"><span class="linenos">9</span>', body)
		for number in range(12, 16):
			with self.subTest(line=number):
				self.assertIn(f'<span class="report-line report-line-documented"><span class="linenos">{number}</span>', body)

	@testcase("Variables and fields in 'if' and 'try'")
	def IfAndTry(self) -> None:
		"""
		A variable or field assigned in an 'if' or 'try' of a module or class is shown and marked; the clauses' headers
		are kept, other statements elided.

		Builds a package with a module assigning a variable in an 'if' and in a 'try', and a field in an 'if'.
		"""
		self._buildPackage({
			"__init__.py": b'"""A package."""\n',
			"Mod.py": dedent("""\
				\"\"\"A module.\"\"\"
				if True:
					T = int  #: A type.
				else:
					T = str

				try:
					import json
					HAS = True  #: Json available.
				except ImportError:
					HAS = False


				class C:
					\"\"\"A class.\"\"\"

					if True:
						g: int  #: A guarded field.
				""").encode("utf-8")
		})

		self.assertEqual([], self._warningLines())
		body = self._body("doccov/pkg/Mod")
		for number, state in ((2, ""), (3, "documented"), (4, ""), (5, ""), (7, ""), (9, "documented"), (10, ""),
				(11, ""), (17, ""), (18, "documented")):
			with self.subTest(line=number):
				classes = "report-line" if state == "" else f"report-line report-line-{state}"
				self.assertIn(f'<span class="{classes}"><span class="linenos">{number}</span>', body)
		self.assertNotIn('<span class="linenos">8</span>', body)
		self.assertIn('<span class="report-line report-line-elided"><span class="linenos"></span>\t<span class="o">', body)

	@testcase("Ignored items")
	def Ignored(self) -> None:
		"""
		A property's setter and an '@overload' stub are marked 'ignored'.

		Builds a package with a module holding a property with setter and an overloaded function.
		"""
		self._buildPackage({
			"__init__.py": b'"""A package."""\n',
			"Mod.py": dedent("""\
				\"\"\"A module.\"\"\"
				from typing import overload


				class C:
					\"\"\"A class.\"\"\"

					@property
					def P(self) -> int:
						\"\"\"A property.\"\"\"
						return 1

					@P.setter
					def P(self, value: int) -> None:
						pass


				@overload
				def f(x: int) -> int: ...
				def f(x):
					\"\"\"A function.\"\"\"
					return x
				""").encode("utf-8")
		})

		self.assertEqual([], self._warningLines())
		body = self._body("doccov/pkg/Mod")
		for number, state in ((8, "documented"), (13, "ignored"), (14, "ignored"), (18, "ignored"), (19, "ignored"),
				(20, "documented")):
			with self.subTest(line=number):
				self.assertIn(f'<span class="report-line report-line-{state}"><span class="linenos">{number}</span>', body)

	@testcase("Empty '__init__.py'")
	def EmptyInit(self) -> None:
		"""
		An empty '__init__.py' has nothing to document: its doc-string isn't counted, its listing is empty.

		Builds a package with an empty '__init__.py'.
		"""
		self._buildPackage({"__init__.py": b"", "Mod.py": b'"""A module."""\n'})

		self.assertEqual([], self._warningLines())
		body = self._body("doccov/pkg")
		self.assertIn("<p>not counted</p>", body)
		self.assertIn('<span class="report-coverage-path">pkg/__init__.py</span>', body)
		self.assertNotIn('<span class="report-line', body)

	@testcase("Declared encoding")
	def Encoding(self) -> None:
		"""
		A source file is read in the encoding it declares.

		Builds a package with a Latin-1 encoded module, which declares its encoding.
		"""
		self._buildPackage({
			"__init__.py": b'"""A package."""\n',
			"Mod.py": '# -*- coding: latin-1 -*-\n"""Maße und Größen."""\n'.encode("latin-1")
		})

		self.assertEqual([], self._warningLines())
		self.assertIn("Maße und Größen.", self._body("doccov/pkg/Mod"))


@testsuite("Condensed source")
class Condensing(DocCoverageProject):
	"""The condensing of a module's source, without Sphinx."""

	@staticmethod
	def _module(status: str = "Undocumented") -> Any:
		"""
		Create a module's item of pyEDAA.Reports' model, declared in its file 'm.py'.

		:param status: Optional, the name of the module's coverage state. Default: ``"Undocumented"``.
		:returns:      The module's item.
		"""
		from pyEDAA.Reports.DocumentationCoverage import CoverageState, DocumentationReport, Item, ItemKind

		report = DocumentationReport(Path("m"))
		file = report.GetOrAddFile(Path("m.py"))

		return Item("m", ItemKind.Module, CoverageState[status], file=file, parent=report)

	@staticmethod
	def _item(module: Any, name: str, kind: str, status: str, startLine: int, parent: Any = None) -> Any:
		"""
		Create an item declared in a module's file.

		:param module:    The module's item.
		:param name:      Name of the item.
		:param kind:      Name of the item's kind.
		:param status:    Name of the item's coverage state.
		:param startLine: The item's first line.
		:param parent:    Optional, the item containing the item. Default: the module.
		:returns:         The item.
		"""
		from pyEDAA.Reports.DocumentationCoverage import CoverageState, Item, ItemKind

		return Item(
			name, ItemKind[kind], CoverageState[status], file=module.File, startLine=startLine,
			parent=module if parent is None else parent
		)

	@testcase("Lines")
	def Lines(self) -> None:
		"""
		The condensed lines are numbered and marked; an elided body has no number, but its indentation.

		Condenses a module with a documented function.
		"""
		module = self._module()
		self._item(module, "f", "Function", "Covered", 3)
		source = 'import sys\n\ndef f(a: int) -> int:\n\t"""Doc."""\n\tb = a\n\treturn b\n'

		self.assertEqual(
			[(None, "", ""), (2, "", ""), (3, "documented", ""), (4, "documented", ""), (None, "", "\t")],
			CondensedSource.Parse(source, "m.py", module).Lines
		)

	@testcase("Module doc-string")
	def ModuleDocString(self) -> None:
		"""
		The module's doc-string is marked by the module's state.

		Condenses a documented module.
		"""
		self.assertEqual(
			[(1, "documented", "")], CondensedSource.Parse('"""Doc."""\n', "m.py", self._module("Covered")).Lines
		)

	@testcase("States of fields and variables from the model")
	def ModelStates(self) -> None:
		"""
		A variable or field is marked by the state of the item starting at its line; a repeated assignment and a name
		without item are not.

		Condenses a module whose model holds a variable and a class with a field.
		"""
		module = self._module()
		self._item(module, "X", "Variable", "Covered", 1)
		self._item(module, "y", "Field", "Undocumented", 6, self._item(module, "A", "Class", "Undocumented", 5))
		source = "X = 1\nZ = 2\nX = 3\n\nclass A:\n\ty: int\n"

		lines = CondensedSource.Parse(source, "m.py", module).Lines
		self.assertIn((1, "documented", ""), lines)
		self.assertIn((2, "", ""), lines)
		self.assertIn((3, "", ""), lines)
		self.assertIn((5, "undocumented", ""), lines)
		self.assertIn((6, "undocumented", ""), lines)

	@testcase("Documentation states")
	def DocumentationStates(self) -> None:
		"""
		A coverage state maps to the listing's state as the model counts it: empty, excluded, ignored, covered.

		Maps the coverage states an item of the Python reader has.
		"""
		from pyEDAA.Reports.DocumentationCoverage import CoverageState

		for coverageState, state in (
			(CoverageState.Empty,                                                       ""),
			(CoverageState.Excluded,                                                    "excluded"),
			(CoverageState.Documented | CoverageState.Covered | CoverageState.Excluded, "excluded"),
			(CoverageState.Undocumented | CoverageState.Ignored,                        "ignored"),
			(CoverageState.Documented | CoverageState.Covered,                          "documented"),
			(CoverageState.Excused | CoverageState.Covered,                             "documented"),
			(CoverageState.Undocumented,                                                "undocumented"),
		):
			with self.subTest(coverageState=coverageState):
				self.assertEqual(state, documentationState(coverageState))

	@testcase("Excluded item")
	def Excluded(self) -> None:
		"""
		An excluded item's lines are marked 'excluded'.

		Condenses a module with an excluded function.
		"""
		module = self._module()
		self._item(module, "f", "Function", "Excluded", 1)

		self.assertEqual(
			[(1, "excluded", ""), (None, "", "\t")], CondensedSource.Parse("def f():\n\tpass\n", "m.py", module).Lines
		)

	@testcase("Constructor")
	def Constructor(self) -> None:
		"""
		The constructor takes the condensed lines; it rejects None, a non-iterable and a line, which isn't a tuple.

		Constructs condensed sources from lines and from wrong values.
		"""
		lines = [(1, "documented", ""), (None, "", "\t")]
		self.assertEqual(lines, CondensedSource(lines).Lines)

		with self.assertRaises(ValueError) as context:
			CondensedSource(None)
		self.assertEqual("Parameter 'lines' is None.", str(context.exception))

		with self.assertRaises(TypeError) as context:
			CondensedSource(1)
		self.assertEqual("Parameter 'lines' is not iterable.", str(context.exception))

		with self.assertRaises(TypeError) as context:
			CondensedSource([[1, "", ""]])
		self.assertEqual("Parameter 'lines' contains an element, which is not of type 'tuple'.", str(context.exception))

	@testcase("Analysis not matching the source")
	def Mismatch(self) -> None:
		"""
		An analysis naming other classes and functions than the source has is warned about; nothing is marked.

		Condenses a module with a function the analysis doesn't name.
		"""
		module = self._module()
		self._item(module, "g", "Function", "Covered", 1)

		with self.assertLogs("sphinx.pyTooling.Sphinx.CondensedSource", "WARNING") as logs:
			lines = CondensedSource.Parse("def f():\n\tpass\n", "m.py", module).Lines

		self.assertEqual([(1, "", ""), (None, "", "\t")], lines)
		self.assertIn("The documentation coverage analysis of 'm.py' doesn't match the source", logs.output[0])


@testsuite("Role ':doccov:'")
class Role(DocCoverageProject):
	"""The role referring to a package or module, by dotted name or a suffix of it."""

	@testcase("Resolution")
	def Resolution(self) -> None:
		"""
		A reference names a dotted name or a suffix of it, with or without report ID.

		Builds the document and checks every link.
		"""
		self._buildPages(dedent("""\
			Index
			#####

			* :doccov:`Shapes`
			* :doccov:`doc:myPackage.Units`
			* :report:doccov:`Units.Length`
			* :doccov:`the package <myPackage>`
			"""))

		self.assertEqual([], self._warningLines())
		body = self._body("index")
		for href, text in (
			(f"{PAGES}/Shapes.html", "Shapes"),
			(f"{PAGES}/Units.html", "Units"),
			(f"{PAGES}/Units/Length.html", "Length"),
			(f"{PAGES}.html", "the package"),
		):
			with self.subTest(text=text):
				self.assertIn(f'href="{href}"><span class="xref report report-doccov">{text}</span>', body)

	@testcase("Unknown")
	def Unknown(self) -> None:
		"""
		An unknown name is warned about.

		Builds a document referring to a module the package doesn't have.
		"""
		self._buildPages("Index\n#####\n\n* :doccov:`Missing`\n")

		warnings = self._warningLines()
		self.assertEqual(1, len(warnings))
		self.assertIn("module 'Missing' not found in the documentation coverage reports", warnings[0])

	@testcase("Domain objects")
	def DomainObjects(self) -> None:
		"""
		Every package and module with a page is an object of type 'module', named by report ID and dotted name.

		Builds the project and checks the domain's objects.
		"""
		app = self._buildPages("Index\n#####\n")
		domain: ReportDomain = app.env.domains[ReportDomain.name]

		objects = {name: (objectType, docName) for name, _, objectType, docName, _, _ in domain.get_objects()}
		self.assertEqual(("module", f"{PAGES}/Units/Length"), objects["doc:myPackage.Units.Length"])
		self.assertEqual(4, sum(1 for name in objects if name.startswith("doc:")))


@testsuite("Configuration key 'pages'")
class Configuration(DocCoverageProject):
	"""The key 'pages' of a package's configuration."""

	@testcase("Normalized")
	def Normalized(self) -> None:
		"""
		Surrounding slashes are removed from the document name.

		Checks the loaded configuration after a build with '/doccov/'.
		"""
		self._buildPages("Index\n#####\n", pages="/doccov/")

		self.assertEqual([], self._warningLines())
		self.assertEqual("doccov", DocCoverageBase._packageConfigurations["doc"]["pages"])
		self.assertEqual(PAGES, DocCoverageReportPages.GetPages("doc").DocNames[0])

	@testcase("Not a relative document name")
	def Invalid(self) -> None:
		"""
		A document name with '..' is logged as an error.

		Builds a project with 'doccov/../src'.
		"""
		self._buildPages("Index\n#####\n", pages="doccov/../src")

		self.assertEqual(
			[
				"ERROR: Caught ReportExtensionError when checking configuration variables.",
				"  conf.py: pyTooling_DocCoverage_Packages:[doc].pages: 'doccov/../src' is not a relative document name."
			],
			self._warningLines()
		)

	@testcase("Invalid source")
	def InvalidSource(self) -> None:
		"""
		A module or '__init__.py', which isn't valid Python, is warned about once and excluded; its row and page say so.

		Its row has the coverage level 'error' and says, that it can't be read; its page says, that its source can't be
		read or parsed.

		Builds the table of a package with a syntax error in a module and in a sub-package's '__init__.py'.
		"""
		package = self._path / "broken"
		(package / "Sub").mkdir(parents=True)
		(package / "__init__.py").write_text('"""A broken package."""\n', encoding="utf-8")
		(package / "Module.py").write_text("x = = 1\n", encoding="utf-8")
		(package / "Sub" / "__init__.py").write_text("def f(:\n", encoding="utf-8")

		self._build(
			"Index\n#####\n\n.. report:doc-coverage::\n   :reportid: doc\n",
			pyTooling_DocCoverage_Packages={
				"doc": {"name": "broken", "directory": str(package), "pages": "doccov", "fail_below": 80, "levels": "default"}
			}
		)

		warnings = self._warningLines()
		self.assertEqual(
			[
				"WARNING: Caught SourceFileWarning when analyzing package 'broken'.",
				"  Source file 'Module.py' can't be analyzed.",
				"  SyntaxError: invalid syntax (Module.py, line 1)",
				"WARNING: Caught SourceFileWarning when analyzing package 'broken'.",
				"  Source file 'Sub/__init__.py' can't be analyzed."
			],
			warnings[:5]
		)
		self.assertEqual(6, len(warnings))
		self.assertTrue(warnings[5].startswith("  SyntaxError: "))

		index = self._body("index")
		for kind, name in (("module", "Module"), ("package", "Sub")):
			with self.subTest(row=name):
				self.assertRegex(
					index,
					f'<tr class="report-{kind} report-cov-error row-(even|odd)">.*?>{name}</span>.*?\n<td>0</td>\n<td>0</td>\n'
					f"<td>0</td>\n<td>can't be read</td>"
				)

		body = self._body("doccov/broken/Module")
		self.assertIn("<p>can't be read</p>", body)
		self.assertIn(
			'<tr class="report-cov-error row-even"><td><p>Module.py</p></td>\n<td><p>0</p></td>\n<td><p>0</p></td>\n'
			"<td><p>0</p></td>\n<td><p>can't be read</p></td>", body
		)
		self.assertIn("<p>The source file 'broken/Module.py' can't be read or parsed.</p>", body)
		self.assertIn('<tr class="report-cov-error row-even"><td><p><a class="reference internal" href="broken/Sub.html"',
			self._body("doccov/broken")
		)

	@testcase("Without pages")
	def WithoutPages(self) -> None:
		"""
		A package without the key 'pages' gets no pages, and its table no links.

		Builds a project with the table of a package declared without 'pages'.
		"""
		self._build(
			"Index\n#####\n\n.. report:doc-coverage::\n   :reportid: doc\n",
			pyTooling_DocCoverage_Packages={
				"doc": {"name": "myPackage", "directory": str(PACKAGE), "fail_below": 80, "levels": "default"}
			}
		)

		self.assertEqual([], self._warningLines())
		self.assertFalse(DocCoverageReportPages.HasPages("doc"))
		self.assertNotIn("report-doccov\">", self._body("index"))
		self.assertFalse((self._path / "build" / "html" / "doccov").exists())


@testsuite("Configuration key 'levels'")
class Levels(DocCoverageProject):
	"""The key 'levels' of a package's configuration."""

	@testcase("Levels as a dictionary")
	def Dictionary(self) -> None:
		"""
		A package declaring its own levels as a dictionary renders its table with these levels.

		Builds a project with the table of a package declaring its levels.
		"""
		levels = {
			50:      {"class": "mine-low",   "desc": "low"},
			100:     {"class": "mine-high",  "desc": "high"},
			"error": {"class": "mine-error", "desc": "error"}
		}
		self._build(
			"Index\n#####\n\n.. report:doc-coverage::\n   :reportid: doc\n",
			pyTooling_DocCoverage_Packages={
				"doc": {"name": "myPackage", "directory": str(PACKAGE), "fail_below": 80, "levels": levels}
			}
		)

		self.assertEqual([], self._warningLines())
		self.assertEqual(levels, DocCoverageBase._packageConfigurations["doc"]["levels"])
		body = self._body("index")
		self.assertIn('<tr class="report-package mine-high row-even"><td>\U0001f4e6myPackage</td>', body)
		self.assertIn('<tr class="report-package mine-low row-odd"><td>\u2001\U0001f4e6Units</td>', body)
