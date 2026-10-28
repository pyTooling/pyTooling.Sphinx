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
A Sphinx directive rendering a project's dependencies as a table, from the requirements rather than by hand.

A dependency table states, per package, which version is required, what it is licensed under, and what it drags in.
Written by hand it is wrong within a release or two: pyTooling's own documentation table was missing four of the
packages :file:`doc/requirements.txt` requires, listed one that isn't required at all, and called Sphinx BSD-3-Clause
when it is BSD-2-Clause.

**The entrypoints are declared in** :file:`conf.py` **and named by the documents**, the way the domain ``report``
declares its reports:

.. code-block:: Python

   # doc/conf.py
   pyTooling_Dependency_PackageOverrides = "Dependency.PackageOverrides.yaml"
   pyTooling_Dependency_Requirements = {
     "package":       {"file":      "../requirements.txt"},
     "documentation": {"file":      "requirements.txt"},
     "yaml":          {"package":   "pyTooling[yaml]"},
     "packaging":     {"pyproject": True}
   }

.. code-block:: rest

   .. dependency-table:: documentation
      :caption: Documentation dependencies

A requirements file is read - with its ``-r`` includes followed - while :file:`conf.py` is being processed, so a
path that doesn't exist ends the build with one clear message instead of an error box in the middle of a page. A
:file:`pyproject.toml` file is read at the same time; its entrypoint stands for the build requirements of the
``[build-system]`` table. ``True`` names the file in the project's root directory - ``pyTooling_ProjectRoot``,
relative to :file:`conf.py`, by default the parent of the directory :file:`conf.py` is in.

**The data is fetched live** from the package index, once per build and shared between every table of that build:
:file:`requirements.txt`, :file:`tests/requirements.txt` and :file:`doc/requirements.txt` overlap heavily, and a
package they share is downloaded once. The requirements are resolved by pyTooling's
:class:`~pyTooling.Dependency.Resolver.Resolver`, which downloads the packages of one level of the tree in parallel.
That still costs real time, so every table reports what it spent, measured with a
:class:`~pyTooling.Stopwatch.Stopwatch`, and the build ends with the total.
"""
from __future__                      import annotations

from enum                            import Enum, auto
from pathlib                         import Path
from typing                          import TYPE_CHECKING, Any, ClassVar, Iterable, Literal, Mapping, \
                                            Optional as Nullable, TypeVar, cast

from pyTooling.Common                import getFullyQualifiedName
from pyTooling.Decorators            import export, readonly
from pyTooling.Dependency            import DependencyError, UnknownLicenseWarning
from pyTooling.Exceptions            import ConfigurationError, MissingDependencyError
from pyTooling.Licensing             import SPDXLicense, UnknownLicense
from pyTooling.MetaClasses           import ExtendedType
from pyTooling.Stopwatch             import Stopwatch
from pyTooling.Warning               import WarningCollector

from docutils                        import nodes
from docutils.parsers.rst            import directives
from sphinx.application              import Sphinx
from sphinx.util                     import logging

if TYPE_CHECKING:  # pragma: no cover
	# Only this directive needs a package index, so the model is imported when the configuration declares an
	# entrypoint rather than when the extension is loaded - otherwise every documentation build using any of these
	# roles would need the 'dependencies' extra.
	from sphinx.config                 import Config
	from packaging.requirements        import Requirement
	from packaging.specifiers          import SpecifierSet
	from pyTooling.Dependency.Python   import LicenseOverrides, Project, PythonPackageDependencyGraph, \
	                                          PythonPackageIndex, Release, RequirementsFile
	from pyTooling.Dependency.Resolver import Resolution, ResolvedRequirement

from pyTooling.Sphinx                import BaseDirective, SphinxExtensionError, strip, stripAndNormalize


DEFAULT_INDEX_URL = "https://pypi.org"
"""URL of the package index the tables are built from, unless :file:`conf.py` names another."""

DEFAULT_API_URL = "https://pypi.org/pypi/"
"""URL of that index's JSON API."""

DEFAULT_DEPTH = 0
"""Levels of sub-dependencies rendered when nothing says otherwise; ``0`` expands until the tree ends."""

DEFAULT_SIMPLIFIED_VERSIONS = True
"""Whether a version constraint is reduced to its lower bound when the document doesn't say."""


@export
class VersionFormat(Enum):
	"""How many parts of a version number a dependency table prints."""

	Major =           auto()  #: The major part alone, ``≥9``.
	MajorMinor =      auto()  #: Major and minor, ``≥9.1`` - the default.
	MajorMinorPatch = auto()  #: Major, minor and patch, ``≥9.1.2``.
	All =             auto()  #: Every part the constraint states, ``≥9.1.2.dev3``.

	def __str__(self) -> str:
		"""
		Return this format's name, as a document writes it.

		:returns: The enum member's name.
		"""
		return self.name


@export
class DependencyFormat(Enum):
	"""What a line of a dependency tree states about a package."""

	Package =               auto()  #: The name alone.
	PackageVersion =        auto()  #: Name and version constraint.
	PackageLicense =        auto()  #: Name and license.
	PackageVersionLicense = auto()  #: Name, version constraint and license - the default.

	@readonly
	def ShowsVersion(self) -> bool:
		"""
		Whether this format states a version constraint.

		:returns: ``True`` if the version is printed.
		"""
		return self in (DependencyFormat.PackageVersion, DependencyFormat.PackageVersionLicense)

	@readonly
	def ShowsLicense(self) -> bool:
		"""
		Whether this format states a license.

		:returns: ``True`` if the license is printed.
		"""
		return self in (DependencyFormat.PackageLicense, DependencyFormat.PackageVersionLicense)

	def __str__(self) -> str:
		"""
		Return this format's name, as a document writes it.

		:returns: The enum member's name.
		"""
		return self.name


DEFAULT_VERSION_FORMAT = VersionFormat.MajorMinor
"""How many parts of a version number a table prints when the document doesn't say."""

DEFAULT_DEPENDENCY_FORMAT = DependencyFormat.PackageVersionLicense
"""What a line of a dependency tree states when the document doesn't say."""

OPERATOR_SYMBOLS = (("<=", "≤"), (">=", "≥"), ("!=", "≠"), ("==", "="))
"""Comparison operators as a reader writes them. Order matters - the two-character forms have to be tried first."""

_DROPPED_OPERATORS = ("<", "<=", "!=")
"""Operators a simplified constraint drops: an upper bound and an exclusion say what is *not* required."""

TABLE_COLUMNS = (("Package", 3), ("Version", 1), ("License", 2), ("Dependencies", 4))
"""The table's columns, as ``(title, relative width)``."""

ENTRYPOINT_FIELDS = ("file", "files", "package", "packages", "pyproject")
"""
The fields one entrypoint may state in :file:`conf.py`, exactly one of them.

The singular forms take a string and the plural forms an iterable of strings; they are otherwise the same
statement, and a project writes whichever reads better where it stands. ``pyproject`` names a project's
:file:`pyproject.toml` file - ``True`` for the one in the project's root directory, a path relative to that directory,
or ``None`` for a project without one; a project has one such file, so the field has no plural form.
"""

