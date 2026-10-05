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
Unit tests for :mod:`pyTooling.Sphinx.Report.CodeCoverage`: checking the configuration values and the coverage levels.
"""
from pathlib                              import Path

from pyTooling.Sphinx.Report              import ReportExtensionError
from pyTooling.Sphinx.Report.CodeCoverage import CONFIG_PREFIX, CodeCoverageBase
from pyTooling.Testing                    import Testcase, testsuite, testcase


if __name__ == "__main__":  # pragma: no cover
	print("ERROR: you called a testcase declaration file as an executable module.")
	print("Use: 'python -m unittest <testcase module>'")
	exit(1)


REPORT = Path(__file__).parent.parent.parent / "data" / "Report" / "coverage.json"
"""A report of package 'myPackage'."""


class ConfigurationTestcase(Testcase):
	"""Base-class of the testcases: the configuration read by a previous testcase is discarded."""

	def setUp(self) -> None:
		CodeCoverageBase._coverageLevelDefinitions.clear()
		CodeCoverageBase._packageConfigurations.clear()

	def tearDown(self) -> None:
		CodeCoverageBase._coverageLevelDefinitions.clear()
		CodeCoverageBase._packageConfigurations.clear()

	@staticmethod
	def _Configuration(**packages: dict[str, object]) -> dict[str, object]:
		"""
		Build a configuration with the default palette and the given packages.

		:param packages: The package configurations, by report ID.
		:returns:        The configuration, keyed by the configuration values' names.
		"""
		return {
			f"{CONFIG_PREFIX}_Levels":   CodeCoverageBase.defaultCoverageDefinitions,
			f"{CONFIG_PREFIX}_Packages": packages,
		}


@testsuite("Code coverage configuration")
class Configuration(ConfigurationTestcase):
	"""Reading 'pyTooling_CodeCoverage_Levels' and 'pyTooling_CodeCoverage_Packages'."""

	@testcase("Configuration value names")
	def Names(self) -> None:
		"""
		The configuration values carry the prefix 'pyTooling_CodeCoverage'.

		Checks the prefix and the names in 'configValues'.
		"""
		self.assertEqual("pyTooling_CodeCoverage", CONFIG_PREFIX)
		self.assertEqual({"Packages", "Levels"}, set(CodeCoverageBase.configValues))

	@testcase("Valid package")
	def Package(self) -> None:
		"""
		A package naming the default palette is loaded with that palette, and 'fail_below' as a fraction.

		Checks the configuration of a package reading the fixture report.
		"""
		CodeCoverageBase.CheckConfiguration(None, self._Configuration(
			src={"name": "myPackage", "json_report": str(REPORT), "fail_below": 80, "levels": "default"}
		))

		package = CodeCoverageBase._packageConfigurations["src"]
		self.assertEqual("myPackage", package["name"])
		self.assertEqual(REPORT, package["json_report"])
		self.assertEqual(0.8, package["fail_below"])
		self.assertEqual("report-cov-below100", package["levels"][100]["class"])

	@testcase("Missing report file")
	def MissingReport(self) -> None:
		"""
		A report file that doesn't exist is rejected.

		Checks the ReportExtensionError's message names the configuration value, the report ID and the file.
		"""
		with self.assertRaises(ReportExtensionError) as context:
			CodeCoverageBase.CheckConfiguration(None, self._Configuration(
				src={"name": "myPackage", "json_report": "missing.json", "fail_below": 80, "levels": "default"}
			))

		self.assertEqual(
			"conf.py: pyTooling_CodeCoverage_Packages:[src].json_report: Coverage report file 'missing.json' doesn't exist.",
			str(context.exception)
		)

	@testcase("Missing field")
	def MissingField(self) -> None:
		"""
		A package configuration without 'name' is rejected.

		Checks the ReportExtensionError's message.
		"""
		with self.assertRaises(ReportExtensionError) as context:
			CodeCoverageBase.CheckConfiguration(None, self._Configuration(src={"json_report": str(REPORT)}))

		self.assertEqual(
			"conf.py: pyTooling_CodeCoverage_Packages:[src].name: Configuration is missing.", str(context.exception)
		)

	@testcase("Undefined palette")
	def UndefinedPalette(self) -> None:
		"""
		A package naming a palette that isn't defined is rejected.

		Checks a ReportExtensionError is raised.
		"""
		with self.assertRaises(ReportExtensionError):
			CodeCoverageBase.CheckConfiguration(None, self._Configuration(
				src={"name": "myPackage", "json_report": str(REPORT), "fail_below": 80, "levels": "unknown"}
			))

	@testcase("Wrong type of levels")
	def LevelsType(self) -> None:
		"""
		Levels that are neither a palette's name nor a dictionary are rejected, with a note naming the type.

		Checks the ReportExtensionError's message and note.
		"""
		with self.assertRaises(ReportExtensionError) as context:
			CodeCoverageBase.CheckConfiguration(None, self._Configuration(
				src={"name": "myPackage", "json_report": str(REPORT), "fail_below": 80, "levels": 5}
			))

		self.assertEqual(
			"conf.py: pyTooling_CodeCoverage_Packages:[src].levels: Is neither a palette's name nor a dictionary.",
			str(context.exception)
		)
		self.assertEqual(["Got type 'int'."], context.exception.__notes__)

	@testcase("Palette without level 100")
	def PaletteWithoutMaximum(self) -> None:
		"""
		A palette without level 100 is rejected.

		Checks the ReportExtensionError's message.
		"""
		with self.assertRaises(ReportExtensionError) as context:
			CodeCoverageBase.CheckConfiguration(None, {
				f"{CONFIG_PREFIX}_Levels":   {"mine": {"error": {"class": "c", "desc": "d"}}},
				f"{CONFIG_PREFIX}_Packages": {},
			})

		self.assertEqual(
			"conf.py: pyTooling_CodeCoverage_Levels:[mine][100]: Configuration is missing.", str(context.exception)
		)


@testsuite("Code coverage levels")
class Levels(ConfigurationTestcase):
	"""Looking up the level a coverage falls into."""

	@testcase("Color of a coverage")
	def ConvertToColor(self) -> None:
		"""
		A coverage selects the first level whose limit is above it; a negative coverage selects 'error'.

		Checks the CSS classes for 0 %, 49.9 %, 50 %, 100 % and -1.
		"""
		directive = CodeCoverageBase.__new__(CodeCoverageBase)
		directive._levels = CodeCoverageBase.defaultCoverageDefinitions["default"]

		for coverage, cssClass in (
			(0.0,   "report-cov-below10"),
			(0.499, "report-cov-below50"),
			(0.5,   "report-cov-below60"),
			(1.0,   "report-cov-below100"),
			(-1.0,  "report-cov-error"),
		):
			with self.subTest(coverage=coverage):
				self.assertEqual(cssClass, directive._ConvertToColor(coverage, "class"))
