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
Directives rendering a code coverage report: a table per directory and source file, and a source file's listing.

The reports are declared in :file:`conf.py` under ``pyTooling_CodeCoverage_Packages``, each with an identifier a
directive names in its ``:reportid:`` option. A report is a Cobertura XML file (``xml_report``) - written for any
language, e.g. by coverage.py or gcovr - or coverage.py's JSON report (``json_report``); it is read with the code
coverage data model of :mod:`pyEDAA.Reports.CodeCoverage`. An entry with the key ``pages`` gets a page per directory
and source file, generated below that document name (see :mod:`pyTooling.Sphinx.CodeCoveragePages`); ``sources`` is
the directory the report's file paths are relative to, which a source file's listing is read from:

.. code-block:: Python

   # doc/conf.py
   pyTooling_CodeCoverage_Packages = {
     "src": {
       "name":        "myPackage",
       "json_report": "../report/coverage/coverage.json",
       "sources":     "..",
       "pages":       "coverage/src",
       "fail_below":  80,
       "levels":      "default"
     },
     "vhdl": {
       "name":        "myDesign",
       "xml_report":  "../report/coverage/cobertura.xml",
       "sources":     "../src",
       "pages":       "coverage/vhdl",
       "fail_below":  80,
       "levels":      "default"
     }
   }

The coverage levels - limits, descriptions and CSS classes - are declared under ``pyTooling_CodeCoverage_Levels``;
:attr:`CodeCoverageBase.defaultCoverageDefinitions` holds the ``default`` palette.

.. seealso::

   :ref:`DIR/CodeCoverage`
      |rarr| The directives' options and configuration, with examples.
   :mod:`pyTooling.Sphinx.CodeCoveragePages`
      |rarr| The pages per directory and source file, and the role ``:cov:``.
