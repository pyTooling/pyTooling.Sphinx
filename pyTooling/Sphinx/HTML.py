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
Visitors writing pyTooling.Sphinx's nodes in HTML.

Each node has a ``visit_*`` and a ``depart_*`` function and a ``translate*`` pair of both, which
:data:`~pyTooling.Sphinx.NODES` registers.
"""
from docutils              import nodes
from sphinx.writers.html5  import HTML5Translator

from pyTooling.Decorators  import export
from pyTooling.Sphinx.Node import Abbreviation, Landscape, TreeDescription, TreeItem, TreeLabel, TreeSeparator
from pyTooling.Sphinx.Node import COVERAGE_STATES, CoverageListing, visitFunc, departFunc


__all__ = [
	"translateLandscape", "translateTreeItem", "translateTreeLabel", "translateTreeSeparator", "translateTreeDescription",
	"translateAbbreviation", "translateCoverageListing"
]


@export
def visit_TreeItem(translator: HTML5Translator, node: TreeItem) -> None:
	"""
	Open an entry in HTML: a list item, and a ``<details>`` element if the entry has children.

	The root of a tree with descriptions states the width of the column of the entries' texts, as CSS custom property
	``--pyTooling-tree-column``, which its descendants inherit.

	:param translator: The HTML translator writing the page.
	:param node:       The entry.
	"""
	if node["columnWidth"] is None:
		translator.body.append(translator.starttag(node, "li", ""))
	else:
		translator.body.append(
			translator.starttag(node, "li", "", style=f"--pyTooling-tree-column: {node['columnWidth']}")
		)

	if node["expanded"] is not None:
		translator.body.append("<details open>" if node["expanded"] else "<details>")


@export
def depart_TreeItem(translator: HTML5Translator, node: TreeItem) -> None:
	"""
	Close an entry in HTML.

	:param translator: The HTML translator writing the page.
	:param node:       The entry.
	"""
	if node["expanded"] is not None:
		translator.body.append("</details>")
	translator.body.append("</li>\n")


@export
def visit_TreeLabel(translator: HTML5Translator, node: TreeLabel) -> None:
	"""
	Open an entry's text in HTML, behind its icons.

	An entry with children opens a ``<summary>`` and writes both expander icons, the stylesheet showing one of them.
	Any other entry writes an empty expander instead, so its text is aligned with its siblings'. Icons are hidden from
	a screen reader.

	In a tree with descriptions, the text ends with a :class:`~pyTooling.Sphinx.Node.TreeDescription`: the entry is a
	row, whose first column holds the icons and the text, and whose second column the description. The row states the
	entry's level as CSS custom property ``--pyTooling-tree-depth``, from which the stylesheet computes how wide the
	first column is at this level.

	:param translator: The HTML translator writing the page.
	:param node:       The entry's text.
	"""
	if node["expandedIcon"] is not None:
		translator.body.append("<summary>")

	if isinstance(node.children[-1], TreeDescription):
		translator.body.append(
			f'<span class="tree-row" style="--pyTooling-tree-depth: {node["level"]}"><span class="tree-label">'
		)

	if node["expandedIcon"] is None:
		translator.body.append('<span class="tree-expander" aria-hidden="true"></span>')
	else:
		for state, stateIcon in (("expanded", node["expandedIcon"]), ("collapsed", node["collapsedIcon"])):
			translator.body.append(
				f'<span class="tree-expander tree-{state}" aria-hidden="true">{translator.encode(stateIcon)}</span>'
			)

	if node["icon"] != "":
		translator.body.append(f'<span class="tree-icon" aria-hidden="true">{translator.encode(node["icon"])}</span>')

	translator.body.append('<span class="tree-text">')


@export
def depart_TreeLabel(translator: HTML5Translator, node: TreeLabel) -> None:
	"""
	Close an entry's text in HTML - or its row, in a tree with descriptions -, and its ``<summary>`` if the entry has
	children.

	:param translator: The HTML translator writing the page.
	:param node:       The entry's text.
	"""
	translator.body.append("</span>")
	if node["expandedIcon"] is not None:
		translator.body.append("</summary>")


@export
def visit_TreeSeparator(translator: HTML5Translator, node: TreeSeparator) -> None:
	"""
	Skip the separator between an entry's text and its description in HTML, which draws the description in a column of
	its own.

	:param translator: The HTML translator writing the page.
	:param node:       The separator.
	:raises SkipNode:  Always, so neither the separator's text nor its depart function is written.
	"""
	raise nodes.SkipNode()


@export
def depart_TreeSeparator(translator: HTML5Translator, node: TreeSeparator) -> None:
	"""
	Close the separator between an entry's text and its description in HTML, which is never called:
	:func:`visit_TreeSeparator` skips the node.

	:param translator: The HTML translator writing the page.
	:param node:       The separator.
	"""


@export
def visit_TreeDescription(translator: HTML5Translator, node: TreeDescription) -> None:
	"""
	Open an entry's description in HTML: close the entry's text and the first column, and open the second column.

	An entry without a description has an empty one, so every row of a tree with descriptions has both columns.

	:param translator: The HTML translator writing the page.
	:param node:       The description.
	"""
	translator.body.append('</span></span><span class="tree-description">')


@export
def depart_TreeDescription(translator: HTML5Translator, node: TreeDescription) -> None:
	"""
	Close an entry's description in HTML.

	:param translator: The HTML translator writing the page.
	:param node:       The description.
	"""
	translator.body.append("</span>")


@export
def visit_Landscape(translator: HTML5Translator, node: Landscape) -> None:
	"""
	Open a landscape container in HTML, which writes nothing: a web page has no page orientation.

	:param translator: The HTML translator writing the page.
	:param node:       The landscape container.
	"""


@export
def depart_Landscape(translator: HTML5Translator, node: Landscape) -> None:
	"""
	Close a landscape container in HTML, which writes nothing.

	:param translator: The HTML translator writing the page.
	:param node:       The landscape container.
	"""


translateLandscape: tuple[visitFunc, departFunc] = (visit_Landscape, depart_Landscape)
"""Visit and depart function writing a :class:`~pyTooling.Sphinx.Node.Landscape` in HTML."""

translateTreeItem: tuple[visitFunc, departFunc] = (visit_TreeItem, depart_TreeItem)
"""Visit and depart function writing a :class:`~pyTooling.Sphinx.Node.TreeItem` in HTML."""

translateTreeLabel: tuple[visitFunc, departFunc] = (visit_TreeLabel, depart_TreeLabel)
"""Visit and depart function writing a :class:`~pyTooling.Sphinx.Node.TreeLabel` in HTML."""

translateTreeSeparator: tuple[visitFunc, departFunc] = (visit_TreeSeparator, depart_TreeSeparator)
"""Visit and depart function skipping a :class:`~pyTooling.Sphinx.Node.TreeSeparator` in HTML."""

translateTreeDescription: tuple[visitFunc, departFunc] = (visit_TreeDescription, depart_TreeDescription)
"""Visit and depart function writing a :class:`~pyTooling.Sphinx.Node.TreeDescription` in HTML."""


@export
def visit_Abbreviation(translator: HTML5Translator, node: Abbreviation) -> None:
	"""
	Open an abbreviation in HTML: an ``<abbr>`` element.

	:param translator: The HTML translator writing the page.
	:param node:       The abbreviation.
	"""
	translator.body.append(translator.starttag(node, "abbr", "", CLASS="pytooling-abbreviation"))


@export
def depart_Abbreviation(translator: HTML5Translator, node: Abbreviation) -> None:
	"""
	Close an abbreviation in HTML, behind the box the stylesheet shows on hover.

	The box shows the long form and, if the node carries one, the summary of the abbreviation's description. The short
	form is shown in front of the long form only if a title replaced it in the text.

	:param translator: The HTML translator writing the page.
	:param node:       The abbreviation.
	"""
	long = translator.encode(node["long"])
	short = "" if node.astext() == node["short"] else f'<strong>{translator.encode(node["short"])}</strong> '
	summary = node.get("summary", "")
	summary = f'<span class="pytooling-abbreviation-summary">{translator.encode(summary)}</span>' if summary != "" else ""
	translator.body.append(
		f'<span class="pytooling-abbreviation-box" role="tooltip">{short}{long}{summary}</span></abbr>'
	)


translateAbbreviation: tuple[visitFunc, departFunc] = (visit_Abbreviation, depart_Abbreviation)
"""Visit and depart function writing an :class:`~pyTooling.Sphinx.Node.Abbreviation` in HTML."""


@export
def visit_CoverageListing(translator: HTML5Translator, node: CoverageListing) -> None:
	"""
	Write a source file's code coverage in HTML, completely.

	A header shows the file's path and a legend of the coverage states. The listing is a ``<pre>`` in Sphinx'
	highlighting ``<div>``s, so Sphinx' Pygments stylesheet colors the tokens. Each line is a ``<span>`` with class
	``report-line`` and ``report-line-<state>``, holding its number, its hits - if the report has any - and its tokens.
	A line, which ran without taking all its branches, says on hover how many were taken. The node's text - the plain
	source - isn't written again.

	:param translator: The HTML translator writing the page.
	:param node:       The listing.
	:raises SkipNode:  Always, so the node's text isn't written again.
	"""
	withHits = any(hits is not None for _, _, hits, _, _, _ in node["lines"])

	lines: list[str] = []
	for number, status, hits, branches, coveredBranches, tokens in node["lines"]:
		classes = "report-line" if status == "" else f"report-line report-line-{status}"
		attributes = f' id="L{number}"' if node["anchors"] else ""
		if status == "partial":
			attributes += f' title="{coveredBranches} of {branches} branches taken"'

		hitsText = "" if hits is None else f"{hits}"
		gutter = f'<span class="linenos">{number}</span>'
		if withHits:
			gutter += f'<span class="linenos report-hits">{hitsText}</span>'

		code = "".join(
			translator.encode(text) if cssClass == "" else f'<span class="{cssClass}">{translator.encode(text)}</span>'
			for cssClass, text in tokens
		)
		lines.append(f'<span class="{classes}"{attributes}>{gutter}{code}\n</span>')

	classes = "highlight-default notranslate report-coverage-listing"
	legend = "".join(
		f'<span class="report-coverage-legend-{state or "none"}">{translator.encode(label)}</span>'
		for state, label in COVERAGE_STATES.items()
	)
	translator.body.append(translator.starttag(node, "div", "", CLASS=classes))
	translator.body.append(
		f'<div class="report-coverage-header"><span class="report-coverage-path">{translator.encode(node["path"])}</span>'
		f'<span class="report-coverage-legend">{legend}</span></div>'
	)
	translator.body.append('<div class="highlight"><pre>')
	translator.body.extend(lines)
	translator.body.append("</pre></div></div>\n")

	raise nodes.SkipNode


@export
def depart_CoverageListing(translator: HTML5Translator, node: CoverageListing) -> None:
	"""
	Close a source file's code coverage in HTML, which writes nothing: :func:`visit_CoverageListing` wrote it all.

	:param translator: The HTML translator writing the page.
	:param node:       The listing.
	"""


translateCoverageListing: tuple[visitFunc, departFunc] = (visit_CoverageListing, depart_CoverageListing)
"""Visit and depart function writing a :class:`~pyTooling.Sphinx.Node.CoverageListing` in HTML."""
