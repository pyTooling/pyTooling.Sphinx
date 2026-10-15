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
* A module's page shows its counters and its condensed listing (see :class:`CondensedSource`): the source condensed to
  what is documented, syntax highlighted with the Pygments lexer for Python, each line marked by its documentation
  state.

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
"""
from __future__                                    import annotations

from ast                                           import AST, AnnAssign, Assign, AsyncFunctionDef, ClassDef, Constant
from ast                                           import Expr, FunctionDef, Name, TypeAlias, iter_child_nodes
from ast                                           import parse, stmt
from pathlib                                       import Path
from typing                                        import TYPE_CHECKING, Any, ClassVar, Generator, Iterable
from typing                                        import Optional as Nullable, Union

from docutils                                      import nodes
from sphinx.application                            import Sphinx
from sphinx.util.logging                           import getLogger

from pyTooling.Decorators                          import export, readonly
from pyTooling.MetaClasses                         import ExtendedType

from pyTooling.Sphinx                              import ReportExtensionError
from pyTooling.Sphinx.CodeCoveragePages            import tokenizeSource
from pyTooling.Sphinx.DocCoverage                  import DocCoverageBase
from pyTooling.Sphinx.Node                         import DOCUMENTATION_STATES, DocCoverageListing
from pyTooling.Sphinx.Pages                        import ReportPages

if TYPE_CHECKING:  # pragma: no cover
	# pyEDAA.Reports and docstr_coverage are optional dependencies (extra 'reports'), imported where a package is
	# analyzed.
	from docstr_coverage                             import ResultCollection
	from docstr_coverage.result_collection           import File
	from pyEDAA.Reports.DocumentationCoverage        import CoverageState
	from pyEDAA.Reports.DocumentationCoverage.Python import AggregatedCoverage, PackageCoverage


__all__ = ["DEFINITIONS", "ASSIGNMENTS", "Definition"]

#: The statements docstr_coverage expects a doc-string of: a class and a function or method.
DEFINITIONS = (ClassDef, FunctionDef, AsyncFunctionDef)

#: The statements declaring a variable or a class' field.
ASSIGNMENTS = (Assign, AnnAssign, TypeAlias)

type Definition = Union[ClassDef, FunctionDef, AsyncFunctionDef]
"""A statement docstr_coverage expects a doc-string of."""


@export
def documentationState(coverageState: CoverageState) -> str:
	"""
	Return the state a listing marks a line with, for a coverage state of pyEDAA.Reports' documentation coverage model.

	The state is chosen as the model counts it: excluded before ignored, then documented - covered - or undocumented.
	``Unknown`` isn't counted, so it gets no state.

	:param coverageState: The model's coverage state.
	:returns:             The listing's state: ``documented``, ``undocumented``, ``ignored``, ``excluded`` or ``""``.
	"""
	from pyEDAA.Reports.DocumentationCoverage import CoverageState

	if coverageState == CoverageState.Unknown:
		return ""
	elif CoverageState.Excluded in coverageState:
		return "excluded"
	elif CoverageState.Ignored in coverageState:
		return "ignored"
	elif CoverageState.Covered in coverageState:
		return "documented"

	return "undocumented"


@export
class CondensedSource(metaclass=ExtendedType, slots=True):
	"""
	A Python module's source, condensed to what its documentation coverage is about.

	A line is taken as written, at its line number, or replaced by a ``...`` line without a number:

	* The module's doc-string is taken; its imports and other statements are elided.
	* A class or function is taken with its decorators, its header up to the ``:`` - a signature spanning lines too -
	  and its doc-string. Its body follows: a class' members, a function's nested functions and classes; anything else
	  is elided to one ``...`` at the body's indentation. A definition written in one line is taken as written.
	* A variable of the module and a field of a class is taken as written: with a ``#:`` comment on its line or in the
	  lines above it, and a doc-string literal following it.
	* A statement holding a class or function - e.g. an ``if`` or a ``try`` - is taken as written, its classes and
	  functions condensed.
	* Comments between statements are left out; consecutive blank lines become one.

	A class' or function's lines are marked by its state in the analysis, which docstr_coverage expected a doc-string
	for. A variable's or field's lines are marked only if the model holds a state for it; else they - like every other
	line - have no state.
	"""

	_source: list[str]                           #: The source's lines, without line ends.
	_unit:   AggregatedCoverage                  #: The module's coverage, which may hold states of variables and fields.
	_states: dict[int, str]                      #: Documentation state of a class or function, by its keyword's line.
	_lines:  list[tuple[Nullable[int], str, str]]  #: The condensed lines; see :attr:`Lines`.
	_last:   int                                 #: Number of the last source line taken or elided.

	def __init__(self, source: str, path: str, expected: list[tuple[str, str]], unit: AggregatedCoverage) -> None:
		"""
		Condense a module's source.

		An analysis not matching the source - other classes and functions than docstr_coverage found - is logged as a
		warning, and the classes and functions aren't marked.

		:param source:   The module's source.
		:param path:     The module's path, as the warning names it.
		:param expected: docstr_coverage's expected doc-strings of the module, in the order it found them, as
		                 ``(identifier, state)`` pairs.
		:param unit:     The module's or package's coverage.
		"""
		tree = parse(source)
		self._source = source.split("\n")
		self._unit =   unit
		self._states = {}
		self._lines =  []
		self._last =   0

		moduleState = ""
		if len(expected) > 0 and expected[0][0] == "module docstring":
			moduleState = expected[0][1]
			expected = expected[1:]

		definitions = list(self._Definitions(tree))
		if len(definitions) == len(expected) and all(
			definition.name == identifier.rpartition(".")[2]
			for definition, (identifier, _) in zip(definitions, expected)
		):
			self._states = {definition.lineno: state for definition, (_, state) in zip(definitions, expected)}
		else:
			getLogger(__name__).warning(
				f"The documentation coverage analysis of '{path}' doesn't match the source, so its classes and functions "
				f"aren't marked."
			)

		body = tree.body
		if len(body) > 0 and self._IsDocString(body[0]):
			self._Emit(body[0].lineno, body[0].end_lineno, moduleState)
			body = body[1:]

		self._Block(body, True, ())

	@readonly
	def Lines(self) -> list[tuple[Nullable[int], str, str]]:
		"""
		Read-only property to access the condensed lines (:attr:`_lines`).

		:returns: A tuple per line: the line number and its state, and ``""``; or for an elided body, ``None``, ``""``
		          and the body's indentation.
		"""
		return self._lines

	def _Emit(self, first: int, last: int, state: str) -> None:
		"""
		Take source lines as written, except those already taken.

		:param first: Number of the first line.
		:param last:  Number of the last line.
		:param state: The lines' documentation state.
		"""
		for number in range(max(first, self._last + 1), last + 1):
			self._lines.append((number, state, ""))

		self._last = max(self._last, last)

	def _Gap(self, last: int) -> None:
		"""
		Skip the lines between the last line taken and a line: a blank line is taken, unless the line before is blank or
		nothing was taken yet; a comment is left out.

		:param last: Number of the last line to skip.
		"""
		for number in range(self._last + 1, last + 1):
			if self._source[number - 1].strip() != "" or len(self._lines) == 0:
				continue

			previousNumber = self._lines[-1][0]
			if previousNumber is None or self._source[previousNumber - 1].strip() != "":
				self._lines.append((number, "", ""))

		self._last = max(self._last, last)

	def _Block(self, statements: list[stmt], variables: bool, scope: Nullable[tuple[str, ...]]) -> None:
		"""
		Take a block's statements: classes and functions condensed, variables or fields as written, other statements
		elided - consecutive ones to a single ``...``.

		:param statements: The block's statements, without a doc-string.
		:param variables:  Whether assignments are variables or fields - in a module or class - and taken.
		:param scope:      The class names leading to the block - ``()`` for the module -, by which the model is asked
		                   for a variable's or field's state; ``None`` if it can't be asked, e.g. in a function.
		"""
		elided = False
		attributeState: Nullable[str] = None
		for statement in statements:
			# a statement behind a ';' on a line already taken
			if statement.end_lineno <= self._last:
				continue

			docStringState = attributeState
			attributeState = None
			if isinstance(statement, DEFINITIONS):
				self._Definition(statement, scope)
			elif variables and isinstance(statement, ASSIGNMENTS):
				attributeState = self._VariableState(statement, scope)
				first = statement.lineno
				while first - 1 > self._last and self._source[first - 2].lstrip().startswith("#:"):
					first -= 1

				self._Gap(first - 1)
				self._Emit(first, statement.end_lineno, attributeState)
			elif docStringState is not None and self._IsDocString(statement):
				self._Gap(statement.lineno - 1)
				self._Emit(statement.lineno, statement.end_lineno, docStringState)
			elif any(True for _ in self._OutermostDefinitions(statement)):
				self._Compound(statement, scope)
			else:
				if not elided:
					self._Gap(statement.lineno - 1)
					line = self._source[statement.lineno - 1]
					self._lines.append((None, "", line[:len(line) - len(line.lstrip())]))

				self._last = statement.end_lineno
				elided = True
				continue

			elided = False

	def _Definition(self, definition: Definition, scope: Nullable[tuple[str, ...]]) -> None:
		"""
		Take a class or function: its decorators, header and doc-string, then its body's statements.

		:param definition: The class or function.
		:param scope:      The class names leading to the definition, or ``None`` (see :meth:`_Block`).
		"""
		state = self._states.get(definition.lineno, "")
		first = self._FirstLine(definition)
		self._Gap(first - 1)

		body = definition.body
		if self._source[body[0].lineno - 1].encode("utf-8")[:body[0].col_offset].strip() != b"":
			# the body starts in the header's line: 'def f(): pass'
			self._Emit(first, definition.end_lineno, state)
			return

		# the header ends before the body's first statement, without the blank lines and comments in between
		headerEnd = self._FirstLine(body[0]) - 1
		while headerEnd > definition.lineno and (
			(line := self._source[headerEnd - 1].strip()) == "" or line.startswith("#")
		):
			headerEnd -= 1

		self._Emit(first, headerEnd, state)
		if self._IsDocString(body[0]):
			self._Gap(body[0].lineno - 1)
			self._Emit(body[0].lineno, body[0].end_lineno, state)
			body = body[1:]

		if isinstance(definition, ClassDef):
			self._Block(body, True, None if scope is None else (*scope, definition.name))
		else:
			self._Block(body, False, None)

	def _Compound(self, statement: stmt, scope: Nullable[tuple[str, ...]]) -> None:
		"""
		Take a statement holding classes or functions as written, its classes and functions condensed.

		Such a statement is e.g. an ``if`` choosing between two definitions.

		:param statement: The statement.
		:param scope:     The class names leading to the statement, or ``None`` (see :meth:`_Block`).
		"""
		self._Gap(statement.lineno - 1)
		for definition in self._OutermostDefinitions(statement):
			self._Emit(statement.lineno, self._FirstLine(definition) - 1, "")
			self._Definition(definition, scope)

		self._Emit(statement.lineno, statement.end_lineno, "")

	def _VariableState(self, statement: stmt, scope: Nullable[tuple[str, ...]]) -> str:
		"""
		Return a variable's or field's state, if the model holds one: a module's ``Variables``, a class' ``Fields``.

		:param statement: The assignment, which assigns one name.
		:param scope:     The class names leading to the assignment, or ``None`` (see :meth:`_Block`).
		:returns:         The state, or ``""`` if the model holds none.
		"""
		if isinstance(statement, Assign):
			target = statement.targets[0] if len(statement.targets) == 1 else None
		elif isinstance(statement, AnnAssign):
			target = statement.target
		else:
			target = statement.name

		if scope is None or not isinstance(target, Name):
			return ""

		unit: Any = self._unit
		for className in scope:
			if (unit := unit.Classes.get(className, None)) is None:
				return ""

		states = unit.Fields if len(scope) > 0 else unit.Variables
		if (coverageState := states.get(target.id, None)) is None:
			return ""

		return documentationState(coverageState)

	@staticmethod
	def _FirstLine(statement: stmt) -> int:
		"""
		Return a statement's first line: its first decorator's, if it has decorators.

		:param statement: The statement.
		:returns:         The line number.
		"""
		return min((decorator.lineno for decorator in getattr(statement, "decorator_list", ())), default=statement.lineno)

	@staticmethod
	def _IsDocString(statement: stmt) -> bool:
		"""
		Check if a statement is a string literal: a doc-string at the start of a body, or behind a variable or field.

		:param statement: The statement.
		:returns:         ``True``, if the statement is a string literal.
		"""
		return (
			isinstance(statement, Expr) and isinstance(statement.value, Constant) and isinstance(statement.value.value, str)
		)

	@classmethod
	def _Definitions(cls, node: AST) -> Generator[Definition, None, None]:
		"""
		Yield the classes and functions below a node, in the order docstr_coverage visits them: depth-first, each before
		the ones inside it.

		:param node: The node.
		:returns:    A generator of the classes and functions.
		"""
		for child in iter_child_nodes(node):
			if isinstance(child, DEFINITIONS):
				yield child

			yield from cls._Definitions(child)

	@classmethod
	def _OutermostDefinitions(cls, node: AST) -> Generator[Definition, None, None]:
		"""
		Yield the classes and functions below a node, which aren't inside another class or function below it.

		:param node: The node.
		:returns:    A generator of the classes and functions, in source order.
		"""
		for child in iter_child_nodes(node):
			if isinstance(child, DEFINITIONS):
				yield child
			else:
				yield from cls._OutermostDefinitions(child)


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
		for number, state, indentation in CondensedSource(source, path, expected, entity).Lines:
			if number is None:
				lines.append((None, "", [("", indentation), *ellipsis]))
				text.append(f"{indentation}...")
			else:
				lines.append((number, state, tokens[number - 1]))
				text.append(sourceLines[number - 1])

		plainText = "\n".join(text)
		section += DocCoverageListing(plainText, plainText, lines=lines, path=path)

		return section
