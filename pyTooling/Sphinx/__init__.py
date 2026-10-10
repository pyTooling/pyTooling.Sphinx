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
A Sphinx extension providing the roles, nodes and directives shared by pyTooling and its sibling projects.

Every project in the family used to carry its own :file:`doc/prolog.inc` - eighteen hand-copied files, 36 to 67
lines each, already drifted apart - declaring the same roles as **ReST source** that is re-parsed into every
document of every project. This extension declares them once:

.. code-block:: Python

   # doc/conf.py
   extensions = [
     ...,
     "pyTooling.Sphinx",
   ]

.. rubric:: What it registers

* the **style roles**, together with the stylesheet they need - so the styling is a CSS file instead of a
  ``raw:: html`` block smuggled into every page:

  * ``:bolditalic:``, ``:underline:``, ``:strike:`` and ``:xlarge:`` - weight, decoration and size;
  * ``:red:``, ``:green:``, ``:blue:`` and ``:purple:`` - colour, each from a CSS custom property a project can
    redefine;
  * ``:deletion:`` and ``:addition:`` - the two a diff needs.

* the **code role**:

  * ``:pycode:`` - highlights inline Python.

* the **abbreviation roles**, named as in LaTeX' ``acro`` package:

  * ``:acs:``, ``:acl:`` and ``:acf:`` - an abbreviation, its long form, or both;
  * ``:acsp:``, ``:aclp:`` and ``:acfp:`` - their plurals.

* the **directives**:

  * :rst:dir:`condensed-class` - renders a class' public interface from its source;
  * :rst:dir:`dependency-table` - renders a project's dependencies from its requirements files, which
    :file:`conf.py` declares under ``pyTooling_Dependency_Requirements``;
  * :rst:dir:`xmlschema-graph` - draws an XML schema as a Graphviz graph. It sets up :mod:`sphinx.ext.graphviz`
    itself, and needs :mod:`xmlschema` only in a project that uses it.
  * :rst:dir:`shields` - renders a project's badges from shields.io, in rows, from the coordinates its options
    state: the GitHub repository, the PyPI package, the licenses, the workflow and the documentation's URL.
  * :rst:dir:`tree` - draws a hierarchy written as an indented list as a tree, each node foldable in HTML.
  * :rst:dir:`abbreviations` - lists abbreviations, which the abbreviation roles refer to.

* the domain ``report`` - unit test, code coverage and documentation coverage reports as tables -, with the
  configuration values ``pyTooling_Unittest_Testsuites``, ``pyTooling_CodeCoverage_Packages`` and
  ``pyTooling_DocCoverage_Packages`` declaring the reports. Reading a report needs the extra ``reports``
  (pyEDAA.Reports), which is imported only then:

  * :rst:dir:`report:unittest-summary` - a unit test report, per testsuite and testcase; a report declared with
    ``pages`` gets a page per testsuite and testcase (:mod:`~pyTooling.Sphinx.UnittestPages`), which the roles
    ``:ts:`` and ``:tc:`` - also ``:report:ts:`` and ``:report:tc:`` - refer to;
  * :rst:dir:`report:code-coverage` and :rst:dir:`report:code-coverage-legend` - a code coverage report and its
    coverage levels;
  * :rst:dir:`report:doc-coverage` and :rst:dir:`report:doc-coverage-legend` - a package's documentation coverage
    and its coverage levels.

* the **nodes** the directives emit, listed in :data:`NODES` with their visitors per output format.

Two classes aren't registered, because they are base-classes for a project's own directives:
:class:`~pyTooling.Sphinx.BaseDirective` offers typed option access and table construction
over the untyped mapping and the hand-assembled node trees docutils presents, and
:class:`~pyTooling.Sphinx.SchemaGraph.SchemaGraph` draws a schema file named as a directive's
argument, leaving only the reading of that schema to a derived class.

.. attention::

   This package requires **Python 3.12 or newer**, because it requires Sphinx 9.1 and Sphinx 9.1 does.

.. seealso::

   :mod:`pyTooling.Documentation`
      |rarr| The doc-string helpers, which need no Sphinx.