PROJECT_ROOT_CONFIG = "pyTooling_ProjectRoot"
"""
Configuration value naming the project's root directory, relative to :file:`conf.py`.

Unset, the root is the parent of the directory :file:`conf.py` is in - :file:`doc/conf.py` in a project's root
directory. A ``pyproject`` entrypoint's path is relative to it.
"""

CONFIG_PREFIX = "pyTooling_Dependency"
"""Prefix every configuration value of this extension carries in :file:`conf.py`."""

_ConfigRebuild = Literal["env"]
"""What Sphinx accepts as the rebuild condition of a configuration value - the one this extension uses."""

__all__ = [
	"DEFAULT_INDEX_URL", "DEFAULT_API_URL", "DEFAULT_DEPTH", "DEFAULT_SIMPLIFIED_VERSIONS", "OPERATOR_SYMBOLS",
	"TABLE_COLUMNS", "ENTRYPOINT_FIELDS", "CONFIG_PREFIX", "PROJECT_ROOT_CONFIG",
	"DEFAULT_VERSION_FORMAT", "DEFAULT_DEPENDENCY_FORMAT"
]

_logger = logging.getLogger(__name__)

_FormatType = TypeVar("_FormatType", VersionFormat, DependencyFormat)
"""The two option enumerations, so one parser serves both."""


def _SelectedRelease(resolved: ResolvedRequirement) -> Nullable[Release]:
	"""
	Return the release the resolver selected for a requirement, if its details are known.

	A requirement the index couldn't describe still names the release it selected; its lazily loaded properties would
	each retry the download, so only a resolved requirement's release is handed out.

	:param resolved: The resolved requirement.
	:returns:        The selected release, or ``None`` if the requirement wasn't resolved.
	"""
	from pyTooling.Dependency.Resolver import ResolutionStatus

	return resolved.Release if resolved.Status is ResolutionStatus.Resolved else None


def _ReportWarning(prefix: str, warning: BaseException) -> None:
	"""
	Report a warning collected from :mod:`pyTooling.Dependency` as a Sphinx warning.

	Each of the warning's notes follows the message on a line of its own.

	:param prefix:  Text the message starts with, naming what the warning is about.
	:param warning: The collected warning.
	"""
	lines = [f"{prefix} {warning}"]
	lines.extend(f"  {note}" for note in getattr(warning, "__notes__", ()))

	_logger.warning("\n".join(lines))


_COLLECTORS: dict[int, "DependencyCollector"] = {}
"""
The collector of each running build, by the id of its Sphinx application.

It can't live on the build environment, which Sphinx pickles between runs - an open HTTP session and the locks
guarding lazy loading are not picklable, and a cached view of a package index would be stale anyway.
"""


@export
class Entrypoint(metaclass=ExtendedType, slots=True):
	"""
	One entry of ``pyTooling_Dependency_Requirements``: an identifier and the requirements it stands for.

	A file entrypoint - a requirements file or a :file:`pyproject.toml` file - is read while :file:`conf.py` is being
	processed and carries its requirements from then on. A package entrypoint can only be resolved by asking the
	package index, so it carries the package's name and extra and is resolved the first time a table names it.
	"""

	_identifier:   str                                    #: Name the documents refer to this entrypoint by.
	_files:        tuple[Path, ...]                       #: Every file read, a requirements file's references included.
	_packages:     tuple[tuple[str, Nullable[str]], ...]  #: The packages to read, as name and extra.
	_requirements: Nullable[dict[str, Requirement]]       #: The resolved requirements, by canonical package name.

	def __init__(
		self,
		identifier: str,
		files: tuple[Path, ...] = (),
		packages: tuple[tuple[str, Nullable[str]], ...] = (),
		requirements: Nullable[dict[str, Requirement]] = None
	) -> None:
		"""
		Describe one entrypoint.

		:param identifier:   Name the documents refer to this entrypoint by.
		:param files:        Optional, every file read, for a file entrypoint. Default: ``()``.
		:param packages:     Optional, the packages and their extras, for a package entrypoint. Default: ``()``.
		:param requirements: Optional, the requirements, if they are known already. Default: ``None``.
		"""
		self._identifier =   identifier
		self._files =        files
		self._packages =     packages
		self._requirements = requirements

	@readonly
	def Identifier(self) -> str:
		"""
		Name the documents refer to this entrypoint by.

		:returns: The identifier.
		"""
		return self._identifier

	@readonly
	def Files(self) -> tuple[Path, ...]:
		"""
		The requirements file and every file it includes, or the :file:`pyproject.toml` file.

		:returns: The files this entrypoint was read from; empty for a package entrypoint.
		"""
		return self._files

	@readonly
	def Packages(self) -> tuple[tuple[str, Nullable[str]], ...]:
		"""
		The packages this entrypoint reads the requirements of, as ``(name, extra)`` pairs.

		:returns: The packages, or an empty tuple for a file entrypoint.
		"""
		return self._packages

	@readonly
	def Requirements(self) -> Nullable[dict[str, Requirement]]:
		"""
		The requirements this entrypoint stands for.

		:returns: Every required package by its canonical name, or ``None`` if they weren't resolved yet.
		"""
		return self._requirements

	def CacheRequirements(self, requirements: dict[str, Requirement]) -> None:
		"""
		Remember the requirements the package index answered with.

		A package entrypoint can only be resolved by asking the index; remembering the answer is what keeps a second
		table naming the same entrypoint from asking again.

		:param requirements: Every required package, by its canonical name.
		"""
		self._requirements = requirements

	def __repr__(self) -> str:
		"""
		Return a representation naming what this entrypoint reads.

		:returns: The identifier and its source.
		"""
		if len(self._files) > 0:
			source = ", ".join(str(file) for file in self._files)
		else:
			source = ", ".join(name if extra is None else f"{name}[{extra}]" for name, extra in self._packages)

		return f"<Entrypoint {self._identifier}: {source}>"


