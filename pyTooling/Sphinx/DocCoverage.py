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
Directives rendering the documentation coverage of a Python package as a table: per package and module; and a page per
package and module.

Unlike the other reports, there is no report file: the package's source directory is analyzed by the Python reader
of :mod:`pyEDAA.Reports` (:class:`~pyEDAA.Reports.DocumentationCoverage.Python.Analyzer`) once per build, when the
builder is initialized. The packages are declared in :file:`conf.py` under ``pyTooling_DocCoverage_Packages``,
each with an identifier a directive names in its ``:reportid:`` option:

.. code-block:: Python

   # doc/conf.py
   pyTooling_DocCoverage_Packages = {
     "src": {
       "name":       "myPackage",
       "directory":  "../myPackage",
       "pages":      "doccoverage/src",
       "fail_below": 80,
       "levels":     "default"
     }
   }

The coverage levels - limits, descriptions and CSS classes - are declared under ``pyTooling_DocCoverage_Levels``;
:attr:`DocCoverageBase.defaultCoverageDefinitions` holds the ``default`` palette.

A package declared with the key ``pages`` gets a document per package and per module (:class:`DocCoverageReportPages`),
named below that key's document name by its dotted name, e.g. ``<pages>/myPackage/Units/Length``:

* A package's page shows its counters, tables of its sub-packages and modules, each linked to its page, and the
  condensed listing of its ``__init__.py``.
* A module's page shows its counters and its condensed listing (see
  :class:`~pyTooling.Sphinx.CondensedSource.CondensedSource`): the source condensed to what is documented, syntax
  highlighted with the Pygments lexer for Python, each line marked by its documentation state.

The states are those of the items of pyEDAA.Reports' model - the analysis the counters are computed from:
``documented``, ``undocumented``, ``ignored`` or ``excluded``, for a class, a function, a field and a variable.

The pages are built by the machinery of :class:`~pyTooling.Sphinx.Pages.ReportPages`, so they are in the navigation
below the directive ``report:doc-coverage``. Every package and module with a page is an object of domain ``report``,
referred to by the role ``:doccov:`` by its dotted name - e.g. ``:doccov:`myPackage.Units.Length``` - or a suffix of
it.

.. seealso::

   :ref:`DIR/DocCoverage`
      |rarr| The directives' options and configuration, with examples.
   :ref:`DIR/DocCoverage/Pages`
      |rarr| The pages per package and module, and the role ``:doccov:``.
   :mod:`pyTooling.Sphinx.Pages`
      |rarr| The pages of a report: document names, registration, generation and navigation.
   :mod:`pyTooling.Sphinx.CondensedSource`
      |rarr| The condensed listing of a module's source.