"""
__author__ =            "Patrick Lehmann"
__email__ =             "Paebbels@gmail.com"
__copyright__ =         "2026-2026, Patrick Lehmann"
__license__ =           "Apache License, Version 2.0"
__version__ =           "0.1.0"
__keywords__ =          ["Sphinx", "Sphinx Extension", "Documentation", "Directive", "Role", "Domain", "docutils"]
__project_url__ =       "https://github.com/pyTooling/pyTooling.Sphinx"
__documentation_url__ = "https://pyTooling.github.io/pyTooling.Sphinx"
__issue_tracker_url__ = "https://GitHub.com/pyTooling/pyTooling.Sphinx/issues"

from enum                    import Enum, Flag
from hashlib                 import md5
from pathlib                 import Path
from re                      import compile as re_compile, match as re_match
from typing                  import Any, Iterable, Iterator, NamedTuple, Optional as Nullable, TypeVar

from docutils                import nodes
from sphinx.addnodes         import pending_xref
from sphinx.application      import Sphinx
from sphinx.builders         import Builder
from sphinx.config           import Config
from sphinx.directives       import ObjectDescription
from sphinx.domains          import Domain, ObjType
from sphinx.environment      import BuildEnvironment
from sphinx.errors           import ExtensionError, NoUri
from sphinx.roles            import XRefRole
from sphinx.util.logging     import getLogger
from sphinx.util.nodes       import make_refnode

from pyTooling.Common        import readResourceFile
from pyTooling.Decorators    import export, readonly
from pyTooling.Documentation import DocumentationError

from pyTooling.Sphinx        import Resources as SphinxResources
from pyTooling.Sphinx.HTML   import translateLandscape as translateLandscapeAsHTML
from pyTooling.Sphinx.HTML   import translateCoverageListing as translateCoverageListingAsHTML
from pyTooling.Sphinx.HTML   import translateAbbreviation, translateTreeItem, translateTreeLabel, translateTreeSeparator
from pyTooling.Sphinx.HTML   import translateTreeDescription
from pyTooling.Sphinx.LaTeX  import translateLandscape as translateLandscapeAsLaTeX
from pyTooling.Sphinx.LaTeX  import translateCoverageListing as translateCoverageListingAsLaTeX
from pyTooling.Sphinx.Node   import Abbreviation, Landscape, RegisteredNode, TreeItem, TreeLabel, TreeSeparator
from pyTooling.Sphinx.Node   import CoverageListing, TreeDescription


__all__ = ["STYLESHEET", "SUBSTITUTIONS", "NODES", "INDENTATION", "LINE_ANCHOR", "REPORT_ROLES"]

#: Name of the stylesheet, in :mod:`pyTooling.Sphinx.Resources`.
STYLESHEET = "pyTooling.css"

#: Substitutions that have to stay substitutions, because ``|br|`` is written as one in every project.
#:
#: ``|br|`` and ``|hr|`` delegate to the ``:br:`` and ``:hr:`` roles rather than writing HTML themselves, so they
#: reach every output format instead of only HTML - see :func:`~pyTooling.Sphinx.Roles.breakRole`.
SUBSTITUTIONS = """
.. |degree| unicode:: U+00B0
   :trim:

.. |br| replace:: :br:`.`

.. |hr| replace:: :hr:`.`
"""

#: The nodes the extension registers, each with its visitors per output format.
#:
#: A format without visitors of its own - e.g. LaTeX for the tree's nodes - writes a node with the visitors of its
#: base-class.
NODES: tuple[RegisteredNode, ...] = (
	{"name": "TreeItem",        "node": TreeItem,        "html": translateTreeItem},
	{"name": "TreeLabel",       "node": TreeLabel,       "html": translateTreeLabel},
	{"name": "TreeSeparator",   "node": TreeSeparator,   "html": translateTreeSeparator},
	{"name": "TreeDescription", "node": TreeDescription, "html": translateTreeDescription},
	{"name": "Abbreviation",    "node": Abbreviation,    "html": translateAbbreviation},
	{"name": "Landscape",       "node": Landscape,       "html": translateLandscapeAsHTML,
	 "latex": translateLandscapeAsLaTeX},
	{"name": "CoverageListing", "node": CoverageListing, "html": translateCoverageListingAsHTML,
	 "latex": translateCoverageListingAsLaTeX},
)


#: The character a report table indents an entry by, per level of the hierarchy: an em quad, which HTML keeps.
INDENTATION = "\u2001"



_EnumType = TypeVar("_EnumType", bound=Enum)
"""Type of an enumeration read from a directive's options."""


@export
class SphinxExtensionError(ExtensionError, DocumentationError):
	"""
	Base-exception of all exceptions raised by :mod:`pyTooling.Sphinx`.

	It derives from **both** hierarchies on purpose: :exc:`~sphinx.errors.ExtensionError` is what Sphinx catches and
	reports with the position of the directive, and :exc:`~pyTooling.Documentation.DocumentationError` is what a
	caller of pyTooling catches. Neither would be enough alone.
	"""


@export
class ReportExtensionError(SphinxExtensionError):
	"""
	The exception raised by the ``report`` domain.

	It is raised e.g. for a mistake in the domain's configuration values or options.
	"""


@export
class ReportsPackageMissingError(ReportExtensionError):
	"""
	The exception raised when a report is read, but the optional packages of the extra ``reports`` aren't installed.

	The message names what was attempted and the packages it needs; a note says how to install them.
	"""

	def __init__(self, task: str, packages: str = "'pyEDAA.Reports'") -> None:
		"""
		Initialize the exception with what was attempted and the packages it needs.

		:param task:     What needs the packages, e.g. ``Reading a unit test report``.
		:param packages: Optional, the packages needed, quoted. Default: ``'pyEDAA.Reports'``.
		"""
		super().__init__(f"{task} needs {packages}, which isn't installed.")
		self.add_note("Install it with: pip install pyTooling.Sphinx[reports]")


@export
class LegendStyle(Flag):
	"""
	How a legend directive of domain ``report`` lays out the coverage levels; a document writes the names with dashes.
	"""

	Default =    0     #: No style.
	Table =      1     #: A table.

	Horizontal = 1024  #: A column per level.
	Vertical =   2048  #: A row per level.

	horizontal_table = Table | Horizontal  #: A table with a column per level, written ``horizontal-table``.
	vertical_table =   Table | Vertical    #: A table with a row per level, written ``vertical-table``.


