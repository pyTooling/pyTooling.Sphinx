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
Visitors writing pyTooling.Sphinx's nodes in LaTeX.

Each node has a ``visit_*`` and a ``depart_*`` function and a ``translate*`` pair of both, which
:data:`~pyTooling.Sphinx.NODES` registers. A node without visitors here is written by the visitors of its base-class.
"""
from textwrap              import dedent

from sphinx.writers.latex  import LaTeXTranslator

from pyTooling.Decorators  import export
from pyTooling.Sphinx.Node import Landscape, visitFunc, departFunc


__all__ = ["translateLandscape"]


@export
def visit_Landscape(translator: LaTeXTranslator, node: Landscape) -> None:
	"""
	Open a landscape container in LaTeX: a ``landscape`` environment, which starts a new page in landscape orientation.

	:param translator: The LaTeX translator writing the document.
	:param node:       The landscape container.
	"""
	translator.body.append(dedent("""
		\\begin{landscape}
		""")
	)


@export
def depart_Landscape(translator: LaTeXTranslator, node: Landscape) -> None:
	"""
	Close a landscape container in LaTeX: the end of the ``landscape`` environment, which returns to portrait pages.

	:param translator: The LaTeX translator writing the document.
	:param node:       The landscape container.
	"""
	translator.body.append(dedent("""
		\\end{landscape}
		""")
	)


translateLandscape: tuple[visitFunc, departFunc] = (visit_Landscape, depart_Landscape)
"""Visit and depart function writing a :class:`~pyTooling.Sphinx.Node.Landscape` in LaTeX."""
