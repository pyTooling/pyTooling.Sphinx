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
Unit tests for :mod:`pyTooling.Sphinx.Report.DataModel.CodeCoverage`: packages, modules and the aggregated counts.
"""
from pathlib                                        import Path

from pyTooling.Sphinx.Report.DataModel.CodeCoverage import ModuleCoverage, PackageCoverage
from pyTooling.Testing                              import Testcase, testsuite, testcase


if __name__ == "__main__":  # pragma: no cover
	print("ERROR: you called a testcase declaration file as an executable module.")
	print("Use: 'python -m unittest <testcase module>'")
	exit(1)


@testsuite("Code coverage data model: instantiation")
class Instantiation(Testcase):
	"""Creating packages and modules."""

	@testcase("Package")
	def Package(self) -> None:
		"""
		A package has a name, a file, no parent and counts of zero.

		Creates a package and checks its name, its file, its parent, a count and the coverage of -1.0.
		"""
		cov = PackageCoverage("myPackage", Path("__init__.py"))

		self.assertEqual("myPackage", cov.Name)
		self.assertEqual(Path("__init__.py"), cov.File)
		self.assertIsNone(cov.Parent)
		self.assertEqual(0, cov.TotalStatements)
		self.assertEqual(-1.0, cov.Coverage)

	@testcase("Module")
	def Module(self) -> None:
		"""
		A module has a name and no parent.

		Creates a module without a package and checks its name and parent.
		"""
		cov = ModuleCoverage("myModule", Path("__init__.py"))

		self.assertEqual("myModule", cov.Name)
		self.assertIsNone(cov.Parent)

	@testcase("Hierarchy")
	def Hierarchy(self) -> None:
		"""
		A sub-package and a module add themselves to their parent package.

		Creates a package with a sub-package and a module, and checks the parent's mappings, the item access and the
		counts.
		"""
		root = PackageCoverage("myPackage", Path("myPackage/__init__.py"))
		sub = PackageCoverage("sub", Path("myPackage/sub/__init__.py"), root)
		module = ModuleCoverage("Module", Path("myPackage/Module.py"), root)

		self.assertIs(root, sub.Parent)
		self.assertEqual({"sub": sub}, root.Packages)
		self.assertEqual({"Module": module}, root.Modules)
		self.assertIs(sub, root["sub"])
		self.assertIs(module, root["Module"])
		self.assertEqual(1, root.PackageCount)
		self.assertEqual(2, root.ModuleCount)
		self.assertEqual(2, root.TotalPackageCount)
		self.assertEqual(3, root.TotalModuleCount)
		self.assertEqual(3, root.FileCount)

	@testcase("Unknown member")
	def UnknownMember(self) -> None:
		"""
		Accessing a name that is neither a module nor a sub-package raises a KeyError.

		Creates an empty package and accesses a member.
		"""
		root = PackageCoverage("myPackage", Path("myPackage/__init__.py"))

		with self.assertRaises(KeyError):
			_ = root["unknown"]


@testsuite("Code coverage data model: counts")
class Counts(Testcase):
	"""Statement and branch coverage of an element, and the aggregation over a package."""

	@staticmethod
	def _Fill(cov: ModuleCoverage | PackageCoverage, statements: int, covered: int, branches: int, partial: int) -> None:
		"""
		Set an element's counts, as the adapter does.

		:param cov:        The element.
		:param statements: Number of statements.
		:param covered:    Number of executed statements.
		:param branches:   Number of branches.
		:param partial:    Number of partially taken branches; as many are fully taken.
		"""
		cov._totalStatements = statements
		cov._coveredStatements = covered
		cov._missingStatements = statements - covered
		cov._totalBranches = branches
		cov._coveredBranches = partial
		cov._partialBranches = partial
		cov._missingBranches = branches - 2 * partial

	@testcase("Statement and branch coverage")
	def Coverage(self) -> None:
		"""
		The statement coverage is executed over all statements; the branch coverage counts partial branches too.

		Fills a module with 8 of 10 statements and 1 + 1 of 4 branches, and checks 0.8 and 0.5.
		"""
		module = ModuleCoverage("Module", Path("Module.py"))
		self._Fill(module, 10, 8, 4, 1)

		self.assertEqual(0.8, module.StatementCoverage)
		self.assertEqual(0.5, module.BranchCoverage)

	@testcase("No statements")
	def Empty(self) -> None:
		"""
		An element without statements or branches has a coverage of 0.0.

		Creates a module and checks both coverages.
		"""
		module = ModuleCoverage("Module", Path("Module.py"))

		self.assertEqual(0.0, module.StatementCoverage)
		self.assertEqual(0.0, module.BranchCoverage)

	@testcase("Aggregation")
	def Aggregation(self) -> None:
		"""
		A package's aggregated counts sum its own, its sub-packages' and its modules' counts.

		Fills a package, a sub-package and a module, and checks the aggregated counts and coverages.
		"""
		root = PackageCoverage("myPackage", Path("myPackage/__init__.py"))
		sub = PackageCoverage("sub", Path("myPackage/sub/__init__.py"), root)
		module = ModuleCoverage("Module", Path("myPackage/Module.py"), root)
		self._Fill(root, 2, 2, 0, 0)
		self._Fill(sub, 4, 2, 2, 1)
		self._Fill(module, 4, 4, 2, 0)

		self.assertEqual(10, root.AggregatedTotalStatements)
		self.assertEqual(8, root.AggregatedCoveredStatements)
		self.assertEqual(2, root.AggregatedMissingStatements)
		self.assertEqual(0, root.AggregatedExcludedStatements)
		self.assertEqual(0.8, root.AggregatedStatementCoverage)
		self.assertEqual(4, root.AggregatedTotalBranches)
		self.assertEqual(1, root.AggregatedCoveredBranches)
		self.assertEqual(1, root.AggregatedPartialBranches)
		self.assertEqual(2, root.AggregatedMissingBranches)
		self.assertEqual(0.5, root.AggregatedBranchCoverage)