@export
def strip(option: str) -> str:
	"""
	Option converter removing surrounding whitespace.

	:param option: The option's value as it was written.
	:returns:      The value without surrounding whitespace.
	"""
	return option.strip()


@export
def stripAndNormalize(option: str) -> str:
	"""
	Option converter removing surrounding whitespace and lowering the case.

	:param option: The option's value as it was written.
	:returns:      The value without surrounding whitespace, in lower case.
	"""
	return option.strip().lower()


@export
class BaseDirective(ObjectDescription[str]):
	"""
	Base-class for a directive, offering typed option access and table construction.

	A derived class sets :attr:`directiveName` - which is what the error messages name - and declares
	``option_spec`` as any directive does. What it gets in return is a ``_Parse***Option`` per type instead of
	reaching into :attr:`options` and validating by hand, and a ``_Create***TableHeader`` per table shape instead of
	assembling :class:`~docutils.nodes.tgroup`, :class:`~docutils.nodes.colspec`, :class:`~docutils.nodes.thead`
	and :class:`~docutils.nodes.row` in the right order.
	"""

	has_content =               False  #: A boolean; ``True`` if content is allowed.
	required_arguments =        0      #: Number of required directive arguments.
	optional_arguments =        0      #: Number of optional arguments after the required ones.
	final_argument_whitespace = False  #: A boolean; ``True`` if the last argument may contain spaces.
	option_spec =               {}     #: Mapping of option names to validator functions.

	directiveName: str  #: Name the directive is invoked by, used in every error message.

	def _ParseBooleanOption(self, optionName: str, default: Nullable[bool] = None) -> bool:
		"""
		Read an option written as ``yes``/``true`` or ``no``/``false``.

		:param optionName:             Name of the option to read.
		:param default:                Optional, the value to return when the option wasn't given.
		:returns:                      The option's value.
		:raises SphinxExtensionError:  If the option wasn't given and has no default.
		:raises SphinxExtensionError:  If the option's value is neither of the two accepted spellings.
		"""
		try:
			option = self.options[optionName]
		except KeyError as cause:
			if default is not None:
				return default

			raise SphinxExtensionError(
				f"{self.directiveName}: Required option '{optionName}' not found for directive."
			) from cause

		if option in ("yes", "true"):
			return True
		elif option in ("no", "false"):
			return False

		raise SphinxExtensionError(
			f"{self.directiveName}::{optionName}: '{option}' not supported for a boolean value (yes/true, no/false)."
		)

	def _ParseStringOption(self, optionName: str, default: Nullable[str] = None, regexp: str = "\\w+") -> str:
		"""
		Read an option that has to match a regular expression.

		The pattern defaults to one or more word characters.

		:param optionName:             Name of the option to read.
		:param default:                Optional, the value to return when the option wasn't given.
		:param regexp:                 Optional, the pattern the value has to match.
		:returns:                      The option's value.
		:raises SphinxExtensionError:  If the option wasn't given and has no default.
		:raises SphinxExtensionError:  If the option's value doesn't match the pattern.
		"""
		try:
			option: str = self.options[optionName]
		except KeyError as cause:
			if default is not None:
				return default

			raise SphinxExtensionError(
				f"{self.directiveName}: Required option '{optionName}' not found for directive."
			) from cause

		if re_match(regexp, option):
			return option

		raise SphinxExtensionError(
			f"{self.directiveName}::{optionName}: '{option}' not an accepted value for regexp '{regexp}'."
		)

	def _ParseEnumOption(
		self,
		optionName: str,
		enumType: type[_EnumType],
		default: Nullable[_EnumType] = None
	) -> _EnumType:
		"""
		Read an option naming a member of an enumeration.

		The written value is lowered and its dashes become underscores, so ``horizontal-table`` in a document selects
		the ``horizontal_table`` member - a document reads in the spelling documents use, and the enumeration keeps
		the spelling Python uses.

		:param optionName:             Name of the option to read.
		:param enumType:               The enumeration whose members the value is looked up in.
		:param default:                Optional, the member to return when the option wasn't given.
		:returns:                      The named member of the enumeration.
		:raises SphinxExtensionError:  If the option wasn't given and has no default.
		:raises SphinxExtensionError:  If the value names no member of the enumeration.
		"""
		try:
			option: str = self.options[optionName]
		except KeyError as cause:
			if default is not None:
				return default

			raise SphinxExtensionError(
				f"{self.directiveName}: Required option '{optionName}' not found for directive."
			) from cause

		identifier = option.lower().replace("-", "_")

		try:
			return enumType[identifier]
		except KeyError as cause:
			raise SphinxExtensionError(
				f"{self.directiveName}::{optionName}: Value '{option}' (transformed: '{identifier}') is not a valid "
				f"member of '{enumType.__name__}'."
			) from cause

	def _CreateSingleRowTableHeader(
		self,
		columns: list[tuple[str, Nullable[int]]],
		identifier: str,
		classes: list[str]
	) -> nodes.tgroup:
		"""
		Create a table with a single header row.

		:param columns:    One ``(title, width)`` pair per column; a width of ``None`` leaves it to the writer.
		:param identifier: Identifier of the table.
		:param classes:    CSS classes to put on the table.
		:returns:          The table's column group, with the header row already in it.
		"""
		table = nodes.table("", identifier=identifier, classes=classes)
		table += (tableGroup := nodes.tgroup(cols=(len(columns))))

		# Setup column specifications
		for _, width in columns:
			tableGroup += nodes.colspec(colwidth=width)

		tableGroup += (tableHeader := nodes.thead())
		tableHeader += (headerRow := nodes.row())

		# Setup header row
		for columnTitle, _ in columns:
			headerRow += nodes.entry("", nodes.Text(columnTitle))

		return tableGroup

	def _CreateDoubleRowTableHeader(
		self,
		columns: list[tuple[str, Nullable[list[tuple[str, int]]], Nullable[int]]],
		identifier: str,
		classes: list[str]
	) -> nodes.tgroup:
		"""
		Create a table whose header spans two rows, so a column can group sub-columns.

		A column's ``subColumns`` is ``None`` when it spans both header rows, and otherwise holds the
		``(title, width)`` pairs below it.

		:param columns:    One ``(title, subColumns, width)`` triple per column.
		:param identifier: Identifier of the table.
		:param classes:    CSS classes to put on the table.
		:returns:          The table's column group, with both header rows already in it.
		"""
		columnCount = sum(len(groupColumn[1]) if groupColumn[1] is not None else 1 for groupColumn in columns)

		# Create table with N columns
		table = nodes.table("", identifier=identifier, classes=classes)
		table += (tableGroup := nodes.tgroup(cols=columnCount))

		# Setup column specifications
		for _, more, width in columns:
			if more is None:
				tableGroup += nodes.colspec(colwidth=width)
			else:
				for _, width in more:
					tableGroup += nodes.colspec(colwidth=width)

		tableGroup += (tableHeader := nodes.thead())
		tableHeader += (headerRow1 := nodes.row())

		# Setup primary header row
		for columnTitle, more, _ in columns:
			if more is None:
				headerRow1 += nodes.entry("", nodes.Text(columnTitle), morerows=1)
			else:
				headerRow1 += nodes.entry("", nodes.Text(columnTitle), morecols=(morecols := len(more) - 1))
				for _ in range(morecols):
					headerRow1 += None

		# Setup secondary header row
		tableHeader += (headerRow2 := nodes.row())
		for columnTitle, more, _ in columns:
			if more is None:
				headerRow2 += None
			else:
				for columnTitle, _ in more:
					headerRow2 += nodes.entry("", nodes.Text(columnTitle))

		return tableGroup

	def _CreateRotatedTableHeader(
		self,
		columns: list[tuple[str, Nullable[list[str]]]],
		identifier: str,
		classes: list[str]
	) -> nodes.tgroup:
		"""
		Create a table whose header titles are rotated, for many narrow columns.

		:param columns:    One ``(title, classes)`` pair per column; the classes are put on the header cell.
		:param identifier: Identifier of the table.
		:param classes:    CSS classes to put on the table.
		:returns:          The table's column group, with the header row already in it.
		"""
		table = nodes.table("", identifier=identifier, classes=classes)
		table += (tableGroup := nodes.tgroup(cols=len(columns)))

		# Setup column specifications
		for i, _ in enumerate(columns):
			tableGroup += nodes.colspec(classes=[f"col-{i}"])

		tableGroup += (tableHeader := nodes.thead())
		tableHeader += (headerRow := nodes.row())

		# Setup header row
		for columnTitle, columnClasses in columns:
			span = nodes.inline("", text=columnTitle)
			div = nodes.container("", span)
			headerRow += nodes.entry("", div, classes=[] if columnClasses is None else columnClasses)

		return tableGroup

	def _internalError(
		self,
		container: nodes.container,
		location: str,
		message: str,
		exception: Exception
	) -> list[nodes.Node]:
		"""
		Report an exception a directive couldn't recover from, in the log **and** on the page.

		A directive that fails silently leaves a hole in the documentation that nobody notices. This puts the message
		where a reader sees it and the traceback where a maintainer does. The exception's notes - e.g. how to install a
		missing package - are logged below it.

		:param container: The container the message is put into.
		:param location:  Name of the logger, which is what the log line is attributed to.
		:param message:   What went wrong, in one sentence.
		:param exception: The exception that was caught.
		:returns:         The container, as the list a directive's ``run`` returns.
		"""
		logger = getLogger(location)
		logger.error(f"{message}")
		logger.error(f"  {exception.__class__.__name__}: {exception}")
		for note in getattr(exception, "__notes__", ()):
			logger.error(f"    {note}")

		if exception.__cause__ is not None:
			logger.error(f"    {exception.__cause__.__class__.__name__}: {exception.__cause__}")
		logger.exception(exception)

		container += nodes.paragraph(text=message)

		return [container]


