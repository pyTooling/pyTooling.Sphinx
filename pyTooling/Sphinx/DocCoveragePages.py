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
A page per package and per module of a documentation coverage analysis, generated without a source file.

A package declared in ``pyTooling_DocCoverage_Packages`` with the key ``pages`` gets a document per package and per
module, named below that key's document name by its dotted name, e.g. ``<pages>/myPackage/Units/Length``.

* A package's page shows its counters, tables of its sub-packages and modules, each linked to its page, and the
  condensed listing of its ``__init__.py``.
* A module's page shows its counters and its condensed listing (see
  :class:`~pyTooling.Sphinx.CondensedSource.CondensedSource`): the source condensed to what is documented, syntax
  highlighted with the Pygments lexer for Python, each line marked by its documentation state.

A class' or function's state is docstr_coverage's - the analysis the counters are computed from: ``documented``,
``undocumented``, or ``ignored``. A field or variable is marked only if pyEDAA.Reports' model holds a state for it, as
docstr_coverage doesn't count them.

The pages are built by the machinery of :class:`~pyTooling.Sphinx.Pages.ReportPages`, so they are in the navigation
below the directive ``report:doc-coverage``. Every package and module with a page is an object of domain ``report``,
referred to by the role ``:doccov:`` by its dotted name - e.g. ``:doccov:`myPackage.Units.Length``` - or a suffix of
it.

.. seealso::

   :ref:`DIR/DocCoverage/Pages`
      |rarr| The pages and the role, with examples.
   :mod:`pyTooling.Sphinx.Pages`
      |rarr| The pages of a report: document names, registration, generation and navigation.
   :mod:`pyTooling.Sphinx.CondensedSource`
      |rarr| The condensed listing of a module's source.
