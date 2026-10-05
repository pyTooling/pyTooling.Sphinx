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
Directives rendering a code coverage report as a table: per package and module, statements and branches.

The report files are declared in :file:`conf.py` under ``pyTooling_CodeCoverage_Packages``, each with an
identifier a directive names in its ``:reportid:`` option:

.. code-block:: Python

   # doc/conf.py
   pyTooling_CodeCoverage_Packages = {
     "src": {
       "name":        "myPackage",
       "json_report": "../report/coverage/coverage.json",
       "fail_below":  80,
       "levels":      "default"
     }
   }

The coverage levels - limits, descriptions and CSS classes - are declared under ``pyTooling_CodeCoverage_Levels``;
:attr:`CodeCoverageBase.defaultCoverageDefinitions` holds the ``default`` palette.

.. seealso::

   :ref:`DIR/CodeCoverage`
      |rarr| The directives' options and configuration, with examples.
   :mod:`pyTooling.Sphinx.Report.Adapter.Coverage`
      |rarr| The adapter reading Coverage.py's JSON report.
"""
from pathlib                                        import Path
from typing                                         import Any, ClassVar, Generator, Mapping, TypedDict, Union

from docutils                                       import nodes
from docutils.parsers.rst.directives                import flag
from sphinx.application                             import Sphinx
from sphinx.config                                  import Config
from sphinx.directives.code                         import LiteralIncludeReader
from sphinx.util.docutils                           import new_document
from sphinx.util.logging                            import getLogger

from pyTooling.Common                               import getFullyQualifiedName
from pyTooling.Decorators                           import export

from pyTooling.Sphinx                               import BaseDirective, SphinxExtensionError, strip, stripAndNormalize
from pyTooling.Sphinx.Node                          import Landscape
from pyTooling.Sphinx.Report                        import INDENTATION, LegendStyle, ReportExtensionError
from pyTooling.Sphinx.Report.Adapter.Coverage       import Analyzer
from pyTooling.Sphinx.Report.DataModel.CodeCoverage import Coverage, PackageCoverage
from pyTooling.Sphinx.Report.DataModel.CodeCoverage import ModuleCoverage as ModuleCoverageData


__all__ = ["CONFIG_PREFIX"]

#: Prefix every configuration value of the code coverage directives carries in :file:`conf.py`.
CONFIG_PREFIX = "pyTooling_CodeCoverage"


@export
class PackageConfiguration(TypedDict):
	"""An entry of ``pyTooling_CodeCoverage_Packages``, after :meth:`CodeCoverageBase.CheckConfiguration` read it."""

	name:        str                                                  #: Name of the Python package.
	json_report: Path                                                 #: Coverage.py's JSON report.
	fail_below:  int                                                  #: Coverage below which the package fails.
	levels:      Union[str, dict[Union[int, str], dict[str, str]]]    #: Coverage levels, or the name of a palette.


@export
class CodeCoverageBase(BaseDirective):
	"""
	Base-class of the code coverage directives: the shared options, the configuration and the coverage levels.

	The configuration is read once per build by :meth:`CheckConfiguration`, into class variables every directive reads.
	"""

	option_spec: dict[str, Any] = {  # type: ignore[misc]
		"class":    strip,
		"reportid": stripAndNormalize
	}  #: Mapping of option names to validator functions.

	defaultCoverageDefinitions: ClassVar[dict[str, dict[Union[int, str], dict[str, str]]]] = {
		"default": {
			10:      {"class": "report-cov-below10",  "desc": "almost unused"},
			20:      {"class": "report-cov-below20",  "desc": "almost unused"},
			30:      {"class": "report-cov-below30",  "desc": "almost unused"},
			40:      {"class": "report-cov-below40",  "desc": "poorly used"},
			50:      {"class": "report-cov-below50",  "desc": "poorly used"},
			60:      {"class": "report-cov-below60",  "desc": "somehow used"},
			70:      {"class": "report-cov-below70",  "desc": "somehow used"},
			80:      {"class": "report-cov-below80",  "desc": "somehow used"},
			85:      {"class": "report-cov-below85",  "desc": "well used"},
			90:      {"class": "report-cov-below90",  "desc": "well used"},
			95:      {"class": "report-cov-below95",  "desc": "well used"},
			100:     {"class": "report-cov-below100", "desc": "excellently used"},
			"error": {"class": "report-cov-error",    "desc": "internal error"},
		}
	}  #: Predefined palettes of coverage levels, by name: a limit in percent or ``error``, to a CSS class and text.

	configValues: ClassVar[dict[str, tuple[Any, str, Any]]] = {
		"Packages": ({},                         "env", dict),
		"Levels":   (defaultCoverageDefinitions, "env", dict),
	}  #: Values added to :file:`conf.py`, as ``name: (default, rebuild, types)``, prefixed by :data:`CONFIG_PREFIX`.

	_coverageLevelDefinitions: ClassVar[dict[str, dict[Union[int, str], dict[str, str]]]] = {}  #: Palettes, by name.
	_packageConfigurations:    ClassVar[dict[str, PackageConfiguration]] = {}  #: Package configurations, by report ID.

	_cssClasses: list[str]                             #: Additional CSS classes of the table.
	_reportID:   str                                   #: Identifier of the report in the configuration.
	_levels:     dict[Union[int, str], dict[str, str]] #: The coverage levels of the report.

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
	def ReadReports(cls, sphinxApplication: Sphinx) -> None:
		"""
		Read code coverage report files.

		So far, this only logs that the reports are read; each directive reads its report when it runs.

		:param sphinxApplication: Sphinx application instance.
		"""
		getLogger(__name__).info("[REPORT] Reading code coverage reports ...")

	@classmethod
	def _CheckLevelsConfiguration(cls, sphinxConfiguration: Config) -> None:
		"""
		Check and load the palettes of coverage levels from ``pyTooling_CodeCoverage_Levels``.

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
		Check and load the package configurations from ``pyTooling_CodeCoverage_Packages``.

		:param sphinxConfiguration:   Sphinx configuration instance.
		:raises ReportExtensionError: If the configuration value isn't registered.
		:raises ReportExtensionError: If a package configuration has no ``name``.
		:raises ReportExtensionError: If a package configuration has no ``json_report``.
		:raises ReportExtensionError: If the ``json_report`` file doesn't exist.
		:raises ReportExtensionError: If a package configuration has no ``fail_below``.
		:raises ReportExtensionError: If ``fail_below`` isn't an integer, or is out of range.
		:raises ReportExtensionError: If a package configuration has no ``levels``.
		:raises ReportExtensionError: If ``levels`` names a palette that isn't defined.
		:raises ReportExtensionError: If ``levels`` is a dictionary without level ``100`` or level ``error``.
		:raises ReportExtensionError: If ``levels`` is neither a palette's name nor a dictionary.
		"""
		variableName = f"{CONFIG_PREFIX}_Packages"

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
				jsonReport = Path(packageConfiguration["json_report"])
			except KeyError as ex:
				raise ReportExtensionError(f"{configurationName}.json_report: Configuration is missing.") from ex

			if not jsonReport.exists():
				raise ReportExtensionError(
					f"{configurationName}.json_report: Coverage report file '{jsonReport}' doesn't exist."
				) from FileNotFoundError(jsonReport)

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
				"name": packageName,
				"json_report": jsonReport,
				"fail_below": failBelow,
				"levels": levelDefinition
			}

	def _ConvertToColor(self, currentLevel: float, configKey: str) -> str:
		"""
		Look up the coverage level a coverage falls into, and return one of its fields.

		:param currentLevel: The coverage, in range 0.0..1.0; a negative value selects level ``error``.
		:param configKey:    The field to return: ``class`` or ``desc``.
		:returns:            The field's value of the first level whose limit is above the coverage.
		"""
		if currentLevel < 0.0:
			return self._levels["error"][configKey]

		for levelLimit, levelConfig in self._levels.items():
			if isinstance(levelLimit, int) and (currentLevel * 100) < levelLimit:
				return levelConfig[configKey]

		return self._levels[100][configKey]


@export
class CodeCoverage(CodeCoverageBase):
	"""
	The ``report:code-coverage`` directive: a table of a package's code coverage, per package and module.
	"""

	directiveName: str = "code-coverage"  #: Name the directive is invoked by.

	has_content =        False                                     #: A boolean; ``True`` if content is allowed.
	required_arguments = 0                                         #: Number of required directive arguments.
	optional_arguments = CodeCoverageBase.optional_arguments + 1  #: Number of optional arguments.

	option_spec: dict[str, Any] = CodeCoverageBase.option_spec | {  # type: ignore[misc]
		"no-branch-coverage": flag
	}  #: Mapping of option names to validator functions.

	_noBranchCoverage: bool             #: Whether the branch coverage columns are left out.
	_packageName:      str              #: Name of the Python package.
	_jsonReport:       Path             #: Coverage.py's JSON report.
	_failBelow:        float            #: Coverage below which the package fails.
	_coverage:         PackageCoverage  #: The package's coverage, read from the report.

	def _CheckOptions(self) -> None:
		"""
		Parse all directive options or use default values.

		:raises ReportExtensionError: If ``pyTooling_CodeCoverage_Packages`` has no entry for the report ID.
		"""
		super()._CheckOptions()

		self._noBranchCoverage = "no-branch-coverage" in self.options

		try:
			packageConfiguration = self._packageConfigurations[self._reportID]
		except KeyError as ex:
			raise ReportExtensionError(f"No configuration for '{self._reportID}'") from ex

		self._packageName = packageConfiguration["name"]
		self._jsonReport =  packageConfiguration["json_report"]
		self._failBelow =   packageConfiguration["fail_below"]
		self._levels =      packageConfiguration["levels"]

	def _GenerateCoverageTable(self) -> nodes.table:
		"""
		Build the table: two header rows, a row per package and module, and a summary row.

		:returns: The table.
		"""
		cssClasses = ["report-codecov-table", f"report-codecov-{self._reportID}"]
		cssClasses.extend(self._cssClasses)

		# Create a table and table header with 10 columns
		columns = [
			("Package",   [(f"{INDENTATION}Module", 5)], None),
			("Statments", [("Total", 1), ("Excluded", 1), ("Covered", 1), ("Missing", 1), ("Coverage", 1)], None),
			("Branches" , [("Total", 1), ("Covered", 1), ("Partial", 1), ("Missing", 1), ("Coverage", 1)], None),
		]

		if self._noBranchCoverage:
			columns.pop(2)

		tableGroup = self._CreateDoubleRowTableHeader(
			identifier=self._reportID,
			columns=columns,
			classes=cssClasses
		)
		tableBody = nodes.tbody()
		tableGroup += tableBody

		self._RenderLevel(tableBody, self._coverage)

		# Add a summary row
		tableRow = nodes.row("", classes=[
			"report-summary",
			self._ConvertToColor(self._coverage.AggregatedStatementCoverage, "class")
		])
		tableBody += tableRow

		tableRow += nodes.entry("", nodes.Text(f"Overall ({self._coverage.FileCount} files):"))
		tableRow += nodes.entry("", nodes.Text(f"{self._coverage.AggregatedTotalStatements}"))
		tableRow += nodes.entry("", nodes.Text(f"{self._coverage.AggregatedExcludedStatements}"))
		tableRow += nodes.entry("", nodes.Text(f"{self._coverage.AggregatedCoveredStatements}"))
		tableRow += nodes.entry("", nodes.Text(f"{self._coverage.AggregatedMissingStatements}"))
		tableRow += nodes.entry("", nodes.Text(f"{self._coverage.AggregatedStatementCoverage:.1%}"))
		if not self._noBranchCoverage:
			tableRow += nodes.entry("", nodes.Text(f"{self._coverage.AggregatedTotalBranches}"))
			tableRow += nodes.entry("", nodes.Text(f"{self._coverage.AggregatedCoveredBranches}"))
			tableRow += nodes.entry("", nodes.Text(f"{self._coverage.AggregatedPartialBranches}"))
			tableRow += nodes.entry("", nodes.Text(f"{self._coverage.AggregatedMissingBranches}"))
			tableRow += nodes.entry("", nodes.Text(f"{self._coverage.AggregatedBranchCoverage:.1%}"))

		return tableGroup.parent

	def _SortedValues(self, d: Mapping[str, Coverage]) -> Generator[Coverage, None, None]:
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
		coverage = 1 if packageCoverage.Coverage < 0.0 else packageCoverage.Coverage
		tableRow = nodes.row("", classes=[
			"report-package",
			self._ConvertToColor(coverage, "class")
		])
		tableBody += tableRow

		tableRow += nodes.entry("", nodes.Text(f"{INDENTATION * level}📦{packageCoverage.Name}"))
		tableRow += nodes.entry("", nodes.Text(f"{packageCoverage.TotalStatements}"))
		tableRow += nodes.entry("", nodes.Text(f"{packageCoverage.ExcludedStatements}"))
		tableRow += nodes.entry("", nodes.Text(f"{packageCoverage.CoveredStatements}"))
		tableRow += nodes.entry("", nodes.Text(f"{packageCoverage.MissingStatements}"))
		tableRow += nodes.entry("", nodes.Text(f"{packageCoverage.StatementCoverage:.1%}"))
		if not self._noBranchCoverage:
			tableRow += nodes.entry("", nodes.Text(f"{packageCoverage.TotalBranches}"))
			tableRow += nodes.entry("", nodes.Text(f"{packageCoverage.CoveredBranches}"))
			tableRow += nodes.entry("", nodes.Text(f"{packageCoverage.PartialBranches}"))
			tableRow += nodes.entry("", nodes.Text(f"{packageCoverage.MissingBranches}"))
			tableRow += nodes.entry("", nodes.Text(f"{packageCoverage.BranchCoverage:.1%}"))

		for package in self._SortedValues(packageCoverage._packages):
			self._RenderLevel(tableBody, package, level + 1)

		for module in self._SortedValues(packageCoverage._modules):
			tableRow = nodes.row("", classes=[
				"report-module",
				self._ConvertToColor(module.Coverage, "class")
			])
			tableBody += tableRow

			tableRow += nodes.entry("", nodes.Text(f"{INDENTATION * (level + 1)}{INDENTATION}⚙️{module.Name}"))
			tableRow += nodes.entry("", nodes.Text(f"{module.TotalStatements}"))
			tableRow += nodes.entry("", nodes.Text(f"{module.ExcludedStatements}"))
			tableRow += nodes.entry("", nodes.Text(f"{module.CoveredStatements}"))
			tableRow += nodes.entry("", nodes.Text(f"{module.MissingStatements}"))
			tableRow += nodes.entry("", nodes.Text(f"{module.StatementCoverage:.1%}"))
			if not self._noBranchCoverage:
				tableRow += nodes.entry("", nodes.Text(f"{module.TotalBranches}"))
				tableRow += nodes.entry("", nodes.Text(f"{module.CoveredBranches}"))
				tableRow += nodes.entry("", nodes.Text(f"{module.PartialBranches}"))
				tableRow += nodes.entry("", nodes.Text(f"{module.MissingBranches}"))
				tableRow += nodes.entry("", nodes.Text(f"{module.BranchCoverage:.1%}"))

	def _CreatePages(self) -> None:
		"""
		Register a title per module, for a page per module - a start, no page is written yet.
		"""
		def handlePackage(package: PackageCoverage) -> None:
			"""
			Nested function for recursion: handle a package's sub-packages and modules.

			:param package: The package.
			"""
			for pack in package._packages.values():
				if handlePackage(pack):
					return

			for module in package._modules.values():
				if handleModule(module):
					return

		def handleModule(module: ModuleCoverageData) -> None:
			"""
			Nested function registering the title of a module's page.

			:param module: The module.
			"""
			doc = new_document("dummy")

			rootSection = nodes.section(ids=["foo"])
			doc += rootSection

			title = nodes.title(text=f"{module.Name}")
			rootSection += title
			rootSection += nodes.paragraph(text="some text")

			docname = f"coverage/{module.Name}"
			self.env.titles[docname] = title
			self.env.longtitles[docname] = title

			return

		handlePackage(self._coverage)

	def run(self) -> list[nodes.Node]:
		"""
		Read the configured report and return it as a table, on landscape pages in LaTeX.

		:returns: A :class:`~pyTooling.Sphinx.Node.Landscape` container holding the table, or the error message.
		"""
		container = Landscape()

		try:
			self._CheckOptions()
		except SphinxExtensionError as ex:
			message = f"Caught {ex.__class__.__name__} when checking options for directive '{self.directiveName}'."
			return self._internalError(container, __name__, message, ex)

		# Assemble a list of Python source files
		analyzer = Analyzer(self._packageName, self._jsonReport)
		self._coverage = analyzer.Convert()

		self._CreatePages()

		container += self._GenerateCoverageTable()

		return [container]


@export
class CodeCoverageLegend(CodeCoverageBase):
	"""
	The ``report:code-coverage-legend`` directive: a table of a report's coverage levels.
	"""

	directiveName: str = "code-coverage-legend"  #: Name the directive is invoked by.

	has_content =        False                                     #: A boolean; ``True`` if content is allowed.
	required_arguments = 0                                         #: Number of required directive arguments.
	optional_arguments = CodeCoverageBase.optional_arguments + 1  #: Number of optional arguments.

	option_spec: dict[str, Any] = CodeCoverageBase.option_spec | {  # type: ignore[misc]
		"style": stripAndNormalize
	}  #: Mapping of option names to validator functions.

	_style: LegendStyle  #: How the legend is laid out.

	def _CheckOptions(self) -> None:
		"""
		Parse all directive options or use default values.

		:raises SphinxExtensionError: If option ``:style:`` names no :class:`~pyTooling.Sphinx.Report.LegendStyle`.
		:raises ReportExtensionError: If ``pyTooling_CodeCoverage_Packages`` has no entry for the report ID.
		"""
		super()._CheckOptions()

		self._style = self._ParseEnumOption("style", LegendStyle, LegendStyle.horizontal_table)

		try:
			packageConfiguration = self._packageConfigurations[self._reportID]
		except KeyError as ex:
			raise ReportExtensionError(f"No configuration for '{self._reportID}'") from ex

		self._levels = packageConfiguration["levels"]

	def _CreateHorizontalLegendTable(self, identifier: str, classes: list[str]) -> nodes.table:
		"""
		Build the legend as a table with a column per level.

		:param identifier: Identifier of the table.
		:param classes:    CSS classes of the table.
		:returns:          The table.
		"""
		columns: list[tuple[str, Union[int, None]]] = [("Code Coverage:", 3)]
		for level in self._levels:
			if isinstance(level, int):
				columns.append((f"≤{level} %", 2))

		tableGroup = self._CreateSingleRowTableHeader(columns, identifier=identifier, classes=classes)
		tableBody = nodes.tbody()
		tableGroup += tableBody

		legendRow = nodes.row("", classes=["report-codecov-legend-row"])
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
				("Code Coverage", 3),
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
					classes=["report-codecov-legend-row", self._ConvertToColor((level - 1) / 100, "class")]
				)

		return tableGroup.parent

	def run(self) -> list[nodes.Node]:
		"""
		Return the configured report's coverage levels as a table, in the requested style.

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
					identifier=f"{self._reportID}-legend", classes=["report-codecov-legend"]
				)
			elif LegendStyle.Vertical in self._style:
				container += self._CreateVerticalLegendTable(
					identifier=f"{self._reportID}-legend", classes=["report-codecov-legend"]
				)
			else:
				container += nodes.paragraph(text="Unsupported legend style.")
		else:
			container += nodes.paragraph(text="Unsupported legend style.")

		return [container]