@export
def installStylesheet(sphinx: Sphinx) -> None:
	"""
	Call-back for Sphinx' ``builder-inited`` event, writing the stylesheet into the build and linking it.

	The file is named by the hash of its content, so a browser re-reads it when the styles change and re-uses it when
	they don't. Older copies are removed when the content changed.

	:param sphinx: The Sphinx application.
	"""
	staticDirectory = (Path(sphinx.outdir) / "_pyTooling_static").resolve()
	staticDirectory.mkdir(exist_ok=True)
	sphinx.config.html_static_path.append(str(staticDirectory))

	content = readResourceFile(SphinxResources, STYLESHEET)
	digest = md5(content.encode("utf-8")).hexdigest()          # nosec B324 - a cache-busting name, not a signature
	stylesheet = staticDirectory / f"pyTooling.{digest}.css"
	sphinx.add_css_file(stylesheet.name)

	if not stylesheet.exists():
		# Only this package's own copies - the directory is on 'html_static_path', so another extension may
		# have written its stylesheet beside ours.
		for outdated in staticDirectory.glob("pyTooling.*.css"):
			outdated.unlink()

		stylesheet.write_text(content, encoding="utf-8")


@export
def extendProlog(sphinx: Sphinx, config: Any) -> None:
	"""
	Call-back for Sphinx' ``config-inited`` event, appending the shared substitutions to ``rst_prolog``.

	A role can be registered; a **substitution** cannot - ``|br|`` is substitution syntax, and every project writes
	it that way already. Appending them here is what lets a project delete them from its own prolog without changing
	a single document.

	:param sphinx: The Sphinx application.
	:param config: The configuration, after :file:`conf.py` was read.
	"""
	config.rst_prolog = (config.rst_prolog or "") + SUBSTITUTIONS