"""
from __future__                                    import annotations

from pathlib                                       import Path
from tokenize                                      import open as tokenize_open
from typing                                        import TYPE_CHECKING, Any, ClassVar, Iterable, Optional as Nullable
from typing                                        import TypedDict, Union

from docutils                                      import nodes
from sphinx.application                            import Sphinx
from sphinx.config                                 import Config
from sphinx.util.logging                           import getLogger

from pyTooling.Common                              import getFullyQualifiedName
from pyTooling.Decorators                          import export
from pyTooling.Warning                             import WarningCollector

from pyTooling.Sphinx                              import INDENTATION, BaseDirective, LegendStyle, ReportExtensionError
from pyTooling.Sphinx                              import ReportsPackageMissingError, SphinxExtensionError, strip
from pyTooling.Sphinx                              import stripAndNormalize
from pyTooling.Sphinx.CodeCoveragePages            import tokenizeSource
from pyTooling.Sphinx.CondensedSource              import CondensedSource, documentationState
from pyTooling.Sphinx.Node                         import DOCUMENTATION_STATES, DocCoverageListing
from pyTooling.Sphinx.Pages                        import ReportPages

if TYPE_CHECKING:  # pragma: no cover
	# pyEDAA.Reports is an optional dependency (extra 'reports'), imported where the coverage is computed.
	from pyEDAA.Reports.DocumentationCoverage        import CoverageCounters, Directory, DocumentationReport, Item


__all__ = ["CONFIG_PREFIX"]

#: Prefix every configuration value of the documentation coverage directives carries in :file:`conf.py`.
CONFIG_PREFIX = "pyTooling_DocCoverage"


@export
def subPackagesAndModules(package: Item) -> tuple[list[Item], list[Item]]:
	"""
	Return the sub-packages and the modules of a package, each sorted by name.

	:param package: The package's item.
	:returns:       The sub-packages' and the modules' items.
	"""
	from pyEDAA.Reports.DocumentationCoverage import ItemKind

	packages = sorted((item for item in package.Items if item.Kind is ItemKind.Package), key=lambda item: item.Name)
	modules =  sorted((item for item in package.Items if item.Kind is ItemKind.Module), key=lambda item: item.Name)

	return packages, modules


@export
def fileCounters(unit: Item) -> CoverageCounters:
	"""
	Return the counters of the items declared in a package's ``__init__.py`` or in a module's file.

	:param unit: The package's or module's item.
	:returns:    The file's counters; zero items for a namespace package, which has no ``__init__.py``.
	"""
	from pyEDAA.Reports.DocumentationCoverage import CoverageCounters

	return CoverageCounters() if unit.File is None else unit.File.Counters


@export
def isUnreadable(unit: Item) -> bool:
	"""
	Check if a package's ``__init__.py`` or a module's file couldn't be read or parsed.

	The Python reader excludes such a file's item, without a documentation state.

	:param unit: The package's or module's item.
	:returns:    ``True``, if the file couldn't be read or parsed.
	"""
	from pyEDAA.Reports.DocumentationCoverage import CoverageState

	return unit.File is not None and unit.Status == CoverageState.Excluded


@export
def coverageCell(
	unit: Nullable[Item],
	coverage: float,
	levels: dict[Union[int, str], dict[str, str]]
) -> tuple[str, str]:
	"""
	Return the text of a row's coverage cell and the CSS class of the row's coverage level.

	A package's or module's file, which couldn't be read or parsed, has the text ``can't be read`` and the level
	``error``.

	:param unit:     The package's or module's item, whose row it is; ``None`` for a summary row.
	:param coverage: The row's coverage, in range 0.0..1.0.
	:param levels:   The coverage levels.
	:returns:        The cell's text and the level's CSS class.
	"""
	if unit is not None and isUnreadable(unit):
		return "can't be read", DocCoverageBase.LevelOf(levels, -1.0, "class")

	return f"{coverage:.1%}", DocCoverageBase.LevelOf(levels, coverage, "class")


@export
class PackageConfiguration(TypedDict):
	"""An entry of ``pyTooling_DocCoverage_Packages``, after :meth:`DocCoverageBase.CheckConfiguration` read it."""

	name:      str                                                #: Name of the Python package.
	directory: Path                                               #: The package's source directory.
	pages:     Nullable[str]                                      #: Document name the pages are generated below.
	failBelow: float                                              #: Coverage below which the package fails.
	levels:    Union[str, dict[Union[int, str], dict[str, str]]]  #: Coverage levels, or the name of a palette.


@export
class DocCoverageBase(BaseDirective):
	"""
	Base-class of the documentation coverage directives: the shared options, the configuration and the coverage levels.

	The configuration is checked and the packages are analyzed once per build - by :meth:`CheckConfiguration` and
	:meth:`AnalyzePackages` -, into class variables every directive reads.
	"""

	option_spec: dict[str, Any] = {  # type: ignore[misc]
		"class":    strip,
		"reportid": stripAndNormalize,
	}  #: Mapping of option names to validator functions.

	defaultCoverageDefinitions: ClassVar[dict[str, dict[Union[int, str], dict[str, str]]]] = {
		"default": {
			10:      {"class": "report-cov-below10",  "desc": "almost undocumented"},
			20:      {"class": "report-cov-below20",  "desc": "almost undocumented"},
			30:      {"class": "report-cov-below30",  "desc": "almost undocumented"},
			40:      {"class": "report-cov-below40",  "desc": "poorly documented"},
			50:      {"class": "report-cov-below50",  "desc": "poorly documented"},
			60:      {"class": "report-cov-below60",  "desc": "roughly documented"},
			70:      {"class": "report-cov-below70",  "desc": "roughly documented"},
			80:      {"class": "report-cov-below80",  "desc": "roughly documented"},
			85:      {"class": "report-cov-below85",  "desc": "well documented"},
			90:      {"class": "report-cov-below90",  "desc": "well documented"},
			95:      {"class": "report-cov-below95",  "desc": "well documented"},
			100:     {"class": "report-cov-below100", "desc": "excellent documented"},
			"error": {"class": "report-cov-error",    "desc": "internal error"},
		}
	}  #: Predefined palettes of coverage levels, by name: a limit in percent or ``error``, to a CSS class and text.

	configValues: ClassVar[dict[str, tuple[Any, str, Any]]] = {
		"Packages": ({},                         "env", dict),
		"Levels":   (defaultCoverageDefinitions, "env", dict),
	}  #: Values added to :file:`conf.py`, as ``name: (default, rebuild, types)``, prefixed by :data:`CONFIG_PREFIX`.

	_coverageLevelDefinitions: ClassVar[dict[str, dict[Union[int, str], dict[str, str]]]] = {}  #: Palettes, by name.
	_packageConfigurations:    ClassVar[dict[str, PackageConfiguration]] = {}  #: Package configurations, by report ID.
	_reports:                  ClassVar[dict[str, DocumentationReport]] = {}   #: Packages analyzed, by report ID.
	_analysisErrors:           ClassVar[dict[str, Exception]] = {}             #: Why a package wasn't analyzed, by ID.

	_cssClasses: list[str]                              #: Additional CSS classes of the table.
	_reportID:   str                                    #: Identifier of the package in the configuration.
	_levels:     dict[Union[int, str], dict[str, str]]  #: The coverage levels of the package.

	def _CheckOptions(self) -> None:
		"""
		Parse all directive options or use default values.

		:raises SphinxExtensionError: If option ``:class:`` isn't a list of CSS class names.
		:raises SphinxExtensionError: If option ``:reportid:`` is missing.
		"""
		cssClasses = self._ParseStringOption("class", "", r"(\w+)?( +\w+)*")

		self._reportID = self._ParseStringOption("reportid")
		self._cssClasses = [] if cssClasses == "" else cssClasses.split(" ")

	@classmethod
	def CheckConfiguration(cls, sphinxApplication: Sphinx, sphinxConfiguration: Config) -> None:
		"""
		Check the configuration values and load the coverage levels and package configurations.

		:param sphinxApplication:   Sphinx application instance.
		:param sphinxConfiguration: Sphinx configuration instance.
		"""
		cls._CheckLevelsConfiguration(sphinxConfiguration)
		cls._CheckPackagesConfiguration(sphinxConfiguration)

	@classmethod
	def AnalyzePackages(cls, sphinxApplication: Sphinx) -> None:
		"""
		Analyze every configured package, once per build.

		A package that can't be analyzed keeps the exception, which a directive or a package's pages show when they need
		it: a :exc:`ReportExtensionError`, e.g. pyEDAA.Reports isn't installed, or the package's directory doesn't exist.
		Any other exception is a bug, and ends the build.

		:param sphinxApplication: Sphinx application instance.
		"""
		getLogger(__name__).info("[REPORT] Analyzing documentation coverage ...")

		cls._reports =        {}
		cls._analysisErrors = {}
		for reportID, packageConfiguration in cls._packageConfigurations.items():
			try:
				cls._reports[reportID] = cls._AnalyzePackage(packageConfiguration)
			except ReportExtensionError as ex:
				cls._analysisErrors[reportID] = ex

	@classmethod
	def GetReport(cls, reportID: str) -> DocumentationReport:
		"""
		Return a package analyzed by :meth:`AnalyzePackages`.

		:param reportID:              Identifier of the package.
		:returns:                     The package's report, aggregated; its top-level item is the package.
		:raises ReportExtensionError: If the package wasn't analyzed, chained to the exception analyzing it raised.
		"""
		try:
			return cls._reports[reportID]
		except KeyError:
			cause = cls._analysisErrors.get(reportID, None)
			raise ReportExtensionError(f"Documentation coverage of '{reportID}' wasn't analyzed.") from cause

	@staticmethod
	def _AnalyzePackage(packageConfiguration: PackageConfiguration) -> DocumentationReport:
		"""
		Analyze a package's source directory with pyEDAA.Reports' Python reader.

		A source file, which can't be read or parsed, is logged as a warning, and its module is excluded from the
		analysis.

		:param packageConfiguration:        The package's configuration.
		:returns:                           The package's report, aggregated; its top-level item is the package.
		:raises ReportsPackageMissingError: If pyEDAA.Reports isn't installed.
		:raises ReportExtensionError:       If pyEDAA.Reports' analysis fails, e.g. the directory doesn't exist.
		"""
		try:
			from pyEDAA.Reports.DocumentationCoverage        import DocCoverageError
			from pyEDAA.Reports.DocumentationCoverage.Python import Analyzer
		except ImportError as cause:
			raise ReportsPackageMissingError("Analyzing the documentation coverage", "'pyEDAA.Reports'") from cause

		packageName = packageConfiguration["name"]
		try:
			with WarningCollector() as warnings:
				report = Analyzer(packageName, packageConfiguration["directory"]).Analyze()
		except DocCoverageError as ex:
			raise ReportExtensionError(f"Package '{packageName}' can't be analyzed.") from ex

		for warning in warnings:
			message = f"Caught {warning.__class__.__name__} when analyzing package '{packageName}'.\n  {warning}"
			if (cause := warning.__cause__) is not None:
				message += f"\n  {cause.__class__.__name__}: {cause}"

			getLogger(__name__).warning(message)

		getLogger(__name__).verbose(
			f"[REPORT] Package '{packageName}': {report.FileCount} files analyzed in "
			f"{report.AnalysisDuration.total_seconds():.3f} s."
		)

		return report

	@classmethod
	def _CheckLevelsConfiguration(cls, sphinxConfiguration: Config) -> None:
		"""
		Check and load the palettes of coverage levels from ``pyTooling_DocCoverage_Levels``.

		:param sphinxConfiguration:   Sphinx configuration instance.
		:raises ReportExtensionError: If the configuration value isn't registered.
		:raises ReportExtensionError: If a palette has no level ``100`` or no level ``error``.
		:raises ReportExtensionError: If a level is a keyword other than ``error``.
		:raises ReportExtensionError: If a level is out of range 0..100.
		:raises ReportExtensionError: If a level is neither a keyword nor an integer.
		:raises ReportExtensionError: If a level has no CSS class or no description.
		"""
		variableName = f"{CONFIG_PREFIX}_Levels"

		try:
			coverageLevelDefinitions: dict[str, dict[Union[int, str], dict[str, str]]] = sphinxConfiguration[variableName]
		except (KeyError, AttributeError) as ex:
			raise ReportExtensionError(f"Configuration option '{variableName}' is not configured.") from ex

		if "default" not in coverageLevelDefinitions:
			cls._coverageLevelDefinitions["default"] = cls.defaultCoverageDefinitions["default"]

		for key, coverageLevelDefinition in coverageLevelDefinitions.items():
			configurationName = f"conf.py: {variableName}:[{key}]"
			cls._coverageLevelDefinitions[key] = cls._CheckLevels(configurationName, coverageLevelDefinition)

	@staticmethod
	def _CheckLevels(
		configurationName: str,
		levels: dict[Union[int, str], dict[str, str]]
	) -> dict[Union[int, str], dict[str, str]]:
		"""
		Check coverage levels and return the CSS class and description of each level.

		:param configurationName:     The levels' name in error messages.
		:param levels:                The coverage levels: a limit in percent or ``error``, to a CSS class and text.
		:returns:                     The checked coverage levels.
		:raises ReportExtensionError: If there is no level ``100`` or no level ``error``.
		:raises ReportExtensionError: If a level is a keyword other than ``error``.
		:raises ReportExtensionError: If a level is out of range 0..100.
		:raises ReportExtensionError: If a level is neither a keyword nor an integer.
		:raises ReportExtensionError: If a level has no CSS class or no description.
		"""
		if 100 not in levels:
			raise ReportExtensionError(f"{configurationName}[100]: Configuration is missing.")
		elif "error" not in levels:
			raise ReportExtensionError(f"{configurationName}[error]: Configuration is missing.")

		levelDefinition: dict[Union[int, str], dict[str, str]] = {}
		for level, levelConfig in levels.items():
			try:
				if isinstance(level, str):
					if level != "error":
						raise ReportExtensionError(f"{configurationName}[{level}]: Level is a keyword, but not 'error'.")
				elif not (0.0 <= int(level) <= 100.0):
					raise ReportExtensionError(f"{configurationName}[{level}]: Level is out of range 0..100.")
			except ValueError as ex:
				raise ReportExtensionError(
					f"{configurationName}[{level}]: Level is not a keyword or an integer in range 0..100."
				) from ex

			try:
				cssClass = levelConfig["class"]
			except KeyError as ex:
				raise ReportExtensionError(f"{configurationName}[{level}].class: CSS class is missing.") from ex

			try:
				description = levelConfig["desc"]
			except KeyError as ex:
				raise ReportExtensionError(f"{configurationName}[{level}].desc: Description is missing.") from ex

			levelDefinition[level] = {
				"class": cssClass,
				"desc": description
			}

		return levelDefinition

	@classmethod
	def _CheckPackagesConfiguration(cls, sphinxConfiguration: Config) -> None:
		"""
		Check and load the package configurations from ``pyTooling_DocCoverage_Packages``.

		:param sphinxConfiguration:   Sphinx configuration instance.
		:raises ReportExtensionError: If the configuration value isn't registered.
		:raises ReportExtensionError: If a package configuration has no ``name``.
		:raises ReportExtensionError: If a package configuration has no ``directory``.
		:raises ReportExtensionError: If the ``directory`` doesn't exist.
		:raises ReportExtensionError: If ``pages`` isn't a string.
		:raises ReportExtensionError: If ``pages`` isn't a relative document name. |br|
		                              Use a name like 'doccoverage/src', separated by '/', without '.' or '..'.
		:raises ReportExtensionError: If a package configuration has no ``fail_below``.
		:raises ReportExtensionError: If ``fail_below`` isn't an integer, or is out of range.
		:raises ReportExtensionError: If a package configuration has no ``levels``.
		:raises ReportExtensionError: If ``levels`` names a palette that isn't defined.
		:raises ReportExtensionError: If ``levels`` is a dictionary with a missing or wrong level, CSS class or description.
		:raises ReportExtensionError: If ``levels`` is neither a palette's name nor a dictionary.
		"""
		variableName = f"{CONFIG_PREFIX}_Packages"
		cls._packageConfigurations = {}

		try:
			allPackages: dict[str, PackageConfiguration] = sphinxConfiguration[variableName]
		except (KeyError, AttributeError) as ex:
			raise ReportExtensionError(f"Configuration option '{variableName}' is not configured.") from ex

		for reportID, packageConfiguration in allPackages.items():
			configurationName = f"conf.py: {variableName}:[{reportID}]"

			try:
				packageName = packageConfiguration["name"]
			except KeyError as ex:
				raise ReportExtensionError(f"{configurationName}.name: Configuration is missing.") from ex

			try:
				directory = Path(packageConfiguration["directory"])
			except KeyError as ex:
				raise ReportExtensionError(f"{configurationName}.directory: Configuration is missing.") from ex

			if not directory.exists():
				raise ReportExtensionError(
					f"{configurationName}.directory: Directory '{directory}' doesn't exist."
				) from FileNotFoundError(directory)

			if (pages := packageConfiguration.get("pages", None)) is not None:
				pages = ReportPages.CheckPagesConfiguration(configurationName, pages)

			try:
				failBelow = int(packageConfiguration["fail_below"]) / 100
			except KeyError as ex:
				raise ReportExtensionError(f"{configurationName}.fail_below: Configuration is missing.") from ex
			except ValueError as ex:
				raise ReportExtensionError(
					f"{configurationName}.fail_below: '{packageConfiguration['fail_below']}' is not an integer in range 0..100."
				) from ex

			if not (0.0 <= failBelow <= 100.0):
				raise ReportExtensionError(f"{configurationName}.fail_below: Is out of range 0..100.")

			try:
				levels = packageConfiguration["levels"]
			except KeyError as ex:
				raise ReportExtensionError(f"{configurationName}.levels: Configuration is missing.") from ex

			if isinstance(levels, str):
				try:
					levelDefinition = cls._coverageLevelDefinitions[levels]
				except KeyError as ex:
					raise ReportExtensionError(
						f"{configurationName}.levels: Referenced coverage levels '{levels}' are not defined in conf.py "
						f"variable '{variableName}'."
					) from ex
			elif isinstance(levels, dict):
				levelDefinition = cls._CheckLevels(f"{configurationName}.levels", levels)
			else:
				ex = ReportExtensionError(f"{configurationName}.levels: Is neither a palette's name nor a dictionary.")
				ex.add_note(f"Got type '{getFullyQualifiedName(levels)}'.")
				raise ex

			cls._packageConfigurations[reportID] = {
				"name":      packageName,
				"directory": directory,
				"pages":     pages,
				"failBelow": failBelow,
				"levels":    levelDefinition
			}

	@staticmethod
	def LevelOf(levels: dict[Union[int, str], dict[str, str]], coverage: float, configKey: str) -> str:
		"""
		Look up the coverage level a coverage falls into, and return one of its fields.

		:param levels:    The coverage levels.
		:param coverage:  The coverage, in range 0.0..1.0; a negative value selects level ``error``.
		:param configKey: The field to return: ``class`` or ``desc``.
		:returns:         The field's value of the first level whose limit is above the coverage.
		"""
		if coverage < 0.0:
			return levels["error"][configKey]

		for levelLimit, levelConfig in levels.items():
			if isinstance(levelLimit, int) and (coverage * 100) < levelLimit:
				return levelConfig[configKey]

		return levels[100][configKey]

	def _ConvertToColor(self, currentLevel: float, configKey: str) -> str:
		"""
		Look up the coverage level a coverage falls into, in the package's levels, and return one of its fields.

		:param currentLevel: The coverage, in range 0.0..1.0; a negative value selects level ``error``.
		:param configKey:    The field to return: ``class`` or ``desc``.
		:returns:            The field's value of the first level whose limit is above the coverage.
		"""
		return self.LevelOf(self._levels, currentLevel, configKey)


@export
class DocCoverage(DocCoverageBase):
	"""
	Base-class of the ``report:doc-coverage`` directive: the table, without an analyzer.

	A package with pages links every package and module to its page.
	"""

	directiveName: str = "doc-coverage"  #: Name the directive is invoked by.

	has_content =        False                                    #: A boolean; ``True`` if content is allowed.
	required_arguments = 0                                        #: Number of required directive arguments.
	optional_arguments = DocCoverageBase.optional_arguments + 0  #: Number of optional arguments.

	_packageName: str                  #: Name of the Python package.
	_directory:   Path                 #: The package's source directory.
	_failBelow:   float                #: Coverage below which the package fails.
	_report:      DocumentationReport  #: The package's report, as analyzed.

	def _CheckOptions(self) -> None:
		"""
		Parse all directive options or use default values.

		:raises KeyError: If ``pyTooling_DocCoverage_Packages`` has no entry for the report ID.
		"""
		super()._CheckOptions()

		packageConfiguration = self._packageConfigurations[self._reportID]
		self._packageName = packageConfiguration["name"]
		self._directory =   packageConfiguration["directory"]
		self._failBelow =   packageConfiguration["failBelow"]
		self._levels =      packageConfiguration["levels"]

	def _GenerateCoverageTable(self) -> nodes.table:
		"""
		Build the table: a row per package and module, and a summary row.

		:returns: The table.
		"""
		cssClasses = ["report-doccov-table", f"report-doccov-{self._reportID}"]
		cssClasses.extend(self._cssClasses)

		# Create a table and table header with 5 columns
		tableGroup = self._CreateSingleRowTableHeader(
			identifier=self._reportID,
			columns=[
				("Filename", 5),
				("Total", 1),
				("Covered", 1),
				("Missing", 1),
				("Coverage in %", 1)
			],
			classes=cssClasses
		)
		tableBody = nodes.tbody()
		tableGroup += tableBody

		self._RenderLevel(tableBody, self._report.Items[0])

		# Add a summary row
		tableBody += nodes.row(
			"",
			nodes.entry("", nodes.Text(f"Overall ({self._report.FileCount} files):")),
			nodes.entry("", nodes.Text(f"{self._report.Counters.Expected}")),
			nodes.entry("", nodes.Text(f"{self._report.Counters.Covered}")),
			nodes.entry("", nodes.Text(f"{self._report.Counters.Uncovered}")),
			nodes.entry("", nodes.Text(f"{self._report.Counters.Coverage:.1%}")),
			classes=[
				"report-summary",
				self._ConvertToColor(self._report.Counters.Coverage, "class")
			]
		)

		return tableGroup.parent

	def _RenderLevel(self, tableBody: nodes.tbody, package: Item, level: int = 0) -> None:
		"""
		Add a row for a package, then - recursively - rows for its sub-packages and modules.

		A package's row counts the items declared in its ``__init__.py``, a module's row those declared in the module; a
		file, which couldn't be read or parsed, has the coverage level ``error``. The hierarchy is shown by indentation, a
		package by 📦 and a module by ⚙️.

		:param tableBody: The table body the rows are added to.
		:param package:   The package's item.
		:param level:     Optional, the package's depth in the hierarchy. Default: ``0``.
		"""
		def addRow(unit: Item, prefix: str, cssClass: str) -> None:
			"""
			Nested function adding the row of a package or module.

			:param unit:     The package's or module's item.
			:param prefix:   The indentation and the icon written before the name.
			:param cssClass: The CSS class of the row's kind.
			"""
			counters = fileCounters(unit)
			coverage, levelClass = coverageCell(unit, counters.Coverage, self._levels)
			tableBody.append(nodes.row(
				"",
				nodes.entry("", self._NameCell(unit, prefix)),
				nodes.entry("", nodes.Text(f"{counters.Expected}")),
				nodes.entry("", nodes.Text(f"{counters.Covered}")),
				nodes.entry("", nodes.Text(f"{counters.Uncovered}")),
				nodes.entry("", nodes.Text(coverage)),
				classes=[cssClass, levelClass],
			))

		packages, modules = subPackagesAndModules(package)

		addRow(package, f"{INDENTATION * level}📦", "report-package")
		for subPackage in packages:
			self._RenderLevel(tableBody, subPackage, level + 1)

		for module in modules:
			addRow(module, f"{INDENTATION * (level + 1)}{INDENTATION}⚙️", "report-module")

	def _NameCell(self, unit: Item, prefix: str) -> nodes.Node:
		"""
		Create the content of the cell naming a package or module, linked to its page if the package has pages.

		:param unit:   The package's or module's item.
		:param prefix: The indentation and the icon written before the name.
		:returns:      The cell's content.
		"""
		if DocCoverageReportPages.HasPages(self._reportID):
			pages = DocCoverageReportPages.GetPages(self._reportID)
			if (entry := pages.Entry(unit)) is not None:
				# a reference has to be inside a text element; an inline keeps the cell free of a paragraph, as the
				# others are
				return nodes.inline("", "", nodes.Text(prefix), pages.CreateReference("doccov", entry, self.env.docname))

		return nodes.Text(f"{prefix}{unit.Name}")


@export
class DocStrCoverage(DocCoverage):
	"""
	The ``report:doc-coverage`` directive: a table of a package's documentation coverage.
	"""

	def run(self) -> list[nodes.Node]:
		"""
		Return the configured package's documentation coverage as a table, and - if the package has pages - a hidden
		table of contents of its page.

		:returns: A container holding the table, or the error message; then the table of contents, if the package has
		          pages.
		"""
		container = nodes.container()

		try:
			self._CheckOptions()
		except SphinxExtensionError as ex:
			message = f"Caught {ex.__class__.__name__} when checking options for directive '{self.directiveName}'."
			return self._internalError(container, __name__, message, ex)

		try:
			self._report = self.GetReport(self._reportID)
		except ReportExtensionError as ex:
			cause = ex if ex.__cause__ is None else ex.__cause__
			message = f"Caught {cause.__class__.__name__} when analyzing package '{self._packageName}'."
			return self._internalError(container, __name__, message, cause)

		container += self._GenerateCoverageTable()

		if not DocCoverageReportPages.HasPages(self._reportID):
			return [container]

		return [container, DocCoverageReportPages.GetPages(self._reportID).TableOfContents(self.env.docname)]


@export
class DocCoverageLegend(DocCoverageBase):
	"""
	The ``report:doc-coverage-legend`` directive: a table of a package's coverage levels.
	"""

	directiveName: str = "doc-coverage-legend"  #: Name the directive is invoked by.

	has_content =        False                                    #: A boolean; ``True`` if content is allowed.
	required_arguments = 0                                        #: Number of required directive arguments.
	optional_arguments = DocCoverageBase.optional_arguments + 1  #: Number of optional arguments.

	option_spec: dict[str, Any] = DocCoverageBase.option_spec | {  # type: ignore[misc]
		"style": stripAndNormalize
	}  #: Mapping of option names to validator functions.

	_style: LegendStyle  #: How the legend is laid out.

	def _CheckOptions(self) -> None:
		"""
		Parse all directive options or use default values.

		:raises SphinxExtensionError: If option ``:style:`` names no :class:`~pyTooling.Sphinx.LegendStyle`.
		:raises KeyError:             If ``pyTooling_DocCoverage_Packages`` has no entry for the report ID.
		"""
		super()._CheckOptions()

		self._style = self._ParseEnumOption("style", LegendStyle, LegendStyle.horizontal_table)

		packageConfiguration = self._packageConfigurations[self._reportID]
		self._levels = packageConfiguration["levels"]

	def _CreateHorizontalLegendTable(self, identifier: str, classes: list[str]) -> nodes.table:
		"""
		Build the legend as a table with a column per level.

		:param identifier: Identifier of the table.
		:param classes:    CSS classes of the table.
		:returns:          The table.
		"""
		columns: list[tuple[str, Union[int, None]]] = [("Documentation Coverage:", 3)]
		for level in self._levels:
			if isinstance(level, int):
				columns.append((f"≤{level} %", 2))

		tableGroup = self._CreateSingleRowTableHeader(columns, identifier=identifier, classes=classes)
		tableBody = nodes.tbody()
		tableGroup += tableBody

		legendRow = nodes.row("", classes=["report-doccov-legend-row"])
		legendRow += nodes.entry("", nodes.paragraph(text="Coverage Level:"))
		tableBody += legendRow
		for level, config in self._levels.items():
			if isinstance(level, int):
				legendRow += nodes.entry(
					"", nodes.paragraph(text=config["desc"]), classes=[self._ConvertToColor((level - 1) / 100, "class")]
				)

		return tableGroup.parent

	def _CreateVerticalLegendTable(self, identifier: str, classes: list[str]) -> nodes.table:
		"""
		Build the legend as a table with a row per level.

		:param identifier: Identifier of the table.
		:param classes:    CSS classes of the table.
		:returns:          The table.
		"""
		tableGroup = self._CreateSingleRowTableHeader([
				("Documentation Coverage", 3),
				("Coverage Level", 3)
			],
			identifier=identifier,
			classes=classes
		)

		tableBody = nodes.tbody()
		tableGroup += tableBody

		for level, config in self._levels.items():
			if isinstance(level, int):
				tableBody += nodes.row(
					"",
					nodes.entry("", nodes.Text(f"≤{level} %")),
					nodes.entry("", nodes.paragraph(text=config["desc"])),
					classes=["report-doccov-legend-row", self._ConvertToColor((level - 1) / 100, "class")]
				)

		return tableGroup.parent

	def run(self) -> list[nodes.Node]:
		"""
		Return the configured package's coverage levels as a table, in the requested style.

		:returns: A container holding the table, or the error message.
		"""
		container = nodes.container()

		try:
			self._CheckOptions()
		except SphinxExtensionError as ex:
			message = f"Caught {ex.__class__.__name__} when checking options for directive '{self.directiveName}'."
			return self._internalError(container, __name__, message, ex)

		if LegendStyle.Table in self._style:
			if LegendStyle.Horizontal in self._style:
				container += self._CreateHorizontalLegendTable(
					identifier=f"{self._reportID}-legend", classes=["report-doccov-legend"]
				)
			elif LegendStyle.Vertical in self._style:
				container += self._CreateVerticalLegendTable(
					identifier=f"{self._reportID}-legend", classes=["report-doccov-legend"]
				)
			else:
				container += nodes.paragraph(text="Unsupported legend style.")
		else:
			container += nodes.paragraph(text="Unsupported legend style.")

		return [container]


@export
class DocCoverageReportPages(ReportPages):
	"""
	The pages of one package's documentation coverage: a page per package and per module.
	"""

	_reportPages: ClassVar[dict[str, ReportPages]] = {}  #: The pages of every analyzed package with pages, by report ID.
	_separator:   ClassVar[str] = "."                    #: Separator of the names in a dotted name.

	_directory: Path                                   #: The package's source directory.
	_levels:    dict[Union[int, str], dict[str, str]]  #: The package's coverage levels, coloring the tables.

	def __init__(
		self,
		reportID: str,
		prefix: str,
		directory: Path,
		package: Item,
		levels: dict[Union[int, str], dict[str, str]]
	) -> None:
		"""
		Compute the document names and entries of a package's packages and modules.

		:param reportID:  Identifier of the package.
		:param prefix:    Document name the pages are generated below.
		:param directory: The package's source directory.
		:param package:   The package's item, the root of the pages.
		:param levels:    The package's coverage levels.
		"""
		super().__init__(reportID, prefix, directory, [("doccov", package)])

		self._directory = directory.resolve()
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
				report = DocCoverageBase.GetReport(reportID)
			except ReportExtensionError as ex:
				cause = ex if ex.__cause__ is None else ex.__cause__
				getLogger(__name__).error(
					f"Caught {ex.__class__.__name__} when generating the pages of documentation coverage '{reportID}'.\n"
					f"  {cause.__class__.__name__}: {cause}"
				)
				continue

			pages = cls(reportID, prefix, packageConfiguration["directory"], report.Items[0], packageConfiguration["levels"])
			cls._reportPages[reportID] = pages
			pages.Register(sphinxApplication.env)

	def _Name(self, entity: Item) -> str:
		"""
		Return a package's or module's name; the root package's may be dotted.

		The root package has the configured name, e.g. ``pyTooling.Sphinx``, which is one element of a path: a reference
		names it in full.

		:param entity: The package's or module's item.
		:returns:      The name.
		"""
		return entity.Name

	def _Title(self, entity: Item) -> Nullable[str]:
		"""
		Return no title, as a package or module has none.

		:param entity: The package's or module's item.
		:returns:      ``None``
		"""
		return None

	def _Children(self, roleName: str, entity: Item) -> Iterable[tuple[str, Item]]:
		"""
		Return a package's sub-packages, then its modules, each sorted by name; a module has none.

		:param roleName: The role referring to the object: ``doccov``.
		:param entity:   The package's or module's item.
		:returns:        The children as ``(role name, object)`` pairs.
		"""
		packages, modules = subPackagesAndModules(entity)

		return [("doccov", child) for child in (*packages, *modules)]

	def _Directory(self, package: Item) -> Directory:
		"""
		Return a package's directory in the report's physical hierarchy.

		:param package: The package's item.
		:returns:       The directory; the report itself for the root package.
		"""
		names: list[str] = []
		unit = package
		while unit.Parent is not unit.Root:
			names.insert(0, unit.Name)
			unit = unit.Parent

		directory = package.Root
		for name in names:
			directory = directory.Directories[Path(name)]

		return directory

	def _Source(self, entity: Item) -> Path:
		"""
		Return the source of a package's or module's page: the module's file, the package's ``__init__.py`` - or its
		directory, if it has none.

		:param entity: The package's or module's item.
		:returns:      The page's source file.
		"""
		if entity.File is not None:
			return self._directory / entity.File.Path

		return self._directory / self._Directory(entity).Path

	def _Page(self, docName: str, roleName: str, entity: Item) -> nodes.section:
		"""
		Build a package's or module's page: its summary, a package's tables of sub-packages and modules, and the
		condensed listing.

		:param docName:  Name of the page's document.
		:param roleName: The role referring to the object: ``doccov``.
		:param entity:   The package's or module's item.
		:returns:        The page's top section.
		"""
		page = nodes.section("", nodes.title(entity.Name, entity.Name), ids=["report-doccov-page"])
		page += (summarySection := self._SummarySection(docName, entity))

		children = self._ChildrenSections(page, docName, entity)
		if len(children) > 0:
			# body elements precede a section's subsections, so the hidden table of contents goes before 'Summary'
			page.insert(page.index(summarySection), self._TableOfContents(docName, children))

		if entity.File is not None:
			page += self._SourceSection(entity, self._Source(entity))

		return page

	def _SummarySection(self, docName: str, entity: Item) -> nodes.section:
		"""
		Create a page's section *Summary*: the parent package, the doc-string's state, and the counters - of the module's
		file or the package's ``__init__.py``, and a package's overall -, colored by coverage level. A file, which
		couldn't be read or parsed, has the coverage level ``error``.

		:param docName: Name of the page's document.
		:param entity:  The package's or module's item.
		:returns:       The section.
		"""
		from pyEDAA.Reports.DocumentationCoverage import ItemKind

		section = nodes.section("", nodes.title("Summary", "Summary"), ids=["summary"])
		section += (fieldList := nodes.field_list(classes=["report-doccov-fields"]))
		if entity.Parent is not entity.Root:
			self._Field(fieldList, "Package", self._Reference("doccov", entity.Parent, docName))

		if isUnreadable(entity):
			self._Field(fieldList, "Doc-string", nodes.Text("can't be read"))
		elif entity.File is not None:
			self._Field(fieldList, "Doc-string", nodes.Text(DOCUMENTATION_STATES[documentationState(entity.Status)]))

		table, tableBody = self._Table(
			[("File", 6), ("Expected", 2), ("Covered", 2), ("Uncovered", 2), ("Coverage", 2)],
			["report-doccov-table", "report-doccov-summary"]
		)
		section += table

		rows = []
		if entity.File is not None:
			rows.append((f"{entity.File.Name}", "", entity, fileCounters(entity)))

		if entity.Kind is ItemKind.Package:
			rows.append((f"Overall ({self._Directory(entity).FileCount} files)", "report-summary", None, entity.Counters))

		for name, cssClass, unit, counters in rows:
			coverage, level = coverageCell(unit, counters.Coverage, self._levels)
			tableBody += (row := nodes.row("", classes=[cssClass, level] if cssClass != "" else [level]))
			row += nodes.entry("", nodes.paragraph("", name))
			row += nodes.entry("", nodes.paragraph("", f"{counters.Expected}"))
			row += nodes.entry("", nodes.paragraph("", f"{counters.Covered}"))
			row += nodes.entry("", nodes.paragraph("", f"{counters.Uncovered}"))
			row += nodes.entry("", nodes.paragraph("", coverage))

		return section

	def _ChildrenSections(self, page: nodes.section, docName: str, package: Item) -> list[str]:
		"""
		Add a package's sections of its sub-packages and modules: a table each, every row linked to its page and colored
		by coverage level. A sub-package's row counts it with all its modules; a module has none. A package or module,
		whose file couldn't be read or parsed, has the coverage level ``error``.

		:param page:    The package's page.
		:param docName: Name of the page's document.
		:param package: The package's or module's item.
		:returns:       The document names of the listed pages.
		"""
		packages, modules = subPackagesAndModules(package)

		children: list[str] = []
		for title, column, identifier, units in (
			("Packages", "Package", "packages", packages),
			("Modules",  "Module",  "modules",  modules),
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
				coverage, level = coverageCell(unit, unit.Counters.Coverage, self._levels)
				tableBody += (row := nodes.row("", classes=[level]))
				row += nodes.entry("", nodes.paragraph("", "", self._Reference("doccov", unit, docName)))
				row += nodes.entry("", nodes.paragraph("", f"{unit.Counters.Expected}"))
				row += nodes.entry("", nodes.paragraph("", f"{unit.Counters.Covered}"))
				row += nodes.entry("", nodes.paragraph("", f"{unit.Counters.Uncovered}"))
				row += nodes.entry("", nodes.paragraph("", coverage))
				if (entry := self.Entry(unit)) is not None:
					children.append(entry.docName)

		return children

	def _SourceSection(self, entity: Item, sourceFile: Path) -> nodes.section:
		"""
		Create a page's section *Source*: the condensed listing of the module, or of the package's ``__init__.py``.

		The source file is read in its declared encoding. A source file, which the analysis couldn't read or parse, isn't
		read again; the section says so. A source file, which can't be read or parsed now, is logged as a warning, and
		the section says so.

		:param entity:     The package's or module's item, which has a file.
		:param sourceFile: The source file.
		:returns:          The section.
		"""
		section = nodes.section("", nodes.title("Source", "Source"), ids=["source"])
		path = (entity.Root.Name / entity.File.Path).as_posix()
		if isUnreadable(entity):
			section += nodes.paragraph(text=f"The source file '{path}' can't be read or parsed.")
			return section

		try:
			with tokenize_open(sourceFile) as file:
				source = file.read()

			condensedSource = CondensedSource.Parse(source, path, entity)
		except (OSError, SyntaxError, ValueError) as ex:
			getLogger(__name__).warning(
				f"Source file '{sourceFile}' of the documentation coverage can't be read or parsed: {ex}"
			)
			section += nodes.paragraph(text=f"The source file '{path}' can't be read or parsed.")
			return section

		sourceLines = source.split("\n")
		tokens = tokenizeSource(source, sourceFile.name)
		ellipsis = tokenizeSource("...\n", sourceFile.name)[0]

		lines: list[tuple[Nullable[int], str, list[tuple[str, str]]]] = []
		text: list[str] = []
		for number, state, indentation in condensedSource.Lines:
			if number is None:
				lines.append((None, "", [("", indentation), *ellipsis]))
				text.append(f"{indentation}...")
			else:
				lines.append((number, state, tokens[number - 1]))
				text.append(sourceLines[number - 1])

		plainText = "\n".join(text)
		section += DocCoverageListing(plainText, plainText, lines=lines, path=path)

		return section
