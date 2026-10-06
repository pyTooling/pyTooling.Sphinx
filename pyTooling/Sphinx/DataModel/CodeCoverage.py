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
Data model of a code coverage report: statement and branch coverage per Python package and module.

A :class:`PackageCoverage` holds its sub-packages and its modules - each a :class:`ModuleCoverage` -, so the model
mirrors the package hierarchy. Both derive from :class:`Coverage`, which holds the counts read from the report; a
package adds the aggregated counts of everything below it.

The model is filled by :class:`~pyTooling.Sphinx.Adapter.Coverage.Analyzer`.
"""
from pathlib               import Path
from typing                import Generic, Optional as Nullable, TypeVar, Union

from pyTooling.Decorators  import export, readonly
from pyTooling.MetaClasses import ExtendedType


_ParentType = TypeVar("_ParentType", bound="Base")
"""Type of an element's parent in the hierarchy."""


@export
class Base(Generic[_ParentType], metaclass=ExtendedType, slots=True):
	"""
	Base-class of all elements of the data model: a name, and a parent in the hierarchy.
	"""

	_name:   str                    #: Name of the element.
	_parent: Nullable[_ParentType]  #: Parent of the element, or ``None`` at the hierarchy's root.

	def __init__(self, name: str, parent: Nullable[_ParentType] = None) -> None:
		"""
		Initialize an element with its name and its parent.

		:param name:   Name of the element.
		:param parent: Optional, parent of the element. Default: ``None``.
		"""
		self._name =   name
		self._parent = parent

	@readonly
	def Name(self) -> str:
		"""
		Read-only property to access the element's name (:attr:`_name`).

		:returns: Name of the element.
		"""
		return self._name

	@readonly
	def Parent(self) -> Nullable[_ParentType]:
		"""
		Read-only property to access the element's parent (:attr:`_parent`).

		:returns: Parent of the element, or ``None`` at the hierarchy's root.
		"""
		return self._parent


@export
class Coverage(Base[_ParentType], Generic[_ParentType]):
	"""
	Statement and branch coverage of a Python source file.

	The counts are set by the adapter reading a report; until then, every count is ``0`` and the coverage is ``-1.0``.
	"""

	_file:               Path   #: The source file.

	_totalStatements:    int    #: Number of statements.
	_excludedStatements: int    #: Number of statements excluded from the coverage.
	_coveredStatements:  int    #: Number of executed statements.
	_missingStatements:  int    #: Number of statements not executed.

	_totalBranches:      int    #: Number of branches.
	_coveredBranches:    int    #: Number of fully taken branches.
	_partialBranches:    int    #: Number of partially taken branches.
	_missingBranches:    int    #: Number of branches not taken.

	_coverage:           float  #: Overall coverage as reported, in range 0.0..1.0, or ``-1.0`` if unknown.

	def __init__(self, name: str, file: Path, parent: Nullable[_ParentType] = None) -> None:
		"""
		Initialize a coverage element with all counts set to ``0``.

		:param name:   Name of the package or module.
		:param file:   The source file.
		:param parent: Optional, the package containing this element. Default: ``None``.
		"""
		super().__init__(name, parent)
		self._file = file

		self._totalStatements =    0
		self._excludedStatements = 0
		self._coveredStatements =  0
		self._missingStatements =  0

		self._totalBranches =      0
		self._coveredBranches =    0
		self._partialBranches =    0
		self._missingBranches =    0

		self._coverage = -1.0

	@readonly
	def File(self) -> Path:
		"""
		Read-only property to access the source file (:attr:`_file`).

		:returns: The source file.
		"""
		return self._file

	@readonly
	def TotalStatements(self) -> int:
		"""
		Read-only property to access the number of statements (:attr:`_totalStatements`).

		:returns: Number of statements.
		"""
		return self._totalStatements

	@readonly
	def ExcludedStatements(self) -> int:
		"""
		Read-only property to access the number of excluded statements (:attr:`_excludedStatements`).

		:returns: Number of statements excluded from the coverage.
		"""
		return self._excludedStatements

	@readonly
	def CoveredStatements(self) -> int:
		"""
		Read-only property to access the number of executed statements (:attr:`_coveredStatements`).

		:returns: Number of executed statements.
		"""
		return self._coveredStatements

	@readonly
	def MissingStatements(self) -> int:
		"""
		Read-only property to access the number of statements not executed (:attr:`_missingStatements`).

		:returns: Number of statements not executed.
		"""
		return self._missingStatements

	@readonly
	def StatementCoverage(self) -> float:
		"""
		Read-only property to return the statement coverage: executed statements over all statements.

		:returns: Statement coverage in range 0.0..1.0, or ``0.0`` if there are no statements.
		"""
		if self._totalStatements <= 0:
			return 0.0

		return self._coveredStatements / self._totalStatements

	@readonly
	def TotalBranches(self) -> int:
		"""
		Read-only property to access the number of branches (:attr:`_totalBranches`).

		:returns: Number of branches.
		"""
		return self._totalBranches

	@readonly
	def CoveredBranches(self) -> int:
		"""
		Read-only property to access the number of fully taken branches (:attr:`_coveredBranches`).

		:returns: Number of fully taken branches.
		"""
		return self._coveredBranches

	@readonly
	def PartialBranches(self) -> int:
		"""
		Read-only property to access the number of partially taken branches (:attr:`_partialBranches`).

		:returns: Number of partially taken branches.
		"""
		return self._partialBranches

	@readonly
	def MissingBranches(self) -> int:
		"""
		Read-only property to access the number of branches not taken (:attr:`_missingBranches`).

		:returns: Number of branches not taken.
		"""
		return self._missingBranches

	@readonly
	def BranchCoverage(self) -> float:
		"""
		Read-only property to return the branch coverage: fully and partially taken branches over all branches.

		:returns: Branch coverage in range 0.0..1.0, or ``0.0`` if there are no branches.
		"""
		if self._totalBranches <= 0:
			return 0.0

		return (self._coveredBranches + self._partialBranches) / self._totalBranches

	@readonly
	def Coverage(self) -> float:
		"""
		Read-only property to access the overall coverage as reported (:attr:`_coverage`).

		:returns: Overall coverage in range 0.0..1.0, or ``-1.0`` if unknown.
		"""
		return self._coverage


