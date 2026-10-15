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
Directives rendering the documentation coverage of a Python package as a table: per package and module.

Unlike the other reports, there is no report file: the package's source directory is analyzed with
`docstr_coverage <https://github.com/HunterMcGushion/docstr_coverage>`__ (via :mod:`pyEDAA.Reports`) once per build,
when the builder is initialized. The packages are declared in :file:`conf.py` under ``pyTooling_DocCoverage_Packages``,
each with an identifier a directive names in its ``:reportid:`` option. An entry with the key ``pages`` gets a page
per package and module, generated below that document name (see :mod:`pyTooling.Sphinx.DocCoveragePages`):

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

.. seealso::

   :ref:`DIR/DocCoverage`
      |rarr| The directives' options and configuration, with examples.
   :mod:`pyTooling.Sphinx.DocCoveragePages`
      |rarr| The pages per package and module, and the role ``:doccov:``.
"""
from __future__                                    import annotations

from pathlib                                       import Path
from tokenize                                      import TokenError
from typing                                        import TYPE_CHECKING, Any, ClassVar, Generator, Mapping
from typing                                        import Optional as Nullable, TypedDict, Union

from docutils                                      import nodes
from sphinx.application                            import Sphinx
from sphinx.config                                 import Config
from sphinx.util.logging                           import getLogger

from pyTooling.Common                              import getFullyQualifiedName
from pyTooling.Decorators                          import export

from pyTooling.Sphinx                              import INDENTATION, BaseDirective, LegendStyle, ReportExtensionError
from pyTooling.Sphinx                              import ReportsPackageMissingError, SphinxExtensionError, strip
from pyTooling.Sphinx                              import stripAndNormalize
from pyTooling.Sphinx.Pages                        import ReportPages

if TYPE_CHECKING:  # pragma: no cover
	# pyEDAA.Reports is an optional dependency (extra 'reports'), imported where the coverage is computed.
	from docstr_coverage                             import ResultCollection
	from pyEDAA.Reports.DocumentationCoverage.Python import AggregatedCoverage, PackageCoverage


__all__ = ["CONFIG_PREFIX"]

#: Prefix every configuration value of the documentation coverage directives carries in :file:`conf.py`.
CONFIG_PREFIX = "pyTooling_DocCoverage"


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
	_reports:                  ClassVar[dict[str, PackageCoverage]] = {}       #: Packages analyzed, by report ID.
	_results:                  ClassVar[dict[str, ResultCollection]] = {}      #: docstr_coverage's results, by report ID.
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
		it: a :exc:`ReportExtensionError` - e.g. pyEDAA.Reports isn't installed, or its analysis failed -, an
		:exc:`OSError` reading a source file, a :exc:`SyntaxError` or :exc:`tokenize.TokenError` parsing one, or a
		:exc:`UnicodeDecodeError` decoding one. Any other exception is a bug, and ends the build.

		:param sphinxApplication: Sphinx application instance.
		"""
		getLogger(__name__).info("[REPORT] Analyzing documentation coverage ...")

		cls._reports =        {}
		cls._results =        {}
		cls._analysisErrors = {}
		for reportID, packageConfiguration in cls._packageConfigurations.items():
			try:
				cls._reports[reportID], cls._results[reportID] = cls._AnalyzePackage(packageConfiguration)
			except (ReportExtensionError, OSError, SyntaxError, TokenError, UnicodeDecodeError) as ex:
				cls._analysisErrors[reportID] = ex

	@classmethod
	def GetReport(cls, reportID: str) -> PackageCoverage:
		"""
		Return a package analyzed by :meth:`AnalyzePackages`.

		:param reportID:              Identifier of the package.
		:returns:                     The package's coverage, aggregated.
		:raises ReportExtensionError: If the package wasn't analyzed, chained to the exception analyzing it raised.
		"""
		try:
			return cls._reports[reportID]
		except KeyError:
			cause = cls._analysisErrors.get(reportID, None)
			raise ReportExtensionError(f"Documentation coverage of '{reportID}' wasn't analyzed.") from cause

	@staticmethod
	def _AnalyzePackage(packageConfiguration: PackageConfiguration) -> tuple[PackageCoverage, ResultCollection]:
		"""
		Analyze a package's source directory with docstr_coverage, and convert the result to pyEDAA.Reports' model.

		:param packageConfiguration:        The package's configuration.
		:returns:                           The package's coverage, aggregated, and docstr_coverage's results per
		                                    expected doc-string, which a module's listing marks.
		:raises ReportsPackageMissingError: If pyEDAA.Reports or docstr_coverage isn't installed.
		:raises ReportExtensionError:       If pyEDAA.Reports' analysis fails, e.g. the directory doesn't exist.
		:raises OSError:                    If a source file can't be read.
		:raises SyntaxError:                If a source file isn't valid Python.
		:raises tokenize.TokenError:        If a source file ends inside a statement or string.
		:raises UnicodeDecodeError:         If a source file isn't UTF-8.
		"""
		try:
			from pyEDAA.Reports.DocumentationCoverage        import DocCoverageError
			from pyEDAA.Reports.DocumentationCoverage.Python import DocStrCoverage as DocStrCovAnalyzer
		except ImportError as cause:
			raise ReportsPackageMissingError(
				"Analyzing the documentation coverage", "'pyEDAA.Reports' and 'docstr_coverage'"
			) from cause

		try:
			docStrCov = DocStrCovAnalyzer(packageConfiguration["name"], packageConfiguration["directory"])
			results = docStrCov.Analyze()
			coverage = docStrCov.Convert()
		except DocCoverageError as ex:
			raise ReportExtensionError(f"Package '{packageConfiguration['name']}' can't be analyzed.") from ex

		coverage.Aggregate()

		return coverage, results

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

			if 100 not in coverageLevelDefinition:
				raise ReportExtensionError(f"{configurationName}[100]: Configuration is missing.")
			elif "error" not in coverageLevelDefinition:
				raise ReportExtensionError(f"{configurationName}[error]: Configuration is missing.")

			cls._coverageLevelDefinitions[key] = {}

			for level, levelConfig in coverageLevelDefinition.items():
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

				cls._coverageLevelDefinitions[key][level] = {
					"class": cssClass,
					"desc": description
				}

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
		:raises ReportExtensionError: If ``levels`` is a dictionary without level ``100`` or level ``error``.
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
				if 100 not in levels:
					raise ReportExtensionError(f"{configurationName}.levels[100]: Configuration is missing.")
				elif "error" not in levels:
					raise ReportExtensionError(f"{configurationName}.levels[error]: Configuration is missing.")

				levelDefinition = {}
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

	_packageName: str              #: Name of the Python package.
	_directory:   Path             #: The package's source directory.
	_failBelow:   float            #: Coverage below which the package fails.
	_coverage:    PackageCoverage  #: The package's coverage, as analyzed.

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

		self._RenderLevel(tableBody, self._coverage)

		# Add a summary row
		tableBody += nodes.row(
			"",
			nodes.entry("", nodes.Text(f"Overall ({self._coverage.FileCount} files):")),
			nodes.entry("", nodes.Text(f"{self._coverage.AggregatedExpected}")),
			nodes.entry("", nodes.Text(f"{self._coverage.AggregatedCovered}")),
			nodes.entry("", nodes.Text(f"{self._coverage.AggregatedUncovered}")),
			nodes.entry("", nodes.Text(f"{self._coverage.AggregatedCoverage:.1%}")),
			classes=[
				"report-summary",
				self._ConvertToColor(self._coverage.AggregatedCoverage, "class")
			]
		)

		return tableGroup.parent

	def _SortedValues(self, d: Mapping[str, AggregatedCoverage]) -> Generator[AggregatedCoverage, None, None]:
		"""
		Yield the values of a mapping, sorted by key.

		:param d: The mapping, e.g. a package's modules by name.
		:returns: A generator of the values, sorted by their keys.
		"""
		for key in sorted(d.keys()):
			yield d[key]

	def _RenderLevel(self, tableBody: nodes.tbody, packageCoverage: PackageCoverage, level: int = 0) -> None:
		"""
		Add a row for a package, then - recursively - rows for its sub-packages and modules.

		The hierarchy is shown by indentation, a package by 📦 and a module by ⚙️.

		:param tableBody:       The table body the rows are added to.
		:param packageCoverage: The package.
		:param level:           Optional, the package's depth in the hierarchy. Default: ``0``.
		"""
		tableBody += nodes.row(
			"",
			nodes.entry("", self._NameCell(packageCoverage, f"{INDENTATION * level}📦")),
			nodes.entry("", nodes.Text(f"{packageCoverage.Expected}")),
			nodes.entry("", nodes.Text(f"{packageCoverage.Covered}")),
			nodes.entry("", nodes.Text(f"{packageCoverage.Uncovered}")),
			nodes.entry("", nodes.Text(f"{packageCoverage.Coverage:.1%}")),
			classes=[
				"report-package",
				self._ConvertToColor(packageCoverage.Coverage, "class")
			],
		)

		for package in self._SortedValues(packageCoverage._packages):
			self._RenderLevel(tableBody, package, level + 1)

		for module in self._SortedValues(packageCoverage._modules):
			tableBody += nodes.row(
				"",
				nodes.entry("", self._NameCell(module, f"{INDENTATION * (level + 1)}{INDENTATION}⚙️")),
				nodes.entry("", nodes.Text(f"{module.Expected}")),
				nodes.entry("", nodes.Text(f"{module.Covered}")),
				nodes.entry("", nodes.Text(f"{module.Uncovered}")),
				nodes.entry("", nodes.Text(f"{module.Coverage :.1%}")),
				classes=[
					"report-module",
					self._ConvertToColor(module.Coverage, "class")
				],
			)


	def _NameCell(self, unit: AggregatedCoverage, prefix: str) -> nodes.Node:
		"""
		Create the content of the cell naming a package or module, linked to its page if the package has pages.

		:param unit:   The package or module.
		:param prefix: The indentation and the icon written before the name.
		:returns:      The cell's content.
		"""
		from pyTooling.Sphinx.DocCoveragePages import DocCoverageReportPages

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
	The ``report:doc-coverage`` directive: a table of a package's documentation coverage, analyzed by docstr_coverage.
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
			self._coverage = self.GetReport(self._reportID)
		except ReportExtensionError as ex:
			cause = ex if ex.__cause__ is None else ex.__cause__
			message = f"Caught {cause.__class__.__name__} when analyzing package '{self._packageName}'."
			return self._internalError(container, __name__, message, cause)

		container += self._GenerateCoverageTable()

		from pyTooling.Sphinx.DocCoveragePages import DocCoverageReportPages

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
