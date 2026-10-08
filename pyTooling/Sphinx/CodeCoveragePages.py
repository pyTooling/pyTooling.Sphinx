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
A page per directory and per source file of a code coverage report, generated without a source file.

A report declared in ``pyTooling_CodeCoverage_Packages`` with the key ``pages`` gets a document per directory and per
source file, named below that key's document name by its path in the report, e.g. ``<pages>/src/Counter.vhdl``. A
chain of directories holding no file and one directory each is one page, e.g. ``pyTooling/Sphinx`` (see
:func:`~pyTooling.Sphinx.CodeCoverage.compactDirectory`).

* A directory's page shows its counters, and tables of its directories and files, each linked to its page.
* A source file's page shows its counters, its missed lines, and its listing: the source read from the report's
  ``sources`` directory, syntax highlighted with the Pygments lexer of the file's name, each line marked by its
  coverage state.

The pages are built by the machinery of :class:`~pyTooling.Sphinx.Pages.ReportPages`, so they are in the navigation
below the directive ``report:code-coverage``. Every directory and file with a page is an object of domain ``report``,
referred to by the role ``:cov:`` by its path - e.g. ``:cov:`src/Counter.vhdl``` -, which may end in ``#<line>`` to
link to a line of a file's listing.

.. seealso::

   :ref:`DIR/CodeCoverage/Pages`
      |rarr| The pages and the role, with examples.
   :mod:`pyTooling.Sphinx.Pages`
      |rarr| The pages of a report: document names, registration, generation and navigation.