@export
class ReportEntry(NamedTuple):
	"""
	An object of a report, which has a page of its own - a testcase, a source file, ...: where it is, and its names.
	"""

	docName:   str              #: Name of the generated document showing the object.
	reportID:  str              #: Identifier of the report in its configuration value.
	path:      tuple[str, ...]  #: Names of the objects from the report's root down to this object's own name.
	separator: str              #: Separator of the names in a qualified name, e.g. ``.`` or ``/``.
	title:     Nullable[str]    #: Title of the object written for a reader, if the report has one.

	@readonly
	def Name(self) -> str:
		"""
		Read-only property to return the object's own name, the last element of :attr:`path`.

		:returns: The name.
		"""
		return self.path[-1]

	@readonly
	def QualifiedName(self) -> str:
		"""
		Read-only property to return the qualified name: the names of :attr:`path` joined by :attr:`separator`.

		:returns: The qualified name, e.g. ``pytest.tests.unit.Arithmetic.Addition.test_Positive``.
		"""
		return self.separator.join(self.path)

	def Matches(self, name: str) -> bool:
		"""
		Check whether a name is the qualified name or a suffix of it, which starts at an element of :attr:`path`.

		:param name: The name as written in a reference, without a report ID.
		:returns:    ``True`` if the name is the qualified name or one of its suffixes.
		"""
		return any(self.separator.join(self.path[index:]) == name for index in range(len(self.path)))


@export
class ReportRoleDefinition(NamedTuple):
	"""
	What a role of domain ``report`` refers to: a kind of object of the reports declared in a configuration value.
	"""

	objectType:  str           #: The object type, as listed by the domain, e.g. ``testcase``.
	configValue: str           #: The configuration value declaring the reports; its first report is the default one.
	reports:     str           #: The reports, as a warning names them, e.g. ``unit test reports``.
	lineAnchors: bool = False  #: Whether a target may end in ``#<line number>``, linking to the line on the page.


#: The line number a target of a role with line anchors may end in, e.g. ``#12`` of ``src/Counter.vhdl#12``.
LINE_ANCHOR = re_compile(r"#(\d+)$")

#: The roles referring to the objects of reports with pages, by role name.
REPORT_ROLES = {
	"tc":  ReportRoleDefinition("testcase",  "pyTooling_Unittest_Testsuites",   "unit test reports"),
	"ts":  ReportRoleDefinition("testsuite", "pyTooling_Unittest_Testsuites",   "unit test reports"),
	"cov": ReportRoleDefinition("source",    "pyTooling_CodeCoverage_Packages", "code coverage reports", True),
}


@export
class ReportRole(XRefRole):
	"""
	A role of domain ``report`` referring to an object of a report with pages.

	Role ``tc`` refers to a testcase, ``ts`` to a testsuite.

	Sphinx registers a role outside a domain without one, so the reference would be resolved by nobody; this role puts
	domain ``report`` on the reference, and uses its name as the reference's type. So it works as ``:report:tc:`` and
	as the global ``:tc:``.
	"""

	def run(self) -> tuple[list[nodes.Node], list[nodes.system_message]]:
		"""
		Create the reference, or only the text if the role is written with ``!``.

		:returns: The nodes and messages a role returns.
		"""
		self.refdomain = ReportDomain.name
		self.reftype = self.name.rpartition(":")[2]
		self.classes = ["xref", ReportDomain.name, f"{ReportDomain.name}-{self.reftype}"]

		if self.disabled:
			return self.create_non_xref_node()

		return self.create_xref_node()