@export
class DependencyCollector(metaclass=ExtendedType, slots=True):
	"""
	The entrypoints a build declared, the package index it queries, and what querying it cost.

	One collector is shared by every table of a build: a package required by two entrypoints is downloaded once, and
	the time is accumulated so the build can report a total. It exists because the alternative - a table that queries
	the index for itself - multiplies a documentation build's runtime by however many tables it has, and
	:file:`requirements.txt`, :file:`tests/requirements.txt` and :file:`doc/requirements.txt` share most of what they
	require.

	The index is opened the first time a table asks for a package, not when the collector is created: a project may
	declare its entrypoints and then build a document that shows none of them, and that build should not open an
	HTTP session. The tables resolve their requirements with resolvers of their own, as each table has its own depth
	limit; the index they share keeps every project and release it downloaded.
	"""

	_entrypoints: dict[str, Entrypoint]                    #: The entrypoints declared in :file:`conf.py`.
	_indexURL:    str                                      #: URL of the package index's website.
	_apiURL:      str                                      #: URL of the package index's JSON API.
	_overrides:   LicenseOverrides                         #: Licenses stated by hand, where the index can't.
	_graph:       Nullable[PythonPackageDependencyGraph]   #: Graph the downloaded packages are collected in.
	_index:       Nullable[PythonPackageIndex]             #: The package index this build queries, once opened.
	_stopwatch:   Stopwatch                                #: Runs only while a resolution is in progress.
	_unresolved:  dict[str, tuple[str, ...]]               #: Packages whose license the index couldn't answer for,
	                                                       #: mapped to what it published instead.

	def __init__(
		self,
		entrypoints: dict[str, Entrypoint],
		indexURL: str,
		apiURL: str,
		overrides: LicenseOverrides
	) -> None:
		"""
		Collect what a build declared, without opening the package index yet.

		:param entrypoints: The entrypoints declared in :file:`conf.py`, by identifier.
		:param indexURL:    URL of the package index's website.
		:param apiURL:      URL of the package index's JSON API.
		:param overrides:   Licenses stated by hand.
		"""
		self._entrypoints = entrypoints
		self._indexURL =    indexURL
		self._apiURL =      apiURL
		self._overrides =   overrides
		self._graph =       None
		self._index =       None
		self._unresolved =  {}

		# 'preferPause', so each 'with' around a resolution is one active span: 'Activity' is the time spent resolving
		# rather than the age of the collector, and 'ActiveCount' is the number of resolutions
		self._stopwatch =   Stopwatch(preferPause=True)

	@readonly
	def Entrypoints(self) -> dict[str, Entrypoint]:
		"""
		The entrypoints declared in :file:`conf.py`.

		:returns: Every entrypoint by its identifier.
		"""
		return self._entrypoints

	@readonly
	def Index(self) -> PythonPackageIndex:
		"""
		The package index this build queries, opened the first time it is asked for.

		:returns: The package index.
		"""
		from pyTooling.Dependency.Python import PythonPackageDependencyGraph, PythonPackageIndex

		if self._index is None:
			self._graph = PythonPackageDependencyGraph("documentation")
			self._index = PythonPackageIndex("index", self._indexURL, self._apiURL, self._graph, self._overrides)

		return self._index

	@readonly
	def ResolutionCount(self) -> int:
		"""
		Number of resolutions against the package index.

		The stopwatch runs for exactly one span per resolution, so this is its
		:attr:`~pyTooling.Stopwatch.Stopwatch.ActiveCount` - counting them a second time in a field of our own
		would be a second answer to one question.

		:returns: Number of resolutions.
		"""
		return self._stopwatch.ActiveCount

	@readonly
	def Seconds(self) -> float:
		"""
		Time spent resolving requirements against the package index, in seconds.

		This is the stopwatch's :attr:`~pyTooling.Stopwatch.Stopwatch.Activity` - the sum of the intervals it ran -
		not its duration, because it is paused between resolutions and everything the build does in between is not
		time this collector spent.

		:returns: Seconds spent on the index.
		"""
		return self._stopwatch.ActivityInSeconds

	@readonly
	def UnresolvedLicenses(self) -> dict[str, tuple[str, ...]]:
		"""
		Packages whose license the index couldn't answer for, and what it published instead.

		The published fields are what the override file has to answer for, so they are kept rather than only the
		package's name: ``License :: OSI Approved :: BSD License`` names three licenses and is never guessed at, and
		a ``license`` field holding a license's title instead of its SPDX identifier doesn't parse.

		:returns: Canonical names of the packages needing a license override, mapped to what the index published for them.
		"""
		return self._unresolved

	def Resolve(self, requirements: Iterable[Requirement], limit: Nullable[int]) -> Resolution:
		"""
		Resolve requirements against the package index, every level of the tree up front.

		Warnings reported while resolving are handled by :meth:`_ReportWarnings`.

		:param requirements:            The requirements to resolve.
		:param limit:                   Number of levels resolved below the requirements, or ``None`` for unlimited.
		:returns:                       The resolution.
		:raises MissingDependencyError: If the 'dependencies' extra isn't installed.
		"""
		from pyTooling.Dependency.Resolver import ResolutionStrategy, Resolver

		warnings: list[BaseException] = []
		resolver = Resolver(self.Index, strategy=ResolutionStrategy.Eager, limit=limit)
		with self._stopwatch, WarningCollector(warnings):
			resolution = resolver.ResolveRequirements(requirements)

		self._ReportWarnings(warnings)

		return resolution

	def PublishedRequirements(self, packages: Iterable[tuple[str, Nullable[str]]]) -> list[Requirement]:
		"""
		Ask the package index what the latest releases of packages require, or one of their extras.

		Warnings reported while asking are handled by :meth:`_ReportWarnings`.

		:param packages:                Pairs of a package name and an extra's name, or ``None`` for the package's own
		                                requirements.
		:returns:                       The requirements, flattened in the order the packages are given.
		:raises MissingDependencyError: If the 'dependencies' extra isn't installed.
		:raises SphinxExtensionError:   If the index doesn't know a package, can't describe its latest release, or the
		                                package has no such extra.
		"""
		try:
			from requests import RequestException
		except ImportError as ex:  # pragma: no cover
			raise MissingDependencyError(dependency="requests", extra="dependencies") from ex

		from pyTooling.Dependency.Resolver import Resolver

		warnings: list[BaseException] = []
		try:
			with self._stopwatch, WarningCollector(warnings):
				resolution = Resolver(self.Index, limit=0).ResolvePackages(packages)
		except (DependencyError, RequestException, ValueError, KeyError) as cause:
			raise SphinxExtensionError(" ".join((str(cause), *getattr(cause, "__notes__", ())))) from cause
		finally:
			self._ReportWarnings(warnings)

		return [resolved.Requirement for resolved in resolution.Requirements]

	def _ReportWarnings(self, warnings: Iterable[BaseException]) -> None:
		"""
		Record or report the warnings collected while resolving.

		An :class:`~pyTooling.Dependency.UnknownLicenseWarning` is recorded in :attr:`UnresolvedLicenses`. Every other
		warning, e.g. a :class:`~pyTooling.Dependency.BrokenRequirementWarning` for a requirement naming an extra its
		release doesn't declare, is reported as a Sphinx warning.

		:param warnings: The collected warnings.
		"""
		from packaging.utils import canonicalize_name

		for warning in warnings:
			if isinstance(warning, UnknownLicenseWarning):
				# the warning's notes are what the index published, which is the reason an override is needed; keyed by the
				# canonical name, which is the override file's spelling, so two spellings of one package are one entry
				self._unresolved[canonicalize_name(warning.ProjectName)] = warning.Notes
			else:
				_ReportWarning("[dependency-table]", warning)