@export
class ModuleCoverage(Coverage["PackageCoverage"]):
	"""
	Code coverage of a Python module.
	"""

	def __init__(self, name: str, file: Path, parent: Nullable["PackageCoverage"] = None) -> None:
		"""
		Initialize a module's coverage and add it to its package.

		:param name:   Name of the module.
		:param file:   The module's source file.
		:param parent: Optional, the package containing the module. Default: ``None``.
		"""
		super().__init__(name, file, parent)

		if parent is not None:
			parent._modules[name] = self


@export
class PackageCoverage(Coverage["PackageCoverage"]):
	"""
	Code coverage of a Python package: its own counts (of its :file:`__init__.py`), its sub-packages and its modules.
	"""

	_modules:  dict[str, ModuleCoverage]     #: The package's modules, by name.
	_packages: dict[str, "PackageCoverage"]  #: The package's sub-packages, by name.

	def __init__(self, name: str, file: Path, parent: Nullable["PackageCoverage"] = None) -> None:
		"""
		Initialize a package's coverage and add it to its parent package.

		:param name:   Name of the package.
		:param file:   The package's source file.
		:param parent: Optional, the package containing this package. Default: ``None``.
		"""
		super().__init__(name, file, parent)

		if parent is not None:
			parent._packages[name] = self

		self._modules =   {}
		self._packages =  {}

	@readonly
	def FileCount(self) -> int:
		"""
		Read-only property to access the number of source files in this package and below (:attr:`TotalModuleCount`).

		:returns: Number of source files, the same as :attr:`TotalModuleCount`.
		"""
		return self.TotalModuleCount

	@readonly
	def PackageCount(self) -> int:
		"""
		Read-only property to return the number of direct sub-packages.

		:returns: Number of sub-packages.
		"""
		return len(self._packages)

	@readonly
	def ModuleCount(self) -> int:
		"""
		Read-only property to return the number of direct modules, counting the package's :file:`__init__.py`.

		:returns: Number of modules.
		"""
		return 1 + len(self._modules)

	@readonly
	def TotalPackageCount(self) -> int:
		"""
		Read-only property to return the number of packages, this one and all below it.

		:returns: Number of packages.
		"""
		return 1 + sum(p.TotalPackageCount for p in self._packages.values())

	@readonly
	def TotalModuleCount(self) -> int:
		"""
		Read-only property to return the number of modules in this package and below, each :file:`__init__.py` counting.

		:returns: Number of modules.
		"""
		return 1 + sum(p.TotalModuleCount for p in self._packages.values()) + len(self._modules)

	@readonly
	def Packages(self) -> dict[str, "PackageCoverage"]:
		"""
		Read-only property to access the sub-packages (:attr:`_packages`).

		:returns: The sub-packages, by name.
		"""
		return self._packages

	@readonly
	def Modules(self) -> dict[str, ModuleCoverage]:
		"""
		Read-only property to access the modules (:attr:`_modules`).

		:returns: The modules, by name.
		"""
		return self._modules

	@readonly
	def AggregatedTotalStatements(self) -> int:
		"""
		Read-only property to return the number of statements in this package and below.

		:returns: Number of statements.
		"""
		return (
			self._totalStatements +
			sum(p.AggregatedTotalStatements for p in self._packages.values()) +
			sum(m._totalStatements for m in self._modules.values())
		)

	@readonly
	def AggregatedExcludedStatements(self) -> int:
		"""
		Read-only property to return the number of excluded statements in this package and below.

		:returns: Number of statements excluded from the coverage.
		"""
		return (
			self._excludedStatements +
			sum(p.AggregatedExcludedStatements for p in self._packages.values()) +
			sum(m._excludedStatements for m in self._modules.values())
		)

	@readonly
	def AggregatedCoveredStatements(self) -> int:
		"""
		Read-only property to return the number of executed statements in this package and below.

		:returns: Number of executed statements.
		"""
		return (
			self._coveredStatements +
			sum(p.AggregatedCoveredStatements for p in self._packages.values()) +
			sum(m._coveredStatements for m in self._modules.values())
		)

	@readonly
	def AggregatedMissingStatements(self) -> int:
		"""
		Read-only property to return the number of statements not executed in this package and below.

		:returns: Number of statements not executed.
		"""
		return (
			self._missingStatements +
			sum(p.AggregatedMissingStatements for p in self._packages.values()) +
			sum(m._missingStatements for m in self._modules.values())
		)

	@readonly
	def AggregatedStatementCoverage(self) -> float:
		"""
		Read-only property to return the statement coverage of this package and below.

		:returns: Statement coverage in range 0.0..1.0.
		"""
		return self.AggregatedCoveredStatements / self.AggregatedTotalStatements

	@readonly
	def AggregatedTotalBranches(self) -> int:
		"""
		Read-only property to return the number of branches in this package and below.

		:returns: Number of branches.
		"""
		return (
			self._totalBranches +
			sum(p.AggregatedTotalBranches for p in self._packages.values()) +
			sum(m._totalBranches for m in self._modules.values())
		)

	@readonly
	def AggregatedCoveredBranches(self) -> int:
		"""
		Read-only property to return the number of fully taken branches in this package and below.

		:returns: Number of fully taken branches.
		"""
		return (
			self._coveredBranches +
			sum(p.AggregatedCoveredBranches for p in self._packages.values()) +
			sum(m._coveredBranches for m in self._modules.values())
		)

	@readonly
	def AggregatedPartialBranches(self) -> int:
		"""
		Read-only property to return the number of partially taken branches in this package and below.

		:returns: Number of partially taken branches.
		"""
		return (
			self._partialBranches +
			sum(p.AggregatedPartialBranches for p in self._packages.values()) +
			sum(m._partialBranches for m in self._modules.values())
		)

	@readonly
	def AggregatedMissingBranches(self) -> int:
		"""
		Read-only property to return the number of branches not taken in this package and below.

		:returns: Number of branches not taken.
		"""
		return (
			self._missingBranches +
			sum(p.AggregatedMissingBranches for p in self._packages.values()) +
			sum(m._missingBranches for m in self._modules.values())
		)

	@readonly
	def AggregatedBranchCoverage(self) -> float:
		"""
		Read-only property to return the branch coverage of this package and below.

		:returns: Branch coverage in range 0.0..1.0.
		"""
		return (self.AggregatedCoveredBranches + self.AggregatedPartialBranches) / self.AggregatedTotalBranches

	def __getitem__(self, key: str) -> Union["PackageCoverage", ModuleCoverage]:
		"""
		Return a module or sub-package by name; a module wins over a sub-package of the same name.

		:param key:       Name of the module or sub-package.
		:returns:         The module or sub-package.
		:raises KeyError: If neither a module nor a sub-package has that name.
		"""
		try:
			return self._modules[key]
		except KeyError:
			return self._packages[key]