@export
class ReportDomain(Domain):
	"""
	The Sphinx domain ``report``, integrating unit test, code coverage and documentation coverage reports.

	Its directives are registered by :func:`setup`, and read their reports from the files declared in :file:`conf.py`.

	A report with generated pages contributes an object per page - e.g. a unit test report its testsuites and
	testcases -, which the roles of :data:`REPORT_ROLES` refer to, e.g. ``:report:tc:``, also registered as ``:tc:``. A
	reference names an object by its qualified name, or by a suffix of it, optionally preceded by the report's
	identifier and a colon; without one, the first report of the role's configuration value is meant.
	"""

	name =         "report"  #: Name of the domain, the prefix of its directives.
	label =        "rpt"     #: Name of the domain, as displayed.
	data_version = 1         #: Version of the domain data's layout; a pickled environment of another version is dropped.

	object_types = {
		definition.objectType: ObjType(definition.objectType, roleName) for roleName, definition in REPORT_ROLES.items()
	}  #: The objects: per role, the objects of the reports with generated pages.
	initial_data: dict[str, Any] = {
		roleName: {} for roleName in REPORT_ROLES
	}  #: The data of an empty documentation: per role, no object.
	roles = {
		roleName: ReportRole(innernodeclass=nodes.inline, warn_dangling=True) for roleName in REPORT_ROLES
	}  #: The roles, also registered without the domain's prefix.
	dangling_warnings = {
		roleName: f"{definition.objectType} '%(target)s' not found in the {definition.reports}"
		for roleName, definition in REPORT_ROLES.items()
	}  #: The warning for a reference to an unknown object, per role.

	def AddEntry(self, roleName: str, entry: ReportEntry) -> None:
		"""
		Register an object, which has a generated page.

		:param roleName: The role referring to the object, e.g. ``tc`` for a testcase.
		:param entry:    The object.
		"""
		self.data[roleName].setdefault(entry.reportID, {})[entry.QualifiedName] = entry

	def FindEntries(self, roleName: str, target: str) -> list[ReportEntry]:
		"""
		Find the objects a reference's target names.

		A target is ``[<report ID>:]<name>``. If the part before the first colon isn't the identifier of a report, the
		whole target is the name in the default report - the first one of the role's configuration value -, as e.g. a
		parametrized testcase's name may contain a colon. A name is a qualified name or a suffix of one (see
		:meth:`ReportEntry.Matches`); an exact qualified name wins over suffixes.

		:param roleName: The role referring to the object, e.g. ``tc`` for a testcase.
		:param target:   The reference's target.
		:returns:        The matching entries: none, one, or several if the name is ambiguous.
		"""
		reports: dict[str, dict[str, ReportEntry]] = self.data[roleName]
		configuredReports = list(self.env.config[REPORT_ROLES[roleName].configValue])

		reportID, separator, name = target.partition(":")
		if separator == "" or reportID not in configuredReports:
			if len(configuredReports) == 0:
				return []

			reportID, name = configuredReports[0], target

		entries = reports.get(reportID, {})
		if (entry := entries.get(name)) is not None:
			return [entry]

		return [entry for entry in entries.values() if entry.Matches(name)]

	def clear_doc(self, docname: str) -> None:
		"""
		Forget the objects of a document, before it is generated again.

		:param docname: Name of the document.
		"""
		for roleName in REPORT_ROLES:
			for entries in self.data[roleName].values():
				for qualifiedName in [name for name, entry in entries.items() if entry.docName == docname]:
					del entries[qualifiedName]

	def merge_domaindata(self, docnames: Iterable[str], otherdata: dict[str, Any]) -> None:
		"""
		Take over the objects a parallel reader collected for its documents.

		:param docnames:  Names of the documents the other reader read.
		:param otherdata: The other reader's domain data.
		"""
		documents = set(docnames)
		for roleName in REPORT_ROLES:
			for reportID, entries in otherdata[roleName].items():
				ownEntries = self.data[roleName].setdefault(reportID, {})
				for qualifiedName, entry in entries.items():
					if entry.docName in documents:
						ownEntries[qualifiedName] = entry

	def resolve_xref(
		self,
		env: BuildEnvironment,
		fromdocname: str,
		builder: Builder,
		typ: str,
		target: str,
		node: pending_xref,
		contnode: nodes.Element
	) -> Nullable[nodes.Element]:
		"""
		Resolve a reference to an object of a report into a link to its page.

		The link shows the object's name, or the title written in the role; in HTML, its title written for a reader - if
		the report has one - is shown on hover. An ambiguous name is warned about and shown as text.

		:param env:         The build environment.
		:param fromdocname: Name of the document holding the reference.
		:param builder:     The builder writing the documents.
		:param typ:         The role's name, e.g. ``tc``.
		:param target:      The object referred to.
		:param node:        The reference.
		:param contnode:    The reference's text.
		:returns:           The link, the text if the name is ambiguous or the builder doesn't write the page, or
		                    ``None`` if nothing matches.
		"""
		if typ not in REPORT_ROLES:
			return None

		anchor = line = ""
		if REPORT_ROLES[typ].lineAnchors and (match := LINE_ANCHOR.search(target)) is not None:
			target, line = target[:match.start()], match[1]
			anchor = f"L{line}"

		entries = self.FindEntries(typ, target)
		if len(entries) == 0:
			return None
		elif len(entries) > 1:
			candidates = ", ".join(sorted(f"{entry.reportID}:{entry.QualifiedName}" for entry in entries))
			getLogger(__name__).warning(
				f"{REPORT_ROLES[typ].objectType} '{target}' is ambiguous, candidates: {candidates}",
				location=node, type="ref", subtype=typ
			)
			return contnode

		entry = entries[0]
		if node.get("refexplicit", False):
			content = contnode
		else:
			text = entry.Name if line == "" else f"{entry.Name}:{line}"
			content = nodes.inline(text, text, classes=contnode["classes"])

		try:
			return make_refnode(builder, fromdocname, entry.docName, anchor or None, content, entry.title)
		except NoUri:
			# a builder may not write every document, so a link to a page becomes the name
			return content

	def resolve_any_xref(
		self,
		env: BuildEnvironment,
		fromdocname: str,
		builder: Builder,
		target: str,
		node: pending_xref,
		contnode: nodes.Element
	) -> list[tuple[str, nodes.reference]]:
		"""
		Resolve a reference of role ``:any:`` to an object of a report with an unambiguous name.

		:param env:         The build environment.
		:param fromdocname: Name of the document holding the reference.
		:param builder:     The builder writing the documents.
		:param target:      The text referred to.
		:param node:        The reference.
		:param contnode:    The reference's text.
		:returns:           A role and link per kind of object the text names unambiguously.
		"""
		results: list[tuple[str, nodes.reference]] = []
		for roleName in REPORT_ROLES:
			if len(entries := self.FindEntries(roleName, target)) == 1:
				entry = entries[0]
				content = nodes.inline(entry.Name, entry.Name, classes=contnode["classes"])
				reference = make_refnode(builder, fromdocname, entry.docName, None, content, entry.title)
				results.append((f"{self.name}:{roleName}", reference))

		return results

	def get_objects(self) -> Iterator[tuple[str, str, str, str, str, int]]:
		"""
		Name the objects of the reports, for the search and for other documentations referring to them.

		An object's name is ``<report ID>:<qualified name>``. A testcase gets a lower search priority than a testsuite,
		as a report may have thousands of them.

		:returns: A tuple per object: name, display name, type, document, anchor and search priority.
		"""
		for roleName, definition in REPORT_ROLES.items():
			priority = 2 if roleName == "tc" else 1
			for reportID, entries in self.data[roleName].items():
				for qualifiedName, entry in entries.items():
					yield f"{reportID}:{qualifiedName}", entry.QualifiedName, definition.objectType, entry.docName, "", priority