@export
def readEntrypoints(configuration: Any, confDirectory: Path, projectRoot: Path) -> dict[str, Entrypoint]:
	"""
	Turn ``pyTooling_Dependency_Requirements`` into entrypoints, reading every file it names.

	A requirements file or :file:`pyproject.toml` file is read here rather than when a table is built, so a path that
	doesn't exist ends the build with one message naming the identifier instead of an error box in the middle of a
	page - and so two tables naming the same file read it once.

	:param configuration:           Value of ``pyTooling_Dependency_Requirements``.
	:param confDirectory:           Directory :file:`conf.py` lives in; a requirements file's relative path is resolved
	                                against it.
	:param projectRoot:             The project's root directory; a ``pyproject`` entrypoint's relative path is resolved
	                                against it.
	:returns:                       Every declared entrypoint, by its identifier.
	:raises MissingDependencyError: If the 'dependencies' extra isn't installed.
	:raises SphinxExtensionError:   If the configuration is malformed, or a requirements file or
	                                :file:`pyproject.toml` file can't be read.
	"""
	if not isinstance(configuration, dict):
		raise SphinxExtensionError(
			f"conf.py: {CONFIG_PREFIX}_Requirements: Expected a dictionary, "
			f"got '{getFullyQualifiedName(configuration)}'."
		)

	entrypoints: dict[str, Entrypoint] = {}
	for identifier, declaration in configuration.items():
		location = f"conf.py: {CONFIG_PREFIX}_Requirements:[{identifier}]"

		if not isinstance(declaration, dict):
			raise SphinxExtensionError(
				f"{location}: Expected a dictionary, got '{getFullyQualifiedName(declaration)}'."
			)

		if (unknown := set(declaration) - set(ENTRYPOINT_FIELDS)) != set():
			raise SphinxExtensionError(
				f"{location}: Unknown field(s): {', '.join(sorted(unknown))}. "
				f"Known are: {', '.join(ENTRYPOINT_FIELDS)}."
			)

		if len(stated := [field for field in ENTRYPOINT_FIELDS if field in declaration]) != 1:
			known = ", ".join(ENTRYPOINT_FIELDS)
			raise SphinxExtensionError(
				f"{location}: Exactly one of {known} has to be configured, "
				f"{'none is' if len(stated) == 0 else f'{len(stated)} are'}."
			)

		field = stated[0]
		fieldLocation = f"{location}.{field}"
		value = declaration[field]

		if field == "pyproject":
			if value is not None and value is not True and not isinstance(value, str):
				raise SphinxExtensionError(
					f"{fieldLocation}: Expected None, True or a string, got '{getFullyQualifiedName(value)}'."
				)
			elif value == "":
				raise SphinxExtensionError(f"{fieldLocation}: Path is empty. Use True for the project root's file.")
		elif field in ("file", "package"):
			if not isinstance(value, str):
				raise SphinxExtensionError(
					f"{fieldLocation}: Expected a string, got '{getFullyQualifiedName(value)}'."
				)

			values: tuple[str, ...] = (value,)
		else:
			# a string is an iterable of strings itself, so the plural form has to reject one explicitly - otherwise
			# {"files": "requirements.txt"} would silently become sixteen one-character paths
			if isinstance(value, str) or not isinstance(value, Iterable):
				raise SphinxExtensionError(
					f"{fieldLocation}: Expected an iterable of strings, got '{getFullyQualifiedName(value)}'. "
					f"Use '{field[:-1]}' for a single value."
				)

			# materialized before the items are checked, because an iterable may be a generator this would consume
			values = tuple(value)
			for item in values:
				if not isinstance(item, str):
					raise SphinxExtensionError(
						f"{fieldLocation}: Expected strings, got '{getFullyQualifiedName(item)}'."
					)

		if field in ("file", "files"):
			entrypoints[identifier] = _FileEntrypoint(identifier, fieldLocation, values, confDirectory)
		elif field == "pyproject":
			entrypoints[identifier] = _PyProjectEntrypoint(identifier, fieldLocation, value, projectRoot)
		else:
			entrypoints[identifier] = _PackageEntrypoint(identifier, values)

	return entrypoints


def _FileEntrypoint(
	identifier: str,
	location: str,
	files: tuple[str, ...],
	confDirectory: Path
) -> Entrypoint:
	"""
	Read one entrypoint's requirements files.

	Several files are read as several trees and flattened in the order they are declared, so a later file's
	statement wins - the rule a single file's ``-r`` references already follow.

	A line that can't be parsed as a requirement - a :class:`~pyTooling.Dependency.BrokenRequirementWarning` - is
	reported as a Sphinx warning naming the file and line; the file's other requirements are read.

	:param identifier:              Identifier of the entrypoint.
	:param location:                Where in :file:`conf.py` this came from.
	:param files:                   The declared paths.
	:param confDirectory:           Directory relative paths resolve against.
	:returns:                       The entrypoint, with its requirements read.
	:raises MissingDependencyError: If the 'dependencies' extra isn't installed.
	:raises SphinxExtensionError:   If a file can't be read.
	"""
	try:
		from packaging.utils import canonicalize_name
	except ImportError as ex:  # pragma: no cover
		raise MissingDependencyError(dependency="packaging", extra="dependencies") from ex

	from pyTooling.Dependency.Python import RequirementsFile

	readFiles: list[Path] = []
	requirements: dict[str, Requirement] = {}

	for file in files:
		path = Path(file)
		if not path.is_absolute():
			path = confDirectory / path

		warnings: list[BaseException] = []
		try:
			with WarningCollector(warnings):
				requirementsFile = RequirementsFile.Parse(path)
		except (DependencyError, OSError, UnicodeDecodeError) as cause:
			raise SphinxExtensionError(f"{location}: Requirements file '{path}' can't be read: {cause}") from cause

		for warning in warnings:
			_ReportWarning(f"{location}:", warning)

		# the tree knows every file it was read from; walking it here would be a second answer to one question
		readFiles.extend(requirementsFile.AnalyzedRequirementFiles)
		requirements.update({canonicalize_name(req.name): req for req in requirementsFile.AllRequirements})

	return Entrypoint(identifier, files=tuple(readFiles), requirements=requirements)


def _PyProjectEntrypoint(identifier: str, location: str, file: Nullable[bool | str], projectRoot: Path) -> Entrypoint:
	"""
	Read the build requirements of one entrypoint's :file:`pyproject.toml` file.

	The requirements are the ``requires`` key of the ``[build-system]`` table (:pep:`518`), read by pyTooling's
	:meth:`PyProjectFile.Parse <pyTooling.Dependency.Python.PyProjectFile.Parse>`. A file without a ``[build-system]``
	table has no build requirements, and neither has a project declaring ``None``, which has no such file. A requirement
	that can't be parsed - an :class:`~pyTooling.Dependency.UnparsableRequirementWarning` - is reported as a Sphinx
	warning naming the file; the file's other requirements are read.

	:param identifier:              Identifier of the entrypoint.
	:param location:                Where in :file:`conf.py` this came from.
	:param file:                    ``True`` for :file:`pyproject.toml` in the project's root directory, a path relative
	                                to that directory, or ``None`` if the project has no such file.
	:param projectRoot:             The project's root directory.
	:returns:                       The entrypoint, with its requirements read.
	:raises MissingDependencyError: If the 'dependencies' extra isn't installed.
	:raises SphinxExtensionError:   If the file can't be read, isn't valid TOML, or its ``[build-system]`` table
	                                states no list of requirements.
	"""
	try:
		from packaging.utils import canonicalize_name
	except ImportError as ex:  # pragma: no cover
		raise MissingDependencyError(dependency="packaging", extra="dependencies") from ex

	from pyTooling.Dependency.Python import PyProjectFile

	if file is None:
		return Entrypoint(identifier, requirements={})
	elif file is True:
		path = projectRoot / "pyproject.toml"
	else:
		path = Path(file)
		if not path.is_absolute():
			path = projectRoot / path

	warnings: list[BaseException] = []
	try:
		with WarningCollector(warnings):
			pyProjectFile = PyProjectFile.Parse(path)
	except (DependencyError, OSError, UnicodeDecodeError) as cause:
		raise SphinxExtensionError(f"{location}: Project file '{path}' can't be read: {cause}") from cause

	for warning in warnings:
		_ReportWarning(f"{location}:", warning)

	requirements = {canonicalize_name(req.name): req for req in pyProjectFile.BuildRequirements}

	return Entrypoint(identifier, files=(pyProjectFile.Path,), requirements=requirements)


