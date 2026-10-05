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

* the **nodes** the directives emit, listed in :data:`NODES` with their visitors per output format.

The domain ``report`` - unit test, code coverage and documentation coverage reports as tables - is the extension
:mod:`pyTooling.Sphinx.Report`, enabled separately as ``"pyTooling.Sphinx.Report"``, because it needs the extra
``reports``. It sets up this extension itself, and adds the configuration values ``pyTooling_Unittest_Testsuites``,
``pyTooling_CodeCoverage_Packages`` and ``pyTooling_DocCoverage_Packages``:

* :rst:dir:`report:unittest-summary` - a unit test report, per testsuite and testcase;
* :rst:dir:`report:code-coverage` and :rst:dir:`report:code-coverage-legend` - a code coverage report and its
  coverage levels;
* :rst:dir:`report:doc-coverage` and :rst:dir:`report:doc-coverage-legend` - a package's documentation coverage and
  its coverage levels.

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

from enum                    import Enum
from hashlib                 import md5
from pathlib                 import Path
from re                      import match as re_match
from typing                  import Any, Optional as Nullable, TypeVar

from docutils                import nodes
from sphinx.application      import Sphinx
from sphinx.directives       import ObjectDescription
from sphinx.errors           import ExtensionError
from sphinx.util.logging     import getLogger

from pyTooling.Common        import readResourceFile
from pyTooling.Decorators    import export
from pyTooling.Documentation import DocumentationError

from pyTooling.Sphinx        import Resources as SphinxResources
from pyTooling.Sphinx.HTML   import translateLandscape as translateLandscapeAsHTML
from pyTooling.Sphinx.HTML   import translateAbbreviation, translateTreeItem, translateTreeLabel
from pyTooling.Sphinx.LaTeX  import translateLandscape as translateLandscapeAsLaTeX
from pyTooling.Sphinx.Node   import Abbreviation, Landscape, RegisteredNode, TreeItem, TreeLabel


__all__ = ["STYLESHEET", "SUBSTITUTIONS", "NODES"]

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
	{"name": "TreeItem",     "node": TreeItem,     "html": translateTreeItem},
	{"name": "TreeLabel",    "node": TreeLabel,    "html": translateTreeLabel},
	{"name": "Abbreviation", "node": Abbreviation, "html": translateAbbreviation},
	{"name": "Landscape",    "node": Landscape,    "html": translateLandscapeAsHTML, "latex": translateLandscapeAsLaTeX},
)


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
		where a reader sees it and the traceback where a maintainer does.

		:param container: The container the message is put into.
		:param location:  Name of the logger, which is what the log line is attributed to.
		:param message:   What went wrong, in one sentence.
		:param exception: The exception that was caught.
		:returns:         The container, as the list a directive's ``run`` returns.
		"""
		logger = getLogger(location)
		logger.error(f"{message}")
		logger.error(f"  {exception.__class__.__name__}: {exception}")
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
def setup(sphinx: Sphinx) -> dict[str, Any]:
	"""
	Register the roles, the nodes and the directives with Sphinx.

	:param sphinx: The Sphinx application to register with.
	:returns:      The extension's metadata.
	"""
	from pyTooling.Sphinx.Abbreviation    import CONFIG_PREFIX as ABBREVIATION_PREFIX
	from pyTooling.Sphinx.Abbreviation    import ROLES as ABBREVIATION_ROLES, AbbreviationDomain, AbbreviationRole
	from pyTooling.Sphinx.Abbreviation    import Abbreviations
	from pyTooling.Sphinx.CondensedClass  import CondensedClass
	from pyTooling.Sphinx.DependencyTable import CONFIG_PREFIX, DependencyTable, prepareEntrypoints, reportBuildTime
	from pyTooling.Sphinx.Roles           import BREAK_ROLES, PYTHON_CODE_ROLE, STYLE_ROLES
	from pyTooling.Sphinx.Roles           import breakRole, pythonCodeRole, styleRole
	from pyTooling.Sphinx.Shields         import Shields
	from pyTooling.Sphinx.Tree            import Tree
	from pyTooling.Sphinx.XMLSchemaGraph  import XMLSchemaGraph

	for roleName in STYLE_ROLES:
		sphinx.add_role(roleName, styleRole)

	for roleName in BREAK_ROLES:
		sphinx.add_role(roleName, breakRole)

	sphinx.add_role(PYTHON_CODE_ROLE, pythonCodeRole)

	# the abbreviation roles outside their domain too, as LaTeX' 'acro' names them: ':acs:', not ':abbreviation:acs:'
	sphinx.add_domain(AbbreviationDomain)
	for roleName in ABBREVIATION_ROLES:
		sphinx.add_role(roleName, AbbreviationRole(innernodeclass=nodes.inline, warn_dangling=True))

	sphinx.add_directive("condensed-class", CondensedClass)
	sphinx.add_directive("dependency-table", DependencyTable)
	sphinx.add_directive("xmlschema-graph", XMLSchemaGraph)
	sphinx.add_directive("shields", Shields)
	sphinx.add_directive("tree", Tree)
	sphinx.add_directive("abbreviations", Abbreviations)

	for registeredNode in NODES:
		if "latex" in registeredNode:
			sphinx.add_node(registeredNode["node"], html=registeredNode["html"], latex=registeredNode["latex"])
		else:
			sphinx.add_node(registeredNode["node"], html=registeredNode["html"])

	sphinx.setup_extension("sphinx.ext.graphviz")

	for configName, (default, rebuild, types) in DependencyTable.configValues.items():
		sphinx.add_config_value(f"{CONFIG_PREFIX}_{configName}", default, rebuild, types)

	for configName, (default, rebuild, types) in Abbreviations.configValues.items():
		sphinx.add_config_value(f"{ABBREVIATION_PREFIX}_{configName}", default, rebuild, types)

	sphinx.connect("config-inited", extendProlog)
	# after the configuration values above are registered, and before any document is read - a requirements file
	# that doesn't exist should end the build here rather than in the middle of a page
	sphinx.connect("config-inited", prepareEntrypoints)
	sphinx.connect("build-finished", reportBuildTime)
	sphinx.connect("builder-inited", installStylesheet)

	# The extension's version is the package's, so a second number to keep in step would only ever disagree.
	return {"version": __version__, "parallel_read_safe": True, "parallel_write_safe": True}