@export
def checkReportConfiguration(sphinx: Sphinx, config: Config) -> None:
	"""
	Call-back for Sphinx' ``config-inited`` event, checking the reports' configuration values and loading their settings.

	A mistake is logged as an error rather than stopping the build; a directive naming that report fails on its own.

	:param sphinx: The Sphinx application.
	:param config: The configuration, after :file:`conf.py` was read.
	"""
	from pyTooling.Sphinx.CodeCoverage import CodeCoverageBase
	from pyTooling.Sphinx.DocCoverage  import DocCoverageBase
	from pyTooling.Sphinx.Unittest     import UnittestSummary

	checkConfigurations = (
		CodeCoverageBase.CheckConfiguration,
		DocCoverageBase.CheckConfiguration,
		UnittestSummary.CheckConfiguration,
	)

	for check in checkConfigurations:
		try:
			check(sphinx, config)
		except ReportExtensionError as ex:
			getLogger(__name__).error(f"Caught {ex.__class__.__name__} when checking configuration variables.\n  {ex}")


@export
def readReports(sphinx: Sphinx) -> None:
	"""
	Call-back for Sphinx' ``builder-inited`` event, reading the report files and registering the unit test reports' pages.

	:param sphinx: The Sphinx application.
	"""
	from pyTooling.Sphinx.CodeCoverage      import CodeCoverageBase
	from pyTooling.Sphinx.CodeCoveragePages import CodeCoverageReportPages
	from pyTooling.Sphinx.Unittest          import UnittestSummary
	from pyTooling.Sphinx.UnittestPages     import UnittestReportPages

	CodeCoverageBase.ReadReports(sphinx)
	UnittestSummary.ReadReports(sphinx)
	CodeCoverageReportPages.CreatePages(sphinx)
	UnittestReportPages.CreatePages(sphinx)


