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
from sphinx.writers.html5  import HTML5Translator

from pyTooling.Decorators  import export
from pyTooling.Sphinx.Node import Abbreviation, Landscape, TreeItem, TreeLabel, visitFunc, departFunc


__all__ = ["translateLandscape", "translateTreeItem", "translateTreeLabel", "translateAbbreviation"]


@export
def visit_TreeItem(translator: HTML5Translator, node: TreeItem) -> None:
	"""
	Open an entry in HTML: a list item, and a ``<details>`` element if the entry has children.

	:param translator: The HTML translator writing the page.
	:param node:       The entry.
	"""
	translator.body.append(translator.starttag(node, "li", ""))
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

	:param translator: The HTML translator writing the page.
	:param node:       The entry's text.
	"""
	if node["expandedIcon"] is None:
		translator.body.append('<span class="tree-expander" aria-hidden="true"></span>')
	else:
		translator.body.append("<summary>")
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
	Close an entry's text in HTML, and its ``<summary>`` if the entry has children.

	:param translator: The HTML translator writing the page.
	:param node:       The entry's text.
	"""
	translator.body.append("</span>")
	if node["expandedIcon"] is not None:
		translator.body.append("</summary>")


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