"""
from __future__                    import annotations

from pathlib                       import Path
from typing                        import TYPE_CHECKING, ClassVar, Iterable, Optional as Nullable, Union

from docutils                      import nodes
from pygments.lexers               import get_lexer_for_filename
from pygments.lexers.special       import TextLexer
from pygments.token                import STANDARD_TYPES, _TokenType
from pygments.util                 import ClassNotFound
from sphinx.application            import Sphinx
from sphinx.util.logging           import getLogger

from pyTooling.Decorators          import export

from pyTooling.Sphinx              import ReportExtensionError
from pyTooling.Sphinx.CodeCoverage import CodeCoverageBase, compactDirectory, compactedName, isCompacted
from pyTooling.Sphinx.Node         import CoverageListing
from pyTooling.Sphinx.Pages        import ReportPages

if TYPE_CHECKING:  # pragma: no cover
	# pyEDAA.Reports is an optional dependency (extra 'reports'), imported where a report is read.
	from pyEDAA.Reports.CodeCoverage import BaseWithPath, CoverageSummary, Directory, File


__all__ = ["LINE_STATES"]

#: The state a listing marks a line with, by the name of the line's
#: :class:`~pyEDAA.Reports.CodeCoverage.LineCoverageStatus`.
LINE_STATES = {
	"Covered":          "covered",
	"PartiallyCovered": "partial",
	"Uncovered":        "uncovered",
	"Excluded":         "excluded",
	"Unknown":          "",
}


@export
def tokenClass(tokenType: _TokenType) -> str:
	"""
	Return the short CSS class Pygments writes for a token type - e.g. ``k`` for a keyword -, as its HTML formatter does.

	A token type without a class of its own gets its nearest parent's class, extended by the names below it.

	:param tokenType: The token type.
	:returns:         The CSS class; empty for plain text.
	"""
	suffix = ""
	while (name := STANDARD_TYPES.get(tokenType)) is None:
		suffix = f"-{tokenType[-1]}{suffix}"
		tokenType = tokenType.parent

	return f"{name}{suffix}"


@export
def tokenizeSource(source: str, fileName: str) -> list[list[tuple[str, str]]]:
	"""
	Lex a source file with the Pygments lexer of its file name, and split the tokens into lines.

	The whole file is lexed, as a token may span lines - e.g. a doc-string -; such a token is split at the line ends, each
	part keeping its class. A file name without a lexer is lexed as plain text.

	:param source:   The source file's content.
	:param fileName: The source file's name, choosing the lexer.
	:returns:        Per line, its tokens as ``(CSS class, text)`` pairs.
	"""
	try:
		lexer = get_lexer_for_filename(fileName, stripnl=False, ensurenl=True)
	except ClassNotFound:
		lexer = TextLexer(stripnl=False, ensurenl=True)

	lines: list[list[tuple[str, str]]] = [[]]
	for tokenType, value in lexer.get_tokens(source):
		cssClass = tokenClass(tokenType)
		for index, part in enumerate(value.split("\n")):
			if index > 0:
				lines.append([])

			if part != "":
				lines[-1].append((cssClass, part))

	return lines[:-1] if len(lines[-1]) == 0 else lines


@export
def createListing(file: File, sources: Path, anchors: bool) -> Union[CoverageListing, nodes.paragraph]:
	"""
	Create a source file's listing: its lines, syntax highlighted, each marked by its coverage state.

	A report naming a line beyond the source file's end was measured on another version of the file; this is logged as
	a warning.

	:param file:    The file of the report.
	:param sources: The directory the report's file paths are relative to.
	:param anchors: Whether a line gets the ID ``L<number>``, so the role ``:cov:`` can link to it.
	:returns:       The listing; or a paragraph saying so, if the source file can't be read.
	"""
	sourceFile = sources / file.Path
	try:
		source = sourceFile.read_text(encoding="utf-8", errors="replace")
	except OSError as ex:
		getLogger(__name__).warning(f"Source file '{sourceFile}' of the code coverage report can't be read: {ex}")
		return nodes.paragraph(text=f"The source file '{file.Path.as_posix()}' can't be read.")

	tokens = tokenizeSource(source, file._name)
	if (lastLineNumber := file.LastLineNumber) > len(tokens):
		getLogger(__name__).warning(
			f"The code coverage report names line {lastLineNumber} of '{file.Path.as_posix()}', which has {len(tokens)} "
			f"lines: the report wasn't measured on this version of the file."
		)

	fileLines = file.Lines
	lines = []
	for number, lineTokens in enumerate(tokens, start=1):
		if number > lastLineNumber or (line := fileLines[number]) is None:
			lines.append((number, "", None, 0, 0, lineTokens))
		else:
			state = LINE_STATES[line._status.name]
			lines.append((number, state, line._coverageCount, len(line._branches), line.CoveredBranches, lineTokens))

	return CoverageListing(source, source, lines=lines, anchors=anchors, path=file.Path.as_posix(), language="text")


@export
class CodeCoverageReportPages(ReportPages):
	"""
	The pages of one code coverage report: a page per directory and per source file.
	"""

	_reportPages: ClassVar[dict[str, ReportPages]] = {}  #: The pages of every code coverage report with pages, by ID.
	_separator:   ClassVar[str] = "/"                    #: Separator of the names in a path.

	_sources: Path                                   #: Directory the report's file paths are relative to.
	_levels:  dict[Union[int, str], dict[str, str]]  #: The report's coverage levels, coloring the tables.

	def __init__(
		self,
		reportID: str,
		prefix: str,
		reportFile: Path,
		coverage: CoverageSummary,
		sources: Path,
		levels: dict[Union[int, str], dict[str, str]]
	) -> None:
		"""
		Compute the document names and entries of a report's directories and source files.

		:param reportID:   Identifier of the report.
		:param prefix:     Document name the pages are generated below.
		:param reportFile: The report file.
		:param coverage:   The report's root directory.
		:param sources:    Directory the report's file paths are relative to.
		:param levels:     The report's coverage levels.
		"""
		super().__init__(reportID, prefix, reportFile, self._DirectoryChildren(coverage))

		self._sources = sources
		self._levels =  levels

	@classmethod
	def CreatePages(cls, sphinxApplication: Sphinx) -> None:
		"""
		Call-back for Sphinx' ``builder-inited`` event, after the reports are read: compute and register the pages.

		Only a report with the key ``pages`` gets pages. A report that couldn't be read gets none; this is logged as an
		error.

		:param sphinxApplication: Sphinx application instance.
		"""
		cls._reportPages = {}
		for reportID, packageConfiguration in CodeCoverageBase._packageConfigurations.items():
			if (prefix := packageConfiguration["pages"]) is None:
				continue

			try:
				coverage = CodeCoverageBase.GetReport(reportID)
			except ReportExtensionError as ex:
				cause = ex if ex.__cause__ is None else ex.__cause__
				getLogger(__name__).error(
					f"Caught {ex.__class__.__name__} when generating the pages of code coverage report '{reportID}'.\n"
					f"  {cause.__class__.__name__}: {cause}"
				)
				continue

			pages = cls(
				reportID, prefix, packageConfiguration["report"], coverage, packageConfiguration["sources"],
				packageConfiguration["levels"]
			)
			cls._reportPages[reportID] = pages
			pages.Register(sphinxApplication.env)

	@staticmethod
	def _DirectoryChildren(directory: Directory) -> list[tuple[str, BaseWithPath]]:
		"""
		Return a directory's directories - each compacted with its single subdirectories -, then its files, each sorted by
		name.

		:param directory: The directory.
		:returns:         The children as ``(role name, object)`` pairs.
		"""
		children: list[tuple[str, BaseWithPath]] = []
		children.extend(("cov", compactDirectory(directory._directories[name])) for name in sorted(directory._directories))
		children.extend(("cov", directory._files[name]) for name in sorted(directory._files))

		return children

	def _Name(self, entity: BaseWithPath) -> str:
		"""
		Return the name a directory or file is shown with; a compacted directory's includes its parents' names.

		:param entity: The directory or file.
		:returns:      The name, e.g. ``Counter.vhdl`` or ``pyTooling/Sphinx``.
		"""
		return compactedName(entity)

	def _PathElements(self, name: str) -> tuple[str, ...]:
		"""
		Return the elements a name adds to the path: a compacted directory's name adds one per directory.

		:param name: The directory's or file's name.
		:returns:    The path elements.
		"""
		return tuple(name.split("/"))

	def _Title(self, entity: BaseWithPath) -> Nullable[str]:
		"""
		Return no title, as a report has none for its directories and files.

		:param entity: The directory or file.
		:returns:      ``None``
		"""
		return None

	def _Children(self, roleName: str, entity: BaseWithPath) -> Iterable[tuple[str, BaseWithPath]]:
		"""
		Return a directory's directories, then its files; a file has none.

		:param roleName: The role referring to the object: ``cov``.
		:param entity:   The directory or file.
		:returns:        The children as ``(role name, object)`` pairs.
		"""
		if hasattr(entity, "_directories"):
			return self._DirectoryChildren(entity)

		return []

	def _Page(self, docName: str, roleName: str, entity: BaseWithPath) -> nodes.section:
		"""
		Build a directory's or file's page.

		:param docName:  Name of the page's document.
		:param roleName: The role referring to the object: ``cov``.
		:param entity:   The directory or file.
		:returns:        The page's top section.
		"""
		if hasattr(entity, "_directories"):
			return self._DirectoryPage(docName, entity)
		else:
			return self._FilePage(docName, entity)

	def _SummarySection(self, docName: str, entity: BaseWithPath) -> tuple[nodes.section, nodes.field_list]:
		"""
		Create a page's section *Summary*: the line and branch counters, the coverage, and the parent directory.

		:param docName: Name of the page's document.
		:param entity:  The directory or file.
		:returns:       The section, and its field list, which a page may add fields to.
		"""
		section = nodes.section("", nodes.title("Summary", "Summary"), ids=["summary"])
		section += (fieldList := nodes.field_list(classes=["report-codecov-fields"]))

		self._Field(fieldList, "Lines", nodes.Text(
			f"{entity.CoveredLines} of {entity.TotalLines} covered ({entity.LineCoverage:.1%})"
		))
		if entity.ExcludedLines > 0:
			self._Field(fieldList, "Excluded lines", nodes.Text(f"{entity.ExcludedLines}"))

		if entity.TotalBranches > 0:
			self._Field(fieldList, "Branches", nodes.Text(
				f"{entity.CoveredBranches} of {entity.TotalBranches} taken ({entity.BranchCoverage:.1%}), "
				f"{entity.PartialLines} lines partially"
			))
		self._Field(fieldList, "Coverage", nodes.Text(f"{entity.Coverage:.1%}"))

		parent = entity._parent
		while isCompacted(parent):
			parent = parent._parent

		if parent is not None and parent._parent is not None:
			self._Field(fieldList, "Directory", self._Reference("cov", parent, docName))

		return section, fieldList

	def _DirectoryPage(self, docName: str, directory: Directory) -> nodes.section:
		"""
		Build a directory's page: its counters, then tables of its directories and files, each linked to its page.

		:param docName:   Name of the page's document.
		:param directory: The directory.
		:returns:         The page's top section.
		"""
		name = compactedName(directory)
		page = nodes.section("", nodes.title(name, name), ids=["report-codecov-page"])
		summarySection, _ = self._SummarySection(docName, directory)
		page += summarySection

		children: list[str] = []
		subdirectories = [child for _, child in self._DirectoryChildren(directory) if hasattr(child, "_directories")]
		files = [directory._files[fileName] for fileName in sorted(directory._files)]
		for title, column, identifier, entities in (
			("Directories", "Directory", "directories", subdirectories),
			("Files",       "File",      "files",       files),
		):
			if len(entities) == 0:
				continue

			page += (section := nodes.section("", nodes.title(title, title), ids=[identifier]))
			table, tableBody = self._Table(
				[(column, 6), ("Lines", 2), ("Branches", 2), ("Coverage", 1)],
				["report-codecov-table", "report-codecov-children"]
			)
			section += table
			for entity in entities:
				level = CodeCoverageBase.LevelOf(self._levels, entity.Coverage, "class")
				tableBody += (row := nodes.row("", classes=[level]))
				row += nodes.entry("", nodes.paragraph("", "", self._Reference("cov", entity, docName)))
				row += nodes.entry("", nodes.paragraph("", f"{entity.CoveredLines} of {entity.TotalLines}"))
				row += nodes.entry("", nodes.paragraph("", f"{entity.CoveredBranches} of {entity.TotalBranches}"))
				row += nodes.entry("", nodes.paragraph("", f"{entity.Coverage:.1%}"))
				if (entry := self.Entry(entity)) is not None:
					children.append(entry.docName)

		if len(children) > 0:
			# body elements precede a section's subsections, so the hidden table of contents goes before 'Summary'
			page.insert(page.index(summarySection), self._TableOfContents(docName, children))

		return page

	def _FilePage(self, docName: str, file: File) -> nodes.section:
		"""
		Build a source file's page: its counters, its missed lines, and its listing.

		:param docName: Name of the page's document.
		:param file:    The source file.
		:returns:       The page's top section.
		"""
		page = nodes.section("", nodes.title(file._name, file._name), ids=["report-codecov-page"])
		summarySection, fieldList = self._SummarySection(docName, file)
		page += summarySection

		if (missed := self._MissedLines(file)) != "":
			self._Field(fieldList, "Missed lines", nodes.Text(missed))

		page += (section := nodes.section("", nodes.title("Source", "Source"), ids=["source"]))
		section += createListing(file, self._sources, anchors=True)

		return page

	@staticmethod
	def _MissedLines(file: File) -> str:
		"""
		Return a file's lines, which never ran, as ranges of consecutive executable lines, as coverage.py writes them.

		:param file: The source file.
		:returns:    The ranges, e.g. ``8, 14-17``; empty if every executable line ran.
		"""
		ranges: list[str] = []
		start = end = None
		for line in file.IterateLines():
			number = line._lineNumber
			state =  line._status.name
			if state == "Excluded":
				continue

			if state == "Uncovered":
				start = number if start is None else start
				end = number
			elif start is not None:
				ranges.append(f"{start}" if start == end else f"{start}-{end}")
				start = None

		if start is not None:
			ranges.append(f"{start}" if start == end else f"{start}-{end}")

		return ", ".join(ranges)