@export
def setup(sphinx: Sphinx) -> dict[str, Any]:
	"""
	Register the roles, the nodes, the directives and the domain ``report`` with Sphinx.

	The modules are imported here rather than with the package, and none of them imports an optional dependency at
	module level - e.g. pyEDAA.Reports is imported only when a report is read - so the extension works without them.

	:param sphinx: The Sphinx application to register with.
	:returns:      The extension's metadata.
	"""
	from pyTooling.Sphinx.Abbreviation      import CONFIG_PREFIX as ABBREVIATION_PREFIX
	from pyTooling.Sphinx.Abbreviation      import ROLES as ABBREVIATION_ROLES, AbbreviationDomain, AbbreviationRole
	from pyTooling.Sphinx.Abbreviation      import Abbreviations
	from pyTooling.Sphinx.CodeCoverage      import CONFIG_PREFIX as CODE_COVERAGE_PREFIX
	from pyTooling.Sphinx.CodeCoverage      import CodeCoverage, CodeCoverageBase, CodeCoverageLegend, FileCoverage
	from pyTooling.Sphinx.CodeCoveragePages import CodeCoverageReportPages
	from pyTooling.Sphinx.CondensedClass    import CondensedClass
	from pyTooling.Sphinx.DependencyTable   import CONFIG_PREFIX, DependencyTable, prepareEntrypoints, reportBuildTime
	from pyTooling.Sphinx.DocCoverage       import CONFIG_PREFIX as DOC_COVERAGE_PREFIX
	from pyTooling.Sphinx.DocCoverage       import DocCoverageBase, DocCoverageLegend, DocStrCoverage
	from pyTooling.Sphinx.Roles             import BREAK_ROLES, PYTHON_CODE_ROLE, STYLE_ROLES
	from pyTooling.Sphinx.Roles             import breakRole, pythonCodeRole, styleRole
	from pyTooling.Sphinx.Shields           import Shields
	from pyTooling.Sphinx.Tree              import Tree
	from pyTooling.Sphinx.Unittest          import CONFIG_PREFIX as UNITTEST_PREFIX
	from pyTooling.Sphinx.Unittest          import UnittestSummary
	from pyTooling.Sphinx.UnittestPages     import UnittestReportPages
	from pyTooling.Sphinx.Workaround        import FixLatexTableWidths
	from pyTooling.Sphinx.XMLSchemaGraph    import XMLSchemaGraph

	for roleName in STYLE_ROLES:
		sphinx.add_role(roleName, styleRole)

	for roleName in BREAK_ROLES:
		sphinx.add_role(roleName, breakRole)

	sphinx.add_role(PYTHON_CODE_ROLE, pythonCodeRole)

	# the abbreviation roles outside their domain too, as LaTeX' 'acro' names them: ':acs:', not ':abbreviation:acs:'
	sphinx.add_domain(AbbreviationDomain)
	for roleName in ABBREVIATION_ROLES:
		sphinx.add_role(roleName, AbbreviationRole(innernodeclass=nodes.inline, warn_dangling=True))

	# the report roles outside their domain too: ':tc:', not only ':report:tc:'
	for roleName in REPORT_ROLES:
		sphinx.add_role(roleName, ReportRole(innernodeclass=nodes.inline, warn_dangling=True))

	sphinx.add_directive("condensed-class", CondensedClass)
	sphinx.add_directive("dependency-table", DependencyTable)
	sphinx.add_directive("xmlschema-graph", XMLSchemaGraph)
	sphinx.add_directive("shields", Shields)
	sphinx.add_directive("tree", Tree)
	sphinx.add_directive("abbreviations", Abbreviations)

	# Without the domain, these become global directives: 'add_directive' instead of 'add_directive_to_domain'.
	reportDirectives = {
		"code-coverage":        CodeCoverage,
		"code-coverage-legend": CodeCoverageLegend,
		"file-coverage":        FileCoverage,
		"doc-coverage":         DocStrCoverage,
		"doc-coverage-legend":  DocCoverageLegend,
		"unittest-summary":     UnittestSummary,
	}
	sphinx.add_domain(ReportDomain)
	for directiveName, directive in reportDirectives.items():
		sphinx.add_directive_to_domain(ReportDomain.name, directiveName, directive)

	for registeredNode in NODES:
		if "latex" in registeredNode:
			sphinx.add_node(registeredNode["node"], html=registeredNode["html"], latex=registeredNode["latex"])
		else:
			sphinx.add_node(registeredNode["node"], html=registeredNode["html"])

	# the report tables are put into 'Landscape' nodes, whose LaTeX environment is package 'pdflscape''s
	sphinx.add_latex_package("pdflscape")
	sphinx.add_post_transform(FixLatexTableWidths)

	sphinx.setup_extension("sphinx.ext.graphviz")

	for prefix, configValues in (
		(CONFIG_PREFIX,        DependencyTable.configValues),
		(CODE_COVERAGE_PREFIX, CodeCoverageBase.configValues),
		(DOC_COVERAGE_PREFIX,  DocCoverageBase.configValues),
		(UNITTEST_PREFIX,      UnittestSummary.configValues),
	):
		for configName, (default, rebuild, types) in configValues.items():
			sphinx.add_config_value(f"{prefix}_{configName}", default, rebuild, types)

	for configName, (default, rebuild, types) in Abbreviations.configValues.items():
		sphinx.add_config_value(f"{ABBREVIATION_PREFIX}_{configName}", default, rebuild, types)

	sphinx.connect("config-inited", extendProlog)
	# after the configuration values above are registered, and before any document is read - a requirements file
	# that doesn't exist should end the build here rather than in the middle of a page
	sphinx.connect("config-inited", prepareEntrypoints)
	sphinx.connect("config-inited", checkReportConfiguration)
	sphinx.connect("builder-inited", readReports)
	for reportPages in (CodeCoverageReportPages, UnittestReportPages):
		sphinx.connect("env-before-read-docs", reportPages.GenerateAll)
		sphinx.connect("html-page-context", reportPages.HideSource)
	sphinx.connect("build-finished", reportBuildTime)
	sphinx.connect("builder-inited", installStylesheet)

	# The extension's version is the package's, so a second number to keep in step would only ever disagree.
	return {"version": __version__, "parallel_read_safe": True, "parallel_write_safe": True}
