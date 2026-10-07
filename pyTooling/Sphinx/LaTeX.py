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
from textwrap                  import dedent

from docutils                  import nodes
from pygments.formatters.latex import escape_tex
from sphinx.writers.latex      import LaTeXTranslator

from pyTooling.Decorators      import export
from pyTooling.Sphinx.Node     import CoverageListing, Landscape, visitFunc, departFunc


__all__ = ["translateLandscape", "translateCoverageListing", "COVERAGE_MARKERS", "TAB_WIDTH"]

#: Per coverage state of a line, the color of its number - an ``xcolor`` expression - and the marker behind it.
COVERAGE_MARKERS = {
	"covered":   ("green!50!black", "+"),
	"partial":   ("orange",         "~"),
	"uncovered": ("red",            "-"),
	"excluded":  ("gray",           "x"),
	"":          ("gray",           " "),
}

TAB_WIDTH = 4  #: Number of columns a tab advances to, as LaTeX doesn't expand tabs in a listing.


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


@export
def visit_CoverageListing(translator: LaTeXTranslator, node: CoverageListing) -> None:
	"""
	Write a source file's code coverage in LaTeX, completely.

	The listing is a ``sphinxVerbatim`` environment with the tokens written as Sphinx writes highlighted code -
	``\\PYG{<class>}{<text>}`` -, so the configured Pygments style colors them. Each line starts with its number,
	colored by its coverage state, and a marker of :data:`COVERAGE_MARKERS`. Tabs are expanded to :data:`TAB_WIDTH`
	columns. The node's text - the plain source - isn't written again.

	:param translator: The LaTeX translator writing the document.
	:param node:       The listing.
	:raises SkipNode:  Always, so the node's text isn't written again.
	"""
	width = len(str(max((number for number, *_ in node["lines"]), default=1)))

	lines: list[str] = []
	for number, status, _, _, _, tokens in node["lines"]:
		color, marker = COVERAGE_MARKERS[status]
		code: list[str] = []
		column = 0
		for cssClass, text in tokens:
			if "\t" in text:
				padding = column % TAB_WIDTH
				text = (" " * padding + text).expandtabs(TAB_WIDTH)[padding:]
			column += len(text)

			escaped = escape_tex(text, "PYG")
			code.append(escaped if cssClass == "" else f"\\PYG{{{cssClass}}}{{{escaped}}}")

		lines.append(f"\\textcolor{{{color}}}{{{number:>{width}} {marker}}} {''.join(code)}")

	translator.body.append("\n\\begin{sphinxVerbatim}[commandchars=\\\\\\{\\}]\n")
	translator.body.append("\n".join(lines))
	translator.body.append("\n\\end{sphinxVerbatim}\n")

	raise nodes.SkipNode


@export
def depart_CoverageListing(translator: LaTeXTranslator, node: CoverageListing) -> None:
	"""
	Close a source file's code coverage in LaTeX, which writes nothing: :func:`visit_CoverageListing` wrote it all.

	:param translator: The LaTeX translator writing the document.
	:param node:       The listing.
	"""


translateCoverageListing: tuple[visitFunc, departFunc] = (visit_CoverageListing, depart_CoverageListing)
"""Visit and depart function writing a :class:`~pyTooling.Sphinx.Node.CoverageListing` in LaTeX."""