def _PackageEntrypoint(identifier: str, packages: tuple[str, ...]) -> Entrypoint:
	"""
	Describe one entrypoint's packages, which only the package index can resolve.

	:param identifier: Identifier of the entrypoint.
	:param packages:   The declared packages, each optionally with one extra.
	:returns:          The entrypoint, with its packages recorded and its requirements still unresolved.
	"""
	requested: list[tuple[str, Nullable[str]]] = []
	for package in packages:
		name, _, bracket = package.partition("[")
		requested.append((name.strip(), bracket.rstrip("]").strip() or None))

	return Entrypoint(identifier, packages=tuple(requested))


@export
def prepareEntrypoints(sphinx: Sphinx, config: Config) -> None:
	"""
	Call-back for Sphinx' ``config-inited`` event, reading the entrypoints and the license overrides.

	A ``pyproject`` entrypoint is resolved against the project's root directory, :data:`PROJECT_ROOT_CONFIG` relative to
	:file:`conf.py`, or the parent of :file:`conf.py`'s directory if it isn't set.

	A build declaring no entrypoint does nothing here - not even import :mod:`pyTooling.Dependency.Python`, so a
	project using only this extension's roles doesn't need the ``dependencies`` extra.

	:param sphinx:                The Sphinx application.
	:param config:                The configuration, after :file:`conf.py` was read.
	:raises SphinxExtensionError: If the configuration is malformed, or a requirements file, :file:`pyproject.toml`
	                              file or license override file can't be read.
	:raises SphinxExtensionError: If a license override file is configured, but pyTooling's ``yaml`` extra isn't
	                              installed.
	"""
	if len(declarations := getattr(config, f"{CONFIG_PREFIX}_Requirements", {})) == 0:
		return

	confDirectory = Path(sphinx.confdir)
	if (projectRootSetting := getattr(config, PROJECT_ROOT_CONFIG, None)) is None:
		projectRoot = confDirectory.parent
	else:
		projectRoot = Path(projectRootSetting)
		if not projectRoot.is_absolute():
			projectRoot = confDirectory / projectRoot

	try:
		from pyTooling.Dependency.Python import LicenseOverrides
	except MissingDependencyError as cause:  # pragma: no cover
		raise SphinxExtensionError(
			f"conf.py: {CONFIG_PREFIX}_Requirements: Querying a package index needs the 'dependencies' extra: "
			"pip install pyTooling[dependencies]"
		) from cause

	overrides = LicenseOverrides()
	if (overrideFile := getattr(config, f"{CONFIG_PREFIX}_PackageOverrides", None)) is not None:
		path = Path(overrideFile)
		if not path.is_absolute():
			path = confDirectory / path

		try:
			overrides = LicenseOverrides.FromFile(path)
		except MissingDependencyError as cause:
			raise SphinxExtensionError(
				f"conf.py: {CONFIG_PREFIX}_PackageOverrides: Reading the override file needs the 'yaml' extra: "
				f"pip install pyTooling[yaml]"
			) from cause
		except (DependencyError, ConfigurationError, OSError) as cause:
			raise SphinxExtensionError(
				f"conf.py: {CONFIG_PREFIX}_PackageOverrides: Override file '{path}' can't be read: {cause}"
			) from cause

	_COLLECTORS[id(sphinx)] = DependencyCollector(
		readEntrypoints(declarations, confDirectory, projectRoot),
		getattr(config, f"{CONFIG_PREFIX}_IndexURL", DEFAULT_INDEX_URL),
		getattr(config, f"{CONFIG_PREFIX}_APIURL", DEFAULT_API_URL),
		overrides
	)