"""
from __future__                                    import annotations

from pathlib                                       import Path
from typing                                        import TYPE_CHECKING, ClassVar, Iterable, Optional as Nullable, Union

from docutils                                      import nodes
from sphinx.application                            import Sphinx
from sphinx.util.logging                           import getLogger

from pyTooling.Decorators                          import export

from pyTooling.Sphinx                              import ReportExtensionError
from pyTooling.Sphinx.CodeCoveragePages            import tokenizeSource
from pyTooling.Sphinx.CondensedSource              import CondensedSource
from pyTooling.Sphinx.DocCoverage                  import DocCoverageBase
from pyTooling.Sphinx.Node                         import DOCUMENTATION_STATES, DocCoverageListing
from pyTooling.Sphinx.Pages                        import ReportPages

if TYPE_CHECKING:  # pragma: no cover
	# pyEDAA.Reports and docstr_coverage are optional dependencies (extra 'reports'), imported where a package is
	# analyzed.
	from docstr_coverage                             import ResultCollection
	from docstr_coverage.result_collection           import File
	from pyEDAA.Reports.DocumentationCoverage.Python import AggregatedCoverage, PackageCoverage


@export
class DocCoverageReportPages(ReportPages):
	"""
	The pages of one package's documentation coverage: a page per package and per module.
	"""

	_reportPages: ClassVar[dict[str, ReportPages]] = {}  #: The pages of every analyzed package with pages, by report ID.
	_separator:   ClassVar[str] = "."                    #: Separator of the names in a dotted name.

	_directory: Path                                   #: The package's source directory.
	_results:   dict[Path, File]                       #: docstr_coverage's results per module, by its resolved path.
	_levels:    dict[Union[int, str], dict[str, str]]  #: The package's coverage levels, coloring the tables.

	def __init__(
		self,
		reportID: str,
		prefix: str,
		directory: Path,
		coverage: PackageCoverage,
		results: ResultCollection,
		levels: dict[Union[int, str], dict[str, str]]
	) -> None:
		"""
		Compute the document names and entries of a package's packages and modules.

		:param reportID:  Identifier of the package.
		:param prefix:    Document name the pages are generated below.
		:param directory: The package's source directory.
		:param coverage:  The package's coverage, the root of the pages.
		:param results:   docstr_coverage's results of the package.
		:param levels:    The package's coverage levels.
		"""
		super().__init__(reportID, prefix, directory, [("doccov", coverage)])

		self._directory = directory.resolve()
		self._results =   {Path(path).resolve(): file for path, file in results.files()}
		self._levels =    levels

	@classmethod
	def CreatePages(cls, sphinxApplication: Sphinx) -> None:
		"""
		Call-back for Sphinx' ``builder-inited`` event, after the packages are analyzed: compute and register the pages.

		Only a package with the key ``pages`` gets pages. A package that couldn't be analyzed gets none; this is logged
		as an error.

		:param sphinxApplication: Sphinx application instance.
		"""
		cls._reportPages = {}
		for reportID, packageConfiguration in DocCoverageBase._packageConfigurations.items():
			if (prefix := packageConfiguration["pages"]) is None:
				continue

			try:
				coverage = DocCoverageBase.GetReport(reportID)
			except ReportExtensionError as ex:
				cause = ex if ex.__cause__ is None else ex.__cause__
				getLogger(__name__).error(
					f"Caught {ex.__class__.__name__} when generating the pages of documentation coverage '{reportID}'.\n"
					f"  {cause.__class__.__name__}: {cause}"
				)
				continue

			pages = cls(
				reportID, prefix, packageConfiguration["directory"], coverage, DocCoverageBase._results[reportID],
				packageConfiguration["levels"]
			)
			cls._reportPages[reportID] = pages
			pages.Register(sphinxApplication.env)

	def _Name(self, entity: AggregatedCoverage) -> str:
		"""
		Return a package's or module's name; the root package's may be dotted.

		The root package has the configured name, e.g. ``pyTooling.Sphinx``, which is one element of a path: a reference
		names it in full.

		:param entity: The package or module.
		:returns:      The name.
		"""
		return entity.Name

	def _Title(self, entity: AggregatedCoverage) -> Nullable[str]:
		"""
		Return no title, as a package or module has none.

		:param entity: The package or module.
		:returns:      ``None``
		"""
		return None

	def _Children(self, roleName: str, entity: AggregatedCoverage) -> Iterable[tuple[str, AggregatedCoverage]]:
		"""
		Return a package's sub-packages, then its modules, each sorted by name; a module has none.

		:param roleName: The role referring to the object: ``doccov``.
		:param entity:   The package or module.
		:returns:        The children as ``(role name, object)`` pairs.
		"""
		if not hasattr(entity, "Packages"):
			return []

		children: list[tuple[str, AggregatedCoverage]] = []
		children.extend(("doccov", entity.Packages[name]) for name in sorted(entity.Packages))
		children.extend(("doccov", entity.Modules[name]) for name in sorted(entity.Modules))

		return children

	def _Source(self, entity: AggregatedCoverage) -> Path:
		"""
		Return the source of a package's or module's page: the module's file, the package's ``__init__.py`` - or its
		directory, if it has none.

		:param entity: The package or module.
		:returns:      The page's source file.
		"""
		names: list[str] = []
		unit = entity
		while unit.Parent is not None:
			names.insert(0, unit.Name)
			unit = unit.Parent

		if not hasattr(entity, "Packages"):
			return self._directory.joinpath(*names[:-1], f"{entity.Name}.py")

		directory = self._directory.joinpath(*names)
		return directory / "__init__.py" if (directory / "__init__.py").is_file() else directory

	def _Page(self, docName: str, roleName: str, entity: AggregatedCoverage) -> nodes.section:
		"""
		Build a package's or module's page: its summary, a package's tables of sub-packages and modules, and the
		condensed listing.

		:param docName:  Name of the page's document.
		:param roleName: The role referring to the object: ``doccov``.
		:param entity:   The package or module.
		:returns:        The page's top section.
		"""
		sourceFile = self._Source(entity)
		expected: list[tuple[str, str]] = []
		if (fileResult := self._results.get(sourceFile, None)) is not None:
			expected = [
				(
					item.node_identifier,
					"ignored" if item.ignore_reason else "documented" if item.has_docstring else "undocumented"
				)
				for item in fileResult.expected_docstrings()
			]

		page = nodes.section("", nodes.title(entity.Name, entity.Name), ids=["report-doccov-page"])
		page += (summarySection := self._SummarySection(docName, entity, expected))

		if hasattr(entity, "Packages"):
			children = self._ChildrenSections(page, docName, entity)
			if len(children) > 0:
				# body elements precede a section's subsections, so the hidden table of contents goes before 'Summary'
				page.insert(page.index(summarySection), self._TableOfContents(docName, children))

		if sourceFile.is_file():
			page += self._SourceSection(entity, sourceFile, expected)

		return page

	def _SummarySection(
		self,
		docName: str,
		entity: AggregatedCoverage,
		expected: list[tuple[str, str]]
	) -> nodes.section:
		"""
		Create a page's section *Summary*: the parent package, the module's doc-string state, and the counters - a
		package's of its ``__init__.py`` and overall -, colored by coverage level.

		:param docName:  Name of the page's document.
		:param entity:   The package or module.
		:param expected: docstr_coverage's expected doc-strings of the source file.
		:returns:        The section.
		"""
		section = nodes.section("", nodes.title("Summary", "Summary"), ids=["summary"])
		section += (fieldList := nodes.field_list(classes=["report-doccov-fields"]))
		if entity.Parent is not None:
			self._Field(fieldList, "Package", self._Reference("doccov", entity.Parent, docName))

		for identifier, state in expected:
			if identifier == "module docstring":
				self._Field(fieldList, "Doc-string", nodes.Text(DOCUMENTATION_STATES[state]))

		table, tableBody = self._Table(
			[("File", 6), ("Expected", 2), ("Covered", 2), ("Uncovered", 2), ("Coverage", 2)],
			["report-doccov-table", "report-doccov-summary"]
		)
		section += table

		isPackage = hasattr(entity, "Packages")
		rows = [(
			"__init__.py" if isPackage else f"{entity.Name}.py", "", entity.Expected, entity.Covered, entity.Uncovered,
			entity.Coverage
		)]
		if isPackage:
			rows.append((
				f"Overall ({entity.FileCount} files)", "report-summary", entity.AggregatedExpected, entity.AggregatedCovered,
				entity.AggregatedUncovered, entity.AggregatedCoverage
			))

		for name, cssClass, expectedCount, covered, uncovered, coverage in rows:
			level = DocCoverageBase.LevelOf(self._levels, coverage, "class")
			tableBody += (row := nodes.row("", classes=[cssClass, level] if cssClass != "" else [level]))
			row += nodes.entry("", nodes.paragraph("", name))
			row += nodes.entry("", nodes.paragraph("", f"{expectedCount}"))
			row += nodes.entry("", nodes.paragraph("", f"{covered}"))
			row += nodes.entry("", nodes.paragraph("", f"{uncovered}"))
			row += nodes.entry("", nodes.paragraph("", f"{coverage:.1%}"))

		return section

	def _ChildrenSections(self, page: nodes.section, docName: str, package: PackageCoverage) -> list[str]:
		"""
		Add a package's sections of its sub-packages and modules: a table each, every row linked to its page and colored
		by coverage level. A sub-package's row counts it with all its modules.

		:param page:    The package's page.
		:param docName: Name of the page's document.
		:param package: The package.
		:returns:       The document names of the listed pages.
		"""
		children: list[str] = []
		for title, column, identifier, units in (
			("Packages", "Package", "packages", [package.Packages[name] for name in sorted(package.Packages)]),
			("Modules",  "Module",  "modules",  [package.Modules[name] for name in sorted(package.Modules)]),
		):
			if len(units) == 0:
				continue

			page += (section := nodes.section("", nodes.title(title, title), ids=[identifier]))
			table, tableBody = self._Table(
				[(column, 6), ("Expected", 2), ("Covered", 2), ("Uncovered", 2), ("Coverage", 2)],
				["report-doccov-table", "report-doccov-children"]
			)
			section += table
			for unit in units:
				level = DocCoverageBase.LevelOf(self._levels, unit.AggregatedCoverage, "class")
				tableBody += (row := nodes.row("", classes=[level]))
				row += nodes.entry("", nodes.paragraph("", "", self._Reference("doccov", unit, docName)))
				row += nodes.entry("", nodes.paragraph("", f"{unit.AggregatedExpected}"))
				row += nodes.entry("", nodes.paragraph("", f"{unit.AggregatedCovered}"))
				row += nodes.entry("", nodes.paragraph("", f"{unit.AggregatedUncovered}"))
				row += nodes.entry("", nodes.paragraph("", f"{unit.AggregatedCoverage:.1%}"))
				if (entry := self.Entry(unit)) is not None:
					children.append(entry.docName)

		return children

	def _SourceSection(
		self,
		entity: AggregatedCoverage,
		sourceFile: Path,
		expected: list[tuple[str, str]]
	) -> nodes.section:
		"""
		Create a page's section *Source*: the condensed listing of the module, or of the package's ``__init__.py``.

		A source file that can't be read is logged as a warning, and the section says so.

		:param entity:     The package or module.
		:param sourceFile: The source file.
		:param expected:   docstr_coverage's expected doc-strings of the source file.
		:returns:          The section.
		"""
		section = nodes.section("", nodes.title("Source", "Source"), ids=["source"])
		path = "/".join(self.Entry(entity).path) + ("/__init__.py" if hasattr(entity, "Packages") else ".py")
		try:
			source = sourceFile.read_text(encoding="utf-8")
		except OSError as ex:
			getLogger(__name__).warning(f"Source file '{sourceFile}' of the documentation coverage can't be read: {ex}")
			section += nodes.paragraph(text=f"The source file '{path}' can't be read.")
			return section

		sourceLines = source.split("\n")
		tokens = tokenizeSource(source, sourceFile.name)
		ellipsis = tokenizeSource("...\n", sourceFile.name)[0]

		lines: list[tuple[Nullable[int], str, list[tuple[str, str]]]] = []
		text: list[str] = []
		for number, state, indentation in CondensedSource.Parse(source, path, expected, entity).Lines:
			if number is None:
				lines.append((None, "", [("", indentation), *ellipsis]))
				text.append(f"{indentation}...")
			else:
				lines.append((number, state, tokens[number - 1]))
				text.append(sourceLines[number - 1])

		plainText = "\n".join(text)
		section += DocCoverageListing(plainText, plainText, lines=lines, path=path)

		return section
