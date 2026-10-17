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
Unit tests for :mod:`pyTooling.Sphinx.Abbreviation`: an abbreviation's forms, and the domain's bookkeeping.
"""
from unittest.mock                 import MagicMock

from pyTooling.Sphinx.Abbreviation import AbbreviationDomain, AbbreviationEntry
from pyTooling.Testing             import Testcase, testsuite, testcase


if __name__ == "__main__":  # pragma: no cover
	print("ERROR: you called a testcase declaration file as an executable module.")
	print("Use: 'python -m unittest <testcase module>'")
	exit(1)


FSM = AbbreviationEntry("index", "abbreviation-FSM", "FSM", "finite-state machine", "FSMs", "finite-state machines")


@testsuite("Abbreviation forms")
class Forms(Testcase):
	"""The forms a role writes: short, long and full, each singular or plural."""

	@testcase("Singular")
	def Singular(self) -> None:
		"""
		The short, long and full form of the singular.

		Asks an entry for each form and checks the texts.
		"""
		self.assertEqual("FSM", FSM.Form("short", False))
		self.assertEqual("finite-state machine", FSM.Form("long", False))
		self.assertEqual("finite-state machine (FSM)", FSM.Form("full", False))

	@testcase("Plural")
	def Plural(self) -> None:
		"""
		The short, long and full form of the plural.

		Asks an entry for each plural form and checks the texts.
		"""
		self.assertEqual("FSMs", FSM.Form("short", True))
		self.assertEqual("finite-state machines", FSM.Form("long", True))
		self.assertEqual("finite-state machines (FSMs)", FSM.Form("full", True))


@testsuite("Abbreviation domain")
class Domain(Testcase):
	"""What the domain remembers per document, and what it takes over from a parallel reader."""

	def _domain(self) -> AbbreviationDomain:
		"""
		Create a domain with an empty data store, as Sphinx would for a new environment.

		:returns: The domain.
		"""
		environment = MagicMock()
		environment.domaindata = {}
		return AbbreviationDomain(environment)

	@testcase("Clear a document")
	def ClearDoc(self) -> None:
		"""
		Reading a document again forgets its abbreviations, not the others'.

		Registers abbreviations of two documents, clears one, and checks only the other's are left.
		"""
		domain = self._domain()
		domain.Register(FSM, MagicMock())
		domain.Register(FSM._replace(docName="other", short="HDL"), MagicMock())

		domain.clear_doc("index")

		self.assertEqual(["HDL"], list(domain.Abbreviations))

	@testcase("Merge a parallel reader's data")
	def Merge(self) -> None:
		"""
		A parallel reader's abbreviations are taken over for the documents it read.

		Merges data holding abbreviations of a read and an unread document, and checks only the read one's arrives.
		"""
		domain = self._domain()
		other = {"abbreviations": {"FSM": FSM, "HDL": FSM._replace(docName="unread", short="HDL")}}

		domain.merge_domaindata({"index"}, other)

		self.assertEqual({"FSM": FSM}, domain.Abbreviations)