"""
from __future__                       import annotations

from pathlib                          import Path
from typing                           import TYPE_CHECKING, Any, ClassVar, Optional as Nullable, TypedDict, Union

from docutils                         import nodes
from docutils.parsers.rst.directives  import flag
from sphinx.application               import Sphinx
from sphinx.config                    import Config
from sphinx.util.logging              import getLogger

from pyTooling.Common                 import getFullyQualifiedName
from pyTooling.Decorators             import export

from pyTooling.Sphinx                 import INDENTATION, BaseDirective, LegendStyle, ReportExtensionError
from pyTooling.Sphinx                 import ReportsPackageMissingError, SphinxExtensionError, strip, stripAndNormalize
from pyTooling.Sphinx.Node            import Landscape
from pyTooling.Sphinx.Pages           import ReportPages

if TYPE_CHECKING:  # pragma: no cover
	# pyEDAA.Reports is an optional dependency (extra 'reports'), imported where a report is read.
	from pyEDAA.Reports.CodeCoverage    import BaseWithPath, CoverageSummary, Directory, File


__all__ = ["CONFIG_PREFIX", "REPORT_KEYS"]

#: Prefix every configuration value of the code coverage directives carries in :file:`conf.py`.
CONFIG_PREFIX = "pyTooling_CodeCoverage"

#: The keys of a report's configuration naming its file, and the report format each stands for.
REPORT_KEYS = {
	"xml_report":  "Cobertura",
	"json_report": "coverage.py",
}


@export
def compactDirectory(directory: Directory) -> Directory:
	"""
	Follow a chain of directories, which hold no file and exactly one directory each, to its last directory.

	The report tables and pages show such a chain as one entry, e.g. ``pyTooling/Sphinx``, the last directory's.

	:param directory: The first directory of the chain.
	:returns:         The last directory of the chain; the directory itself, if it holds files or several directories.
	"""
	while len(directory._files) == 0 and len(directory._directories) == 1:
		directory = next(iter(directory._directories.values()))

	return directory


@export
def isCompacted(directory: Nullable[Directory]) -> bool:
	"""
	Check whether a directory is shown together with its single subdirectory: it holds no file and one directory, and
	isn't the report's root.

	:param directory: The directory, or ``None``.
	:returns:         ``True``, if the directory is compacted with its subdirectory.
	"""
	return (
		directory is not None and directory._parent is not None and len(directory._files) == 0
		and len(directory._directories) == 1
	)


@export
def compactedName(entity: BaseWithPath) -> str:
	"""
	Return the name a directory or file is shown with: a directory's name is joined with those of the parent
	directories it was compacted with by :func:`compactDirectory`.

	:param entity: The directory or file.
	:returns:      The name, e.g. ``pyTooling/Sphinx``.
	"""
	names = [entity._name]
	parent = entity._parent
	if hasattr(entity, "_directories"):
		while isCompacted(parent):
			names.insert(0, parent._name)
			parent = parent._parent

	return "/".join(names)


@export
class PackageConfiguration(TypedDict):
	"""An entry of ``pyTooling_CodeCoverage_Packages``, after :meth:`CodeCoverageBase.CheckConfiguration` read it."""

	name:      str                                                #: Name of the measured project, the report's root.
	report:    Path                                               #: The report file.
	format:    str                                                #: The report's format, a value of :data:`REPORT_KEYS`.
	sources:   Nullable[Path]                                     #: Directory the report's file paths are relative to.
	pages:     Nullable[str]                                      #: Document name the pages are generated below.
	failBelow: float                                              #: Coverage below which the package fails.
	levels:    Union[str, dict[Union[int, str], dict[str, str]]]  #: Coverage levels, or the name of a palette.


@export
class CodeCoverageBase(BaseDirective):
	"""
	Base-class of the code coverage directives: the shared options, the configuration, the reports and the coverage
	levels.

	The configuration is checked and the reports are read once per build - by :meth:`CheckConfiguration` and
	:meth:`ReadReports` -, into class variables every directive reads.
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
	_reports:                  ClassVar[dict[str, CoverageSummary]] = {}       #: Reports read by :meth:`ReadReports`.
	_readErrors:               ClassVar[dict[str, Exception]] = {}             #: Why a report couldn't be read, by ID.

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

	def _PackageConfiguration(self) -> PackageConfiguration:
		"""
		Return the configuration of the report named by option ``:reportid:``, and take its coverage levels.

		:returns:                     The report's configuration.
		:raises ReportExtensionError: If ``pyTooling_CodeCoverage_Packages`` has no entry for the report ID.
		"""
		try:
			packageConfiguration = self._packageConfigurations[self._reportID]
		except KeyError as ex:
			raise ReportExtensionError(f"No configuration for '{self._reportID}'") from ex

		self._levels = packageConfiguration["levels"]
		return packageConfiguration

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
		Read every configured code coverage report, once per build.

		A report that can't be read keeps the exception, which a directive or a report's pages show when they need it.

		:param sphinxApplication: Sphinx application instance.
		"""
		getLogger(__name__).info("[REPORT] Reading code coverage reports ...")

		cls._reports =    {}
		cls._readErrors = {}
		for reportID, packageConfiguration in cls._packageConfigurations.items():
			try:
				cls._reports[reportID] = cls._ReadReport(packageConfiguration)
			except Exception as ex:
				cls._readErrors[reportID] = ex

	@classmethod
	def GetReport(cls, reportID: str) -> CoverageSummary:
		"""
		Return a report read by :meth:`ReadReports`.

		:param reportID:              Identifier of the report.
		:returns:                     The report's root directory, aggregated.
		:raises ReportExtensionError: If the report wasn't read, chained to the exception reading it raised.
		"""
		try:
			return cls._reports[reportID]
		except KeyError:
			cause = cls._readErrors.get(reportID, None)
			raise ReportExtensionError(f"Code coverage report '{reportID}' wasn't read.") from cause

	@staticmethod
	def _ReadReport(packageConfiguration: PackageConfiguration) -> CoverageSummary:
		"""
		Read a report file with the reader of its format.

		:param packageConfiguration:        The report's configuration.
		:returns:                           The report's root directory, aggregated.
		:raises ReportsPackageMissingError: If pyEDAA.Reports, or its code coverage model, isn't installed.
		"""
		try:
			if packageConfiguration["format"] == "Cobertura":
				from pyEDAA.Reports.CodeCoverage.Cobertura  import Document
			else:
				from pyEDAA.Reports.CodeCoverage.CoveragePy import Document
		except ImportError as cause:
			raise ReportsPackageMissingError("Reading a code coverage report", "'pyEDAA.Reports' >= 0.20") from cause

		return Document(packageConfiguration["report"], analyzeAndConvert=True).ToCoverageSummary()

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
		:raises ReportExtensionError: If a package configuration has neither ``xml_report`` nor ``json_report``, or both.
		:raises ReportExtensionError: If the report file doesn't exist.
		:raises ReportExtensionError: If the ``sources`` directory doesn't exist.
		:raises ReportExtensionError: If ``pages`` isn't a string.
		:raises ReportExtensionError: If ``pages`` isn't a relative document name. |br|
		                              Use a name like 'coverage/src', separated by '/', without '.' or '..'.
		:raises ReportExtensionError: If a package configuration with ``pages`` has no ``sources``.
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
			allPackages: dict[str, dict[str, Any]] = sphinxConfiguration[variableName]
		except (KeyError, AttributeError) as ex:
			raise ReportExtensionError(f"Configuration option '{variableName}' is not configured.") from ex

		for reportID, packageConfiguration in allPackages.items():
			configurationName = f"conf.py: {variableName}:[{reportID}]"

			try:
				packageName = packageConfiguration["name"]
			except KeyError as ex:
				raise ReportExtensionError(f"{configurationName}.name: Configuration is missing.") from ex

			reportKeys = [key for key in REPORT_KEYS if key in packageConfiguration]
			if len(reportKeys) != 1:
				ex = ReportExtensionError(f"{configurationName}: Configuration needs exactly one report file.")
				ex.add_note(f"Use one of: {', '.join(REPORT_KEYS)}")
				raise ex

			reportKey = reportKeys[0]
			reportFile = Path(packageConfiguration[reportKey])
			if not reportFile.exists():
				raise ReportExtensionError(
					f"{configurationName}.{reportKey}: Coverage report file '{reportFile}' doesn't exist."
				) from FileNotFoundError(reportFile)

			if (sources := packageConfiguration.get("sources", None)) is not None:
				sources = Path(sources)
				if not sources.is_dir():
					raise ReportExtensionError(
						f"{configurationName}.sources: Source directory '{sources}' doesn't exist."
					) from FileNotFoundError(sources)

			if (pages := packageConfiguration.get("pages", None)) is not None:
				pages = ReportPages.CheckPagesConfiguration(configurationName, pages)
				if sources is None:
					raise ReportExtensionError(f"{configurationName}.sources: Configuration is missing, as 'pages' needs it.")

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
				"report":    reportFile,
				"format":    REPORT_KEYS[reportKey],
				"sources":   sources,
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
		Look up the coverage level a coverage falls into, in the report's levels, and return one of its fields.

		:param currentLevel: The coverage, in range 0.0..1.0; a negative value selects level ``error``.
		:param configKey:    The field to return: ``class`` or ``desc``.
		:returns:            The field's value of the first level whose limit is above the coverage.
		"""
		return self.LevelOf(self._levels, currentLevel, configKey)


