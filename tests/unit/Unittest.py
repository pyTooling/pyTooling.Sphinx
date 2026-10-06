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
Unit tests for :mod:`pyTooling.Sphinx.Unittest`: which testcases are listed, and how a runtime is written.
"""
from datetime                  import timedelta

from pyEDAA.Reports            import Unittesting
from pyTooling.Sphinx.Unittest import CONFIG_PREFIX, ShowTestcases, UnittestSummary
from pyTooling.Testing         import Testcase, testsuite, testcase


if __name__ == "__main__":  # pragma: no cover
	print("ERROR: you called a testcase declaration file as an executable module.")
	print("Use: 'python -m unittest <testcase module>'")
	exit(1)


@testsuite("Listed testcases")
class ListedTestcases(Testcase):
	"""Option ':show-testcases:' as the flag 'ShowTestcases', compared with a testcase's status."""

	@testcase("All")
	def All(self) -> None:
		"""
		'all' includes the statuses a summary distinguishes, and not 'Unknown'.

		Compares 'all' with 'Passed', 'Failed', 'Skipped', 'Excluded', 'Errored', 'SetupError', 'Aborted' and 'Unknown'.
		"""
		status = Unittesting.TestcaseStatus
		for included in (
			status.Passed, status.Failed, status.Skipped, status.Excluded, status.Errored, status.SetupError, status.Aborted
		):
			with self.subTest(status=included):
				self.assertTrue(ShowTestcases.all == included)

		self.assertFalse(ShowTestcases.all == status.Unknown)

	@testcase("Not passed")
	def NotPassed(self) -> None:
		"""
		'not_passed' includes a failed testcase, but not a passed one.

		Compares 'not_passed' with 'Passed', 'Failed', 'Errored' and 'SetupError'.
		"""
		self.assertFalse(ShowTestcases.not_passed == Unittesting.TestcaseStatus.Passed)
		self.assertTrue(ShowTestcases.not_passed == Unittesting.TestcaseStatus.Failed)
		self.assertTrue(ShowTestcases.not_passed == Unittesting.TestcaseStatus.Errored)
		self.assertTrue(ShowTestcases.not_passed == Unittesting.TestcaseStatus.SetupError)

	@testcase("Other types")
	def OtherTypes(self) -> None:
		"""
		A member doesn't compare equal to anything but a testcase status.

		Compares 'all' with a testsuite status and a string.
		"""
		self.assertFalse(ShowTestcases.all == Unittesting.TestsuiteStatus.Passed)
		self.assertFalse(ShowTestcases.all == "passed")


@testsuite("Unit test summary")
class Summary(Testcase):
	"""The directive's configuration value, runtimes and symbols."""

	@testcase("Configuration value name")
	def Names(self) -> None:
		"""
		The configuration value is 'pyTooling_Unittest_Testsuites'.

		Checks the prefix and the name in 'configValues'.
		"""
		self.assertEqual("pyTooling_Unittest", CONFIG_PREFIX)
		self.assertEqual({"Testsuites"}, set(UnittestSummary.configValues))

	@testcase("Runtime")
	def FormatTimedelta(self) -> None:
		"""
		A runtime is written as 'HH:MM:SS.sss', rounded to milliseconds; no runtime is written as an empty string.

		Formats 1 h 2 min 3.4567 s, and None.
		"""
		directive = UnittestSummary.__new__(UnittestSummary)

		self.assertEqual(
			"01:02:03.457", directive._FormatTimedelta(timedelta(hours=1, minutes=2, seconds=3, microseconds=456_700))
		)
		self.assertEqual("", directive._FormatTimedelta(None))

	@testcase("Status symbols")
	def Symbols(self) -> None:
		"""
		A passed testcase or testsuite is shown as ✅ and a failed one as ❌.

		Converts 'Passed' and 'Failed' of both enumerations.
		"""
		directive = UnittestSummary.__new__(UnittestSummary)

		self.assertEqual("✅", directive._ConvertTestcaseStatusToSymbol(Unittesting.TestcaseStatus.Passed))
		self.assertEqual("❌", directive._ConvertTestcaseStatusToSymbol(Unittesting.TestcaseStatus.Failed))
		self.assertEqual("✅", directive._ConvertTestsuiteStatusToSymbol(Unittesting.TestsuiteStatus.Passed))
		self.assertEqual("❌", directive._ConvertTestsuiteStatusToSymbol(Unittesting.TestsuiteStatus.Failed))