@export
class DependencyTable(BaseDirective):
	"""
	The ``dependency-table`` directive: an entrypoint's dependencies, rendered from the requirements.

	One argument, the identifier of an entrypoint declared in ``pyTooling_Dependency_Requirements``. ``:depth:``
	says how many levels of sub-dependencies to expand, ``:simplified-versions:`` whether a constraint is reduced to
	its lower bound, and ``:caption:`` puts a caption under the table; which package index is queried and which
	licenses are stated by hand are build-wide and configured in :file:`conf.py`.
	"""

	directiveName: str = "dependency-table"  #: Name the directive is invoked by.

	#: The configuration values this directive adds to :file:`conf.py`, as ``name: (default, rebuild, types)``. Each is
	#: registered with :data:`CONFIG_PREFIX` as prefix, e.g. ``pyTooling_Dependency_Requirements``.
	#:
	#: ``Requirements`` maps an identifier to what it names - a file, files, a package, packages or a
	#: :file:`pyproject.toml` file. The other three are build-wide, because one package index is queried per build and
	#: one override file answers for it. All four are ``"env"``-rebuilt: changing any of them changes every table.
	configValues: ClassVar[dict[str, tuple[Any, _ConfigRebuild, Any]]] = {
		"Requirements":     ({},                "env", dict),
		"PackageOverrides": (None,              "env", (str, Path)),
		"IndexURL":         (DEFAULT_INDEX_URL, "env", str),
		"APIURL":           (DEFAULT_API_URL,   "env", str),
	}

	_simplify:         bool               #: Whether this table's version constraints are reduced to their lower bound.
	_versionFormat:    VersionFormat      #: How many parts of a version number this table prints.
	_dependencyFormat: DependencyFormat   #: What a line of this table's dependency trees states.

	has_content =               False  #: A boolean; ``True`` if content is allowed.
	required_arguments =        1      #: Number of required directive arguments: the entrypoint's identifier.
	optional_arguments =        0      #: Number of optional arguments after the required ones.
	final_argument_whitespace = False  #: A boolean; ``True`` if the last argument may contain spaces.
	# docutils declares 'option_spec' on 'Directive' and 'BaseDirective' assigns it, so mypy calls every
	# spelling of this override a conflict with one of them
	#: Mapping of option names to validator functions.
	option_spec: dict[str, Any] = {  # type: ignore[misc]
		"caption":             strip,
		"depth":               directives.nonnegative_int,
		"simplified-versions": stripAndNormalize,
		"version-format":      stripAndNormalize,
		"dependency-format":   stripAndNormalize,
	}

	def run(self) -> list[nodes.Node]:
		"""
		Resolve the named entrypoint against the package index and return its requirements as a table.

		:returns: A ``table`` node, or an error node when the entrypoint couldn't be resolved.
		"""
		identifier =             self.arguments[0].strip()
		self._simplify =         self._ParseBooleanOption("simplified-versions", DEFAULT_SIMPLIFIED_VERSIONS)
		self._versionFormat =    self._ParseFormatOption("version-format", VersionFormat, DEFAULT_VERSION_FORMAT)
		self._dependencyFormat = self._ParseFormatOption(
			"dependency-format", DependencyFormat, DEFAULT_DEPENDENCY_FORMAT
		)

		# ':depth: 0' - and the default - means expand until the tree ends, which is the resolver's 'None'
		depth = self.options.get("depth", DEFAULT_DEPTH)
		limit: Nullable[int] = None if depth == 0 else depth

		with Stopwatch() as stopwatch:
			try:
				collector = self._Collector()
				requirements = self._Requirements(identifier, collector)
				resolution = collector.Resolve(requirements.values(), limit)
				table = self._CreateTable(identifier, resolution)
			except SphinxExtensionError as cause:
				return [self.state.document.reporter.error(
					f"{self.directiveName}: {cause}", line=self.lineno
				)]

		seconds = stopwatch.DurationInSeconds

		# what this table cost, not what the build has spent so far - a package another table already downloaded is
		# free here, and that is the point of sharing the collector
		_logger.info(f"[{self.directiveName}] {identifier}: {len(requirements)} package(s), {seconds:.2f} s")

		return [table]

	def _ParseFormatOption(self, optionName: str, enumType: type[_FormatType], default: _FormatType) -> _FormatType:
		"""
		Read an option naming a member of an enumeration, or fall back to its default.

		:attr:`~pyTooling.Sphinx.BaseDirective._ParseEnumOption` requires the option and
		lower-cases what it reads; these two have a default and are written the way the members are spelled, so a
		document says ``:version-format: MajorMinor`` rather than ``major_minor``.

		:param optionName:            Name of the option to read.
		:param enumType:              The enumeration its value names a member of.
		:param default:               The member to use when the option isn't given.
		:returns:                     The named member.
		:raises SphinxExtensionError: If the value names no member.
		"""
		if (option := self.options.get(optionName, None)) is None:
			return default

		for member in enumType:
			if option.lower() == member.name.lower():
				return member

		known = ", ".join(member.name for member in enumType)
		raise SphinxExtensionError(
			f"{self.directiveName}::{optionName}: '{option}' is not one of: {known}."
		)

	def _Collector(self) -> DependencyCollector:
		"""
		Return the build's collector, which :func:`prepareEntrypoints` created when :file:`conf.py` was read.

		The collector belongs to the running application rather than to the directive, because a document with three
		tables would otherwise open three indexes and download the same packages three times. It deliberately does
		*not* live on the build environment: Sphinx pickles that between runs, and neither an open HTTP session nor a
		cached view of a package index survives being pickled - or should.

		:returns:                     The collector shared by every table of this build.
		:raises SphinxExtensionError: If no entrypoint was configured.
		"""
		if (collector := _COLLECTORS.get(id(self.env.app), None)) is None:
			raise SphinxExtensionError(
				f"No entrypoint is configured. Declare one in conf.py: {CONFIG_PREFIX}_Requirements."
			)

		return collector

	def _Requirements(self, identifier: str, collector: DependencyCollector) -> dict[str, Requirement]:
		"""
		Return what the named entrypoint requires.

		A file entrypoint was read when :file:`conf.py` was processed and answers immediately; a package entrypoint
		is resolved against the package index the first time a table names it, and remembers the answer.

		:param identifier:              Identifier the document names.
		:param collector:               The build's collector.
		:returns:                       Every required package, by its canonical name.
		:raises MissingDependencyError: If the 'dependencies' extra isn't installed.
		:raises SphinxExtensionError:   If the identifier is unknown, or the package index can't answer for the
		                                entrypoint's packages.
		"""
		try:
			from packaging.utils import canonicalize_name
		except ImportError as ex:  # pragma: no cover
			raise MissingDependencyError(dependency="packaging", extra="dependencies") from ex

		if (entrypoint := collector.Entrypoints.get(identifier, None)) is None:
			known = ", ".join(sorted(collector.Entrypoints)) or "none"
			raise SphinxExtensionError(
				f"Entrypoint '{identifier}' is not configured in conf.py: {CONFIG_PREFIX}_Requirements. "
				f"Known are: {known}."
			)

		for file in entrypoint.Files:
			self.env.note_dependency(str(file))

		if (requirements := entrypoint.Requirements) is not None:
			return requirements

		# several packages flatten in the order they are declared, the rule a file's '-r' references already follow
		requirements = {}
		for requirement in collector.PublishedRequirements(entrypoint.Packages):
			requirements[canonicalize_name(requirement.name)] = requirement

		entrypoint.CacheRequirements(requirements)

		return requirements

	def _CreateTable(self, identifier: str, resolution: Resolution) -> nodes.table:
		"""
		Render the resolved requirements as a four-column table, one row per package, sorted by name.

		:param identifier: Identifier of the entrypoint, used as the table's identifier.
		:param resolution: The entrypoint's requirements, resolved.
		:returns:          The finished table.
		"""
		from packaging.utils import canonicalize_name

		tableGroup = self._CreateSingleRowTableHeader(
			columns=list(TABLE_COLUMNS),
			identifier=identifier,
			classes=["dependency-table"]
		)
		tableGroup += (tableBody := nodes.tbody())

		if resolution.RequirementCount == 0:
			tableBody += self._CreateEmptyRow(len(TABLE_COLUMNS))
		else:
			for resolved in sorted(resolution.Requirements, key=lambda item: canonicalize_name(item.Requirement.name)):
				tableBody += self._CreateRow(resolved)

		table = cast(nodes.table, tableGroup.parent)
		if (caption := self.options.get("caption", None)) is not None:
			# the caption is ReST, not text: it is written with markup - ``packaging`` in pyTooling's own captions -
			# and a 'title' built from a string would print the backticks
			captionNodes, messages = self.state.inline_text(caption, self.lineno)
			table.insert(0, nodes.title(caption, "", *captionNodes, *messages))

		return table

	@staticmethod
	def _CreateEmptyRow(columnCount: int) -> nodes.row:
		"""
		Render the one row a table with no requirements gets: a single cell spanning every column.

		A table showing nothing but its header reads as a defect. pyTooling's own :file:`requirements.txt` is empty
		- the package has no mandatory dependencies - and that is a statement worth printing.

		:param columnCount: Number of columns the cell has to span.
		:returns:           The table row.
		"""
		tableRow = nodes.row("", classes=["dependency-table-row"])

		entry = nodes.entry("", morecols=columnCount - 1)
		entry += nodes.paragraph("", "", nodes.emphasis(text="No dependencies"))
		tableRow += entry

		return tableRow

	def _CreateRow(self, resolved: ResolvedRequirement) -> nodes.row:
		"""
		Render one required package as a table row.

		A package the index doesn't know, or one with no release matching the requirement, still gets a row - the
		specifier the entrypoint states is worth showing even when nothing else could be resolved.

		:param resolved: The resolved requirement to render.
		:returns:        The table row.
		"""
		tableRow = nodes.row("", classes=["dependency-table-row"])

		requirement = resolved.Requirement
		release =     _SelectedRelease(resolved)

		tableRow += self._PackageEntry(requirement, resolved.Project)
		specifier = self._FormatSpecifier(requirement.specifier, self._simplify, self._versionFormat)

		tableRow += nodes.entry("", nodes.paragraph(text=specifier))
		tableRow += self._LicenseEntry(release)
		tableRow += self._DependenciesEntry(resolved)

		return tableRow

	@staticmethod
	def _FormatVersion(version: str, versionFormat: VersionFormat) -> str:
		"""
		Shorten a version number to the parts a table prints.

		``≥0.4.6`` says more than a reader of a dependency table needs; the parts that matter are the ones a
		constraint is usually written against. A version with fewer parts than asked for is left as it is - ``≥9``
		does not become ``≥9.0`` - because padding would state a precision the requirement didn't.

		:param version:       The version, as the constraint writes it.
		:param versionFormat: How many parts to keep.
		:returns:             The shortened version.
		"""
		if versionFormat is VersionFormat.All:
			return version

		parts = {VersionFormat.Major: 1, VersionFormat.MajorMinor: 2, VersionFormat.MajorMinorPatch: 3}[versionFormat]

		return ".".join(version.split(".")[:parts])

	@staticmethod
	def _FormatSpecifier(specifier: SpecifierSet, simplify: bool, versionFormat: VersionFormat) -> str:
		"""
		Render a version constraint the way a reader writes one.

		The comparison operators become their mathematical symbols and the versions are shortened to
		``versionFormat``. A simplified constraint keeps only what a package *has to be at least*: an upper bound
		and an exclusion say what a release must not be, which is the packaging problem rather than the reader's,
		and ``~=`` is written as the lower bound it implies. Simplifying everything away leaves the constraint as it
		was written - ``<4.0`` alone is still the whole statement.

		:param specifier:     The constraint to render.
		:param simplify:      Whether to reduce the constraint to its lower bound.
		:param versionFormat: How many parts of each version to keep.
		:returns:             The constraint, or ``any`` when nothing is constrained.
		"""
		def render(operator: str, version: str) -> str:
			shortened = DependencyTable._FormatVersion(version, versionFormat)
			for written, symbol in OPERATOR_SYMBOLS:
				if operator == written:
					return f"{symbol}{shortened}"

			return f"{operator}{shortened}"

		if len(specifier) == 0:
			return "any"

		specifiers = sorted(specifier, key=lambda item: (item.version, item.operator))
		if simplify:
			kept = [
				render(">=" if item.operator == "~=" else item.operator, item.version)
				for item in specifiers if item.operator not in _DROPPED_OPERATORS
			]
			if len(kept) > 0:
				# shortening can make two constraints identical - '>=1.2.3, >1.2.9' is '≥1.2, >1.2' at MajorMinor -
				# and printing one statement twice reads as a defect
				return ", ".join(dict.fromkeys(kept))

		rendered = [render(item.operator, item.version) for item in specifiers]

		return ", ".join(dict.fromkeys(rendered))

	@staticmethod
	def _PackageURL(project: Nullable[Project]) -> Nullable[str]:
		"""
		Return the page a package's name should link to, most useful first.

		A project states none of these reliably, so there are three chances at one: its **documentation** answers
		*what is this*, its **repository** answers *where does it come from*, and its page on the **package index**
		is what the index itself can always answer. Only a package the index doesn't know at all goes unlinked.

		:param project: The project, or ``None`` if the index doesn't know it.
		:returns:       The URL to link the name to, or ``None`` if there is nothing to link to.
		"""
		if project is None:
			return None

		for url in (project.DocumentationURL, project.RepositoryURL, project.URL):
			if url is not None:
				return str(url)

		return None

	@classmethod
	def _PackageEntry(cls, requirement: Requirement, project: Nullable[Project]) -> nodes.entry:
		"""
		Render the package's name, linked to where a reader can find out about it.

		:param requirement: The requirement naming the package.
		:param project:     The project, or ``None`` if the index doesn't know it.
		:returns:           The table entry.
		"""
		entry = nodes.entry()
		name = project.Name if project is not None else requirement.name

		if (url := cls._PackageURL(project)) is not None:
			entry += nodes.paragraph("", "", nodes.reference("", name, refuri=url))
		else:
			entry += nodes.paragraph(text=name)

		return entry

	@staticmethod
	def _LicenseEntry(release: Nullable[Release]) -> nodes.entry:
		"""
		Render a release's license, linked to its text where one is known.

		The license' **name** is shown rather than its SPDX identifier - ``Apache License 2.0``, not ``Apache-2.0`` -
		because the table is read by a person and the identifier is what an expression writes.

		A license that didn't resolve is an :class:`~pyTooling.Licensing.UnknownLicense`, never a blank cell, and it
		is shown **as the index published it** - in italics, so it reads as a quotation rather than as an identifier.
		The reader should see that the index said *something*, and what it was.

		:param release: The release to render the license of, or ``None``.
		:returns:       The table entry.
		"""
		entry = nodes.entry()

		if (text := DependencyTable._LicenseName(release)) is None:
			entry += nodes.paragraph("", "", nodes.emphasis(text=DependencyTable._PublishedLicense(release)))

			return entry

		if (url := DependencyTable._LicenseURL(release)) is not None:
			entry += nodes.paragraph("", "", nodes.reference("", text, refuri=url))
		else:
			entry += nodes.paragraph(text=text)

		return entry

	@staticmethod
	def _LicenseName(release: Nullable[Release]) -> Nullable[str]:
		"""
		Return the name(s) of the licenses a release is published under.

		:param release: The release to name the license of, or ``None``.
		:returns:       The license' name, or ``None`` if nothing resolved.
		"""
		if release is None:
			return None

		# 'Licenses' never comes back empty: what didn't resolve is an 'UnknownLicense', which is SPDX's own way of
		# saying so and keeps the published text
		licenses = release.Licenses
		if all(isinstance(license, UnknownLicense) for license in licenses):
			return None

		return ", ".join(license.Name for license in licenses)

	@staticmethod
	def _PublishedLicense(release: Nullable[Release]) -> str:
		"""
		Return what the package index published, for a license that didn't resolve.

		:param release: The release, or ``None`` if the index couldn't describe it.
		:returns:       What was published, or ``unknown`` when that was nothing either.
		"""
		if release is None:
			return "unknown"

		published = release.LicenseExpression.OriginalText.strip()

		return published if published != "" else ", ".join(license.Name for license in release.Licenses) or "unknown"

	@staticmethod
	def _LicenseURL(release: Nullable[Release]) -> Nullable[str]:
		"""
		Return the page a license should link to, most specific first.

		**The project's own** :file:`LICENSE` **file wins**: it is the license as this project publishes it, which
		is the document a reader auditing a dependency actually wants. Most projects don't state one, though - it
		comes from ``project_urls`` or from the override file - so a license on the SPDX List falls back to its own
		published pages, in the order of who is speaking: the licensor's own page, then OSI's entry, then SPDX's.
		A ``LicenseRef-`` has none of those and stays unlinked, because nothing published it.

		:param release: The release to link the license of, or ``None``.
		:returns:       The URL to link to, or ``None`` if nothing published this license.
		"""
		if release is None:
			return None

		if release.LicenseURL is not None:
			return str(release.LicenseURL)

		for license in release.Licenses:
			if isinstance(license, SPDXLicense):
				for url in (license.License.URL, license.License.OSIURL, license.License.SPDXURL):
					if url is not None:
						return url

		return None

	def _DependenciesEntry(self, resolved: ResolvedRequirement) -> nodes.entry:
		"""
		Render the dependencies of a resolved requirement as a nested bullet list.

		The dependencies are the selected release's unconditional requirements and the requirements of the extras the
		requirement names (``pyTooling[yaml]``). A package already on the path isn't listed again, so a dependency
		cycle ends.

		:param resolved: The resolved requirement to render the dependencies of.
		:returns:        The table entry.
		"""
		entry = nodes.entry()

		if _SelectedRelease(resolved) is None:
			entry += nodes.paragraph("", "", nodes.emphasis(text="not evaluated"))
			return entry

		if len(dependencies := self._Dependencies(resolved)) == 0:
			entry += nodes.paragraph("", "", nodes.emphasis(text="none"))
			return entry

		entry += self._CreateBulletList(dependencies)

		return entry

	@staticmethod
	def _Dependencies(resolved: ResolvedRequirement) -> list[ResolvedRequirement]:
		"""
		Return the dependencies of a resolved requirement, without those closing a cycle.

		:param resolved: The resolved requirement.
		:returns:        Its dependencies, except those whose package is on the path already.
		"""
		from pyTooling.Dependency.Resolver import ResolutionStatus

		return [dependency for dependency in resolved.Dependencies if dependency.Status is not ResolutionStatus.Cycle]

	def _CreateBulletList(self, dependencies: list[ResolvedRequirement]) -> nodes.bullet_list:
		"""
		Render resolved requirements as a bullet list, each item followed by its own dependencies.

		An item whose own dependencies the depth limit cuts off gets a marker saying how many weren't expanded.

		:param dependencies: The resolved requirements to list.
		:returns:            The bullet list.
		"""
		from pyTooling.Dependency.Resolver import ResolutionStatus

		bulletList = nodes.bullet_list()

		for dependency in sorted(dependencies, key=lambda item: item.Requirement.name.lower()):
			item = nodes.list_item()
			item += self._RequirementParagraph(dependency.Requirement, dependency.Project, _SelectedRelease(dependency))

			if len(nested := self._Dependencies(dependency)) > 0:
				if any(nestedDependency.Status is ResolutionStatus.LimitReached for nestedDependency in nested):
					item += self._CreateLimitMarker(len(nested))
				else:
					item += self._CreateBulletList(nested)

			bulletList += item

		return bulletList

	@staticmethod
	def _CreateLimitMarker(count: int) -> nodes.bullet_list:
		"""
		Render the marker of a tree the ``:depth:`` limit cut off: how many dependencies weren't expanded.

		:param count: Number of the package's own dependencies, which weren't expanded.
		:returns:     A bullet list with one item.
		"""
		text = f"… {count} more {'dependency' if count == 1 else 'dependencies'} not expanded"

		bulletList = nodes.bullet_list()
		bulletList += nodes.list_item("", nodes.paragraph("", "", nodes.emphasis(text=text)), classes=["dependency-limit"])

		return bulletList

	def _RequirementParagraph(
		self,
		requirement: Requirement,
		project: Nullable[Project],
		release: Nullable[Release]
	) -> nodes.paragraph:
		"""
		Render one line of a dependency tree: the package, what is required of it, and what it is licensed under.

		The license is the reason a dependency tree is in this table at all - a package pulls in what its own
		dependencies are licensed under, and reading that off the tree is the point. It is linked and parenthesised
		so the line still reads as one requirement.

		:param requirement: The requirement to render.
		:param project:     The project, or ``None`` if the index doesn't know it.
		:param release:     The release satisfying the requirement, or ``None`` if none was found.
		:returns:           The paragraph.
		"""
		paragraph = nodes.paragraph()

		name = project.Name if project is not None else requirement.name
		if (url := self._PackageURL(project)) is not None:
			paragraph += nodes.reference("", name, refuri=url)
		else:
			paragraph += nodes.Text(name)

		if self._dependencyFormat.ShowsVersion:
			specifier = self._FormatSpecifier(requirement.specifier, self._simplify, self._versionFormat)
			if specifier != "any":
				paragraph += nodes.Text(f" {specifier}")

		if self._dependencyFormat.ShowsLicense:
			paragraph += nodes.Text(" (")
			if (license := self._LicenseName(release)) is None:
				# the same statement the License column makes: what the index published, in italics, so it reads as
				# a quotation rather than as an identifier
				paragraph += nodes.emphasis(text=self._PublishedLicense(release))
			elif (licenseURL := self._LicenseURL(release)) is not None:
				paragraph += nodes.reference("", license, refuri=licenseURL)
			else:
				paragraph += nodes.Text(license)
			paragraph += nodes.Text(")")

		return paragraph


