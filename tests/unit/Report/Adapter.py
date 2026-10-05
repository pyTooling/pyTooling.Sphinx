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
Unit tests for :mod:`pyTooling.Sphinx.Report.Adapter.Coverage`: reading Coverage.py's JSON report into the data model.
"""
from json                                     import dump
from pathlib                                  import Path
from tempfile                                 import TemporaryDirectory

from pyTooling.Sphinx.Report.Adapter.Coverage import Analyzer, CodeCoverageError
from pyTooling.Testing                        import Testcase, testsuite, testcase


if __name__ == "__main__":  # pragma: no cover
	print("ERROR: you called a testcase declaration file as an executable module.")
	print("Use: 'python -m unittest <testcase module>'")
	exit(1)


REPORT = Path(__file__).parent.parent.parent / "data" / "Report" / "coverage.json"
"""A report of package 'myPackage': '__init__.py', and module 'Module' in sub-package 'sub'."""


@testsuite("Code coverage adapter")
class CoverageAdapter(Testcase):
	"""Reading a JSON report of Coverage.py, format version 3."""

	@testcase("Conversion")
	def Conversion(self) -> None:
		"""
		The report's files become a package hierarchy with the reported counts.

		Converts the fixture and checks the root package's counts, the sub-package and its module.
		"""
		analyzer = Analyzer("myPackage", REPORT)
		root = analyzer.Convert()

		self.assertEqual("myPackage", analyzer.PackageName)
		self.assertEqual("myPackage", root.Name)
		self.assertEqual(4, root.TotalStatements)
		self.assertEqual(3, root.CoveredStatements)
		self.assertEqual(["sub"], list(root.Packages))
		sub = root.Packages["sub"]
		self.assertEqual(1, sub.TotalStatements)
		self.assertEqual(["Module"], list(sub.Modules))
		module = sub.Modules["Module"]
		self.assertEqual(6, module.TotalStatements)
		self.assertEqual(4, module.TotalBranches)
		self.assertEqual(1, module.PartialBranches)
		self.assertAlmostEqual(0.4, module.Coverage)
		self.assertEqual(11, root.AggregatedTotalStatements)
		self.assertEqual(3, root.FileCount)

	@testcase("Missing report")
	def MissingFile(self) -> None:
		"""
		A report file that doesn't exist is rejected.

		Creates an analyzer for a missing file and checks the CodeCoverageError's message.
		"""
		with self.assertRaises(CodeCoverageError) as context:
			Analyzer("myPackage", Path("missing.json"))

		self.assertEqual("JSON coverage report 'missing.json' not found.", str(context.exception))

	@testcase("Unsupported format")
	def UnsupportedFormat(self) -> None:
		"""
		A report in another format version than 3 is rejected.

		Converts a report of format version 2 and checks the CodeCoverageError's message.
		"""
		with TemporaryDirectory() as directory:
			report = Path(directory) / "coverage.json"
			with report.open("w", encoding="utf-8") as file:
				dump({"meta": {"format": 2}, "files": {}}, file)

			with self.assertRaises(CodeCoverageError) as context:
				Analyzer("myPackage", report).Convert()

		self.assertEqual("Unsupported coverage format version '2'", str(context.exception))