@export
class CodeCoverage(CodeCoverageBase):
	"""
	The ``report:code-coverage`` directive: a table of a report's code coverage, per directory and source file.

	A report with pages links every directory and file to its page, and lists the top-level ones in a hidden table of
	contents, so the pages are below this document in the navigation.
	"""

	directiveName: str = "code-coverage"  #: Name the directive is invoked by.

	has_content =        False                                     #: A boolean; ``True`` if content is allowed.
	required_arguments = 0                                         #: Number of required directive arguments.
	optional_arguments = CodeCoverageBase.optional_arguments + 1  #: Number of optional arguments.

	option_spec: dict[str, Any] = CodeCoverageBase.option_spec | {  # type: ignore[misc]
		"no-branch-coverage": flag
	}  #: Mapping of option names to validator functions.

	_noBranchCoverage: bool             #: Whether the branch coverage columns are left out.
	_name:             str              #: Name of the measured project, shown for the report's root.
	_coverage:         CoverageSummary  #: The report's root directory.

	def _CheckOptions(self) -> None:
		"""
		Parse all directive options or use default values.

		:raises ReportExtensionError: If ``pyTooling_CodeCoverage_Packages`` has no entry for the report ID.
		"""
		super()._CheckOptions()

		self._noBranchCoverage = "no-branch-coverage" in self.options
		self._name = self._PackageConfiguration()["name"]

	def _GenerateCoverageTable(self) -> nodes.table:
		"""
		Build the table: two header rows, a row per directory and source file, and a summary row.

		:returns: The table.
		"""
		cssClasses = ["report-codecov-table", f"report-codecov-{self._reportID}"]
		cssClasses.extend(self._cssClasses)

		columns = [
			("Directory", [(f"{INDENTATION}File", 5)], None),
			("Lines",     [("Total", 1), ("Excluded", 1), ("Covered", 1), ("Missing", 1), ("Coverage", 1)], None),
			("Branches",  [("Total", 1), ("Covered", 1), ("Partial", 1), ("Missing", 1), ("Coverage", 1)], None),
		]

		if self._noBranchCoverage:
			columns.pop(2)

		tableGroup = self._CreateDoubleRowTableHeader(identifier=self._reportID, columns=columns, classes=cssClasses)
		tableBody = nodes.tbody()
		tableGroup += tableBody

		self._RenderRow(tableBody, self._coverage, nodes.Text(f"📦{self._name}"), "report-package")
		self._RenderDirectory(tableBody, self._coverage, 1)

		tableRow = nodes.row("", classes=["report-summary", self._ConvertToColor(self._coverage.Coverage, "class")])
		tableBody += tableRow
		tableRow += nodes.entry("", nodes.Text(f"Overall ({self._coverage.FileCount} files):"))
		self._RenderCounters(tableRow, self._coverage)

		return tableGroup.parent

	def _RenderDirectory(self, tableBody: nodes.tbody, directory: Directory, level: int) -> None:
		"""
		Add a row per directory and file in a directory, recursing into the directories.

		A chain of directories holding no file and one directory each is a single row (see :func:`compactDirectory`).

		:param tableBody: The table body the rows are added to.
		:param directory: The directory.
		:param level:     The depth in the hierarchy of the directories and files.
		"""
		for name in sorted(directory._directories):
			subdirectory = compactDirectory(directory._directories[name])
			self._RenderRow(
				tableBody, subdirectory, self._NameCell(subdirectory, f"{INDENTATION * level}📁"), "report-directory"
			)
			self._RenderDirectory(tableBody, subdirectory, level + 1)

		for name in sorted(directory._files):
			file = directory._files[name]
			self._RenderRow(tableBody, file, self._NameCell(file, f"{INDENTATION * level}📄"), "report-file")

	def _NameCell(self, entity: BaseWithPath, prefix: str) -> nodes.Node:
		"""
		Create the content of the cell naming a directory or file, linked to its page if the report has pages.

		:param entity: The directory or file.
		:param prefix: The indentation and the icon written before the name.
		:returns:      The cell's content.
		"""
		from pyTooling.Sphinx.CodeCoveragePages import CodeCoverageReportPages

		name = compactedName(entity)
		if CodeCoverageReportPages.HasPages(self._reportID):
			pages = CodeCoverageReportPages.GetPages(self._reportID)
			if (entry := pages.Entry(entity)) is not None:
				# a reference has to be inside a text element; an inline keeps the cell free of a paragraph, as the
				# others are
				return nodes.inline("", "", nodes.Text(prefix), pages.CreateReference("cov", entry, self.env.docname, name))

		return nodes.Text(f"{prefix}{name}")

	def _RenderRow(self, tableBody: nodes.tbody, entity: BaseWithPath, name: nodes.Node, cssClass: str) -> None:
		"""
		Add a row of a directory or file: its name and counters, colored by its coverage level.

		:param tableBody: The table body the row is added to.
		:param entity:    The directory or file.
		:param name:      The content of the name's cell.
		:param cssClass:  The CSS class of the row's kind.
		"""
		tableRow = nodes.row("", classes=[cssClass, self._ConvertToColor(entity.Coverage, "class")])
		tableBody += tableRow

		tableRow += nodes.entry("", name)
		self._RenderCounters(tableRow, entity)

	def _RenderCounters(self, tableRow: nodes.row, entity: BaseWithPath) -> None:
		"""
		Add the cells of a directory's or file's line and - unless left out - branch counters.

		:param tableRow: The row the cells are added to.
		:param entity:   The directory or file.
		"""
		tableRow += nodes.entry("", nodes.Text(f"{entity.TotalLines}"))
		tableRow += nodes.entry("", nodes.Text(f"{entity.ExcludedLines}"))
		tableRow += nodes.entry("", nodes.Text(f"{entity.CoveredLines}"))
		tableRow += nodes.entry("", nodes.Text(f"{entity.MissingLines}"))
		tableRow += nodes.entry("", nodes.Text(f"{entity.LineCoverage:.1%}"))
		if not self._noBranchCoverage:
			tableRow += nodes.entry("", nodes.Text(f"{entity.TotalBranches}"))
			tableRow += nodes.entry("", nodes.Text(f"{entity.CoveredBranches}"))
			tableRow += nodes.entry("", nodes.Text(f"{entity.PartialLines}"))
			tableRow += nodes.entry("", nodes.Text(f"{entity.MissingBranches}"))
			tableRow += nodes.entry("", nodes.Text(f"{entity.BranchCoverage:.1%}"))

	def run(self) -> list[nodes.Node]:
		"""
		Return the report as a table, on landscape pages in LaTeX, and - if the report has pages - a hidden table of
		contents of its top-level directories and files.

		:returns: A :class:`~pyTooling.Sphinx.Node.Landscape` container holding the table, or the error message; then
		          the table of contents, if the report has pages.
		"""
		container = Landscape()

		try:
			self._CheckOptions()
		except SphinxExtensionError as ex:
			message = f"Caught {ex.__class__.__name__} when checking options for directive '{self.directiveName}'."
			return self._internalError(container, __name__, message, ex)

		try:
			self._coverage = self.GetReport(self._reportID)
		except ReportExtensionError as ex:
			cause = ex if ex.__cause__ is None else ex.__cause__
			message = f"Caught {cause.__class__.__name__} when reading code coverage report '{self._reportID}'."
			return self._internalError(container, __name__, message, cause)

		container += self._GenerateCoverageTable()

		from pyTooling.Sphinx.CodeCoveragePages import CodeCoverageReportPages

		if not CodeCoverageReportPages.HasPages(self._reportID):
			return [container]

		return [container, CodeCoverageReportPages.GetPages(self._reportID).TableOfContents(self.env.docname)]


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

		:raises SphinxExtensionError: If option ``:style:`` names no :class:`~pyTooling.Sphinx.LegendStyle`.
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
class FileCoverage(CodeCoverageBase):
	"""
	The ``report:file-coverage`` directive: a source file's listing, each line marked by its coverage state.

	The directive's argument names the file by its path in the report. The listing is read from the report's
	``sources`` directory.
	"""

	directiveName: str = "file-coverage"  #: Name the directive is invoked by.

	has_content =        False  #: A boolean; ``True`` if content is allowed.
	required_arguments = 1      #: Number of required directive arguments.
	optional_arguments = 2      #: Number of optional arguments.

	def run(self) -> list[nodes.Node]:
		"""
		Return the source file's listing.

		:returns: A container holding the listing, or the error message.
		"""
		from pyTooling.Sphinx.CodeCoveragePages import createListing

		container = nodes.container(classes=["report-file-coverage"])

		try:
			self._CheckOptions()
			sources = self._PackageConfiguration()["sources"]
			file = self._FindFile(self.GetReport(self._reportID), self.arguments[0])
		except SphinxExtensionError as ex:
			message = f"Caught {ex.__class__.__name__} when checking options for directive '{self.directiveName}'."
			return self._internalError(container, __name__, message, ex)

		if sources is None:
			message = f"Code coverage report '{self._reportID}' has no 'sources' directory."
			return self._internalError(container, __name__, message, ReportExtensionError(message))

		container += createListing(file, sources, anchors=False)
		return [container]

	@staticmethod
	def _FindFile(coverage: CoverageSummary, path: str) -> File:
		"""
		Find a file of a report by its path.

		:param coverage:              The report's root directory.
		:param path:                  The file's path in the report, e.g. ``src/Counter.vhdl``.
		:returns:                     The file.
		:raises ReportExtensionError: If the report has no such file.
		"""
		for file in coverage.IterateFiles():
			if file.Path.as_posix() == path.strip("/"):
				return file

		raise ReportExtensionError(f"Code coverage report has no file '{path}'.")