@export
class ModuleCoverage(CodeCoverageBase):
	"""
	The ``report:module-coverage`` directive: a module's source code, with highlighted lines - a prototype.

	So far, it shows a fixed source file and highlights fixed lines.
	"""

	directiveName: str = "module-coverage"  #: Name the directive is invoked by.

	has_content =        False  #: A boolean; ``True`` if content is allowed.
	required_arguments = 0      #: Number of required directive arguments.
	optional_arguments = 2      #: Number of optional arguments.

	option_spec: dict[str, Any] = CodeCoverageBase.option_spec | {  # type: ignore[misc]
		"module": stripAndNormalize
	}  #: Mapping of option names to validator functions.

	_packageName: str              #: Name of the Python package.
	_moduleName:  str              #: Name of the module.
	_jsonReport:  Path             #: Coverage.py's JSON report.
	_coverage:    PackageCoverage  #: The package's coverage, read from the report.

	def _CheckOptions(self) -> None:
		"""
		Parse all directive options or use default values.

		:raises SphinxExtensionError: If option ``:module:`` is missing.
		:raises ReportExtensionError: If ``pyTooling_CodeCoverage_Packages`` has no entry for the report ID.
		"""
		super()._CheckOptions()

		self._moduleName = self._ParseStringOption("module")

		try:
			packageConfiguration = self._packageConfigurations[self._reportID]
		except KeyError as ex:
			raise ReportExtensionError(f"No configuration for '{self._reportID}'") from ex

		self._packageName = packageConfiguration["name"]
		self._jsonReport =  packageConfiguration["json_report"]

	def run(self) -> list[nodes.Node]:
		"""
		Read the configured report and return the source code as a literal block.

		:returns: A container holding a paragraph and the literal block, or the error message.
		"""
		container = nodes.container()

		try:
			self._CheckOptions()
		except SphinxExtensionError as ex:
			message = f"Caught {ex.__class__.__name__} when checking options for directive '{self.directiveName}'."
			return self._internalError(container, __name__, message, ex)

		# Assemble a list of Python source files
		analyzer = Analyzer(self._packageName, self._jsonReport)
		self._coverage = analyzer.Convert()

		sourceFile = "../../sphinx_reports/__init__.py"

		container += nodes.paragraph(text=f"Code coverage of {self._moduleName}")

		location = self.state_machine.get_source_and_line(self.lineno)
		rel_filename, filename = self.env.relfn2path(sourceFile)
		self.env.note_dependency(rel_filename)

		reader = LiteralIncludeReader(filename, {"tab-width": 2}, self.config)
		text, lines = reader.read(location=location)

		literalBlock: nodes.Element = nodes.literal_block(text, text, source=filename)
		literalBlock["language"] = "codecov"
		literalBlock["highlight_args"] = extra_args = {}
		extra_args["hl_lines"] = [i for i in range(10, 20)]
		self.set_source_info(literalBlock)

		container += literalBlock

		return [container]
