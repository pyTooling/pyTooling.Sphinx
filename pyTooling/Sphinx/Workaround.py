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
Workarounds for Sphinx and docutils problems.
"""
from typing                            import Any

from docutils.nodes                    import table
from sphinx.transforms.post_transforms import SphinxPostTransform
from sphinx.util.logging               import getLogger

from pyTooling.Decorators              import export


@export
class FixLatexTableWidths(SphinxPostTransform):
	"""
	A post-transform giving the report tables in LaTeX the column widths their directives state.

	Without class ``colwidths-given``, Sphinx' LaTeX writer computes the widths itself and ignores the ones the table's
	column specifications state, which squeezes a wide table - such as a unit test or code coverage report - into the
	page.
	"""

	default_priority = 500                                                    #: Priority among the post-transforms.
	formats =          ("latex", )                                            #: Output formats the transform runs for.
	tableClasses =     ("report-unittest-table", "report-codecov-table")  #: CSS classes of the tables it fixes.

	def run(self, **kwargs: Any) -> None:
		"""
		Add class ``colwidths-given`` to every report table that hasn't it yet.

		:param kwargs: Keyword arguments Sphinx passes to a post-transform; none is used.
		"""
		for tableNode in self.document.findall(table):
			if (cssClasses := tableNode.get("classes", None)) is None:
				continue

			if any(tableClass in cssClasses for tableClass in self.tableClasses):
				if "colwidths-given" not in cssClasses:
					cssClasses.append("colwidths-given")

					getLogger(__name__).info(
						"Applied 'colwidths-given' to a table via FixLatexTableWidths transform.", location=tableNode
					)