@export
def formatUnresolvedLicenses(unresolved: Mapping[str, tuple[str, ...]]) -> str:
	"""
	Describe the packages needing a license override, grouped by what the package index published for them.

	Grouped rather than listed one per line, because one ambiguous statement usually accounts for most of the list:
	``License :: OSI Approved :: BSD License`` names three licenses, so every package whose only license information
	is that classifier lands here for the same reason and is worth reading as one group.

	:param unresolved: Names of the packages needing an override, mapped to what the index published for them.
	:returns:          The message, as one line naming the count and two lines per reason.
	"""
	byReason: dict[tuple[str, ...], list[str]] = {}
	for packageName, published in sorted(unresolved.items()):
		byReason.setdefault(published, []).append(packageName)

	lines = [f"[dependency-table] {len(unresolved)} package(s) need a license override:"]

	# the biggest group first, so the statement to fix first is the one at the top
	for published, packageNames in sorted(byReason.items(), key=lambda item: (-len(item[1]), item[0])):
		reason = "; ".join(published) if len(published) > 0 else "the index published no license information"
		lines.append(f"  {reason}")
		lines.append(f"    {', '.join(packageNames)}")

	return "\n".join(lines)


def reportBuildTime(app: Sphinx, exception: Nullable[Exception]) -> None:
	"""
	Report what querying the package index cost this build.

	The tables are fetched live, so this is the number to look at before deciding what a cache would be worth. The
	packages whose license had to be guessed at - or couldn't be - are named too, because that is the list the
	override file has to answer for.

	:param app:       The Sphinx application that finished building.
	:param exception: The exception that ended the build, or ``None`` if it succeeded.
	"""
	if (collector := _COLLECTORS.pop(id(app), None)) is None or collector.ResolutionCount == 0:
		return

	_logger.info(
		f"[dependency-table] {collector.ResolutionCount} resolution(s) against the package index, "
		f"{collector.Seconds:.2f} s in total."
	)

	if len(unresolved := collector.UnresolvedLicenses) > 0:
		_logger.warning(formatUnresolvedLicenses(unresolved))
