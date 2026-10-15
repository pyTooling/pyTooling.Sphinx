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
A translator of Markdown tokens - and of the raw HTML in between - into docutils nodes.

:class:`MarkdownTranslator` translates the tokens markdown-it-py parses into the nodes a directive returns, for a
:class:`~pyTooling.Sphinx.GitHubMarkdown.GitHubMarkdown` converter, which links GitHub's references in the text.

.. rubric:: Headings

A heading must not change the sections of the page the Markdown is put into. A heading becomes a
:class:`~docutils.nodes.topic`, titled by the heading and holding what follows, up to the next heading of the same or a
higher level; a deeper heading inside the topic becomes a :class:`~docutils.nodes.rubric`, as does a heading inside a
list or block quote.

.. rubric:: Alerts

A GitHub alert - ``> [!NOTE]`` - becomes the admonition of its kind (see :data:`ALERTS`), whose title the writer
writes.

.. rubric:: Raw HTML

Markdown may hold HTML, which :class:`RawHTMLParser` reads. The elements with a docutils counterpart are translated
(see :data:`HTML_ELEMENTS`), e.g. ``<ul>``, ``<strong>``, ``<a href>`` or ``<details>``, and ``<br>``, ``<img>`` and
``<hr>``; an element without one is reported by a warning of type ``github`` and subtype ``markdown``, and its content
is kept as if the element wasn't there. A comment is skipped, as GitHub doesn't show it either.

.. rubric:: Nodes of their own

Task list checkboxes and line breaks are nodes of their own (:class:`~pyTooling.Sphinx.Node.TaskListCheckbox`,
:class:`~pyTooling.Sphinx.Node.LineBreak`), which every format writes in its own way. A horizontal rule is written as
the ``|hr|`` substitution writes it, as docutils allows a transition only between sections' body elements.
"""
from __future__                        import annotations

from html.parser                       import HTMLParser
from re                                import compile as re_compile
from typing                            import TYPE_CHECKING, Optional as Nullable

from docutils                          import nodes
from sphinx.util.logging               import getLogger

from pyTooling.Decorators              import export
from pyTooling.MetaClasses             import ExtendedType
from pyTooling.Sphinx.Node             import LineBreak, TaskListCheckbox
from pyTooling.Sphinx.Roles            import BREAK_ROLES

if TYPE_CHECKING:  # pragma: no cover
	from markdown_it.token               import Token

	from pyTooling.Sphinx.GitHubMarkdown import GitHubMarkdown


__all__ = ["IMAGE_CLASS", "ALERTS", "HTML_ELEMENTS"]

#: The CSS class of every image the translator writes, by which
#: :class:`~pyTooling.Sphinx.GitHubMarkdown.ReplaceSVGImages` finds them.
IMAGE_CLASS = "github-image"

#: The admonition each kind of GitHub alert becomes, by the kind as written: ``> [!NOTE]``.
ALERTS: dict[str, type[nodes.Admonition]] = {
	"NOTE":      nodes.note,
	"TIP":       nodes.tip,
	"IMPORTANT": nodes.important,
	"WARNING":   nodes.warning,
	"CAUTION":   nodes.caution,
}

#: The HTML elements with a docutils counterpart: the node class, and the CSS classes it gets. An element mapped to
#: ``None`` is transparent: its content is kept, the element has no node of its own.
HTML_ELEMENTS: dict[str, tuple[Nullable[type[nodes.Element]], tuple[str, ...]]] = {
	"p":          (nodes.paragraph,       ()),
	"ul":         (nodes.bullet_list,     ()),
	"ol":         (nodes.enumerated_list, ()),
	"li":         (nodes.list_item,       ()),
	"blockquote": (nodes.block_quote,     ()),
	"pre":        (nodes.literal_block,   ()),
	"details":    (nodes.container,       ("github-details", )),
	"summary":    (nodes.rubric,          ("github-summary", )),
	"h1":         (nodes.rubric,          ("github-heading", )),
	"h2":         (nodes.rubric,          ("github-heading", )),
	"h3":         (nodes.rubric,          ("github-heading", )),
	"h4":         (nodes.rubric,          ("github-heading", )),
	"h5":         (nodes.rubric,          ("github-heading", )),
	"h6":         (nodes.rubric,          ("github-heading", )),
	"strong":     (nodes.strong,          ()),
	"b":          (nodes.strong,          ()),
	"em":         (nodes.emphasis,        ()),
	"i":          (nodes.emphasis,        ()),
	"code":       (nodes.literal,         ()),
	"tt":         (nodes.literal,         ()),
	"kbd":        (nodes.literal,         ("kbd", )),
	"sub":        (nodes.subscript,       ()),
	"sup":        (nodes.superscript,     ()),
	"del":        (nodes.inline,          ("strike", )),
	"s":          (nodes.inline,          ("strike", )),
	"strike":     (nodes.inline,          ("strike", )),
	"ins":        (nodes.inline,          ("underline", )),
	"u":          (nodes.inline,          ("underline", )),
	"a":          (nodes.reference,       ()),
	"div":        (None,                  ()),
	"span":       (None,                  ()),
}

_WHITESPACE = re_compile(r"\s+")
"""A run of whitespace, which HTML writes as one space."""


@export
class MarkdownTranslator(metaclass=ExtendedType, slots=True):
	"""
	A translator of Markdown tokens - and the raw HTML in between - into docutils nodes: a stack of the nodes still
	open, which a token or an HTML element opens or closes.

	Markdown's tokens nest; raw HTML may not: an element may stay open across tokens, e.g. ``<details>``, or never be
	closed, e.g. ``<li>``. An HTML element closes only nodes opened after the innermost open token's node, and every
	node a closing token opened later. Text directly in a list item, a table cell or a block quote - which HTML allows,
	docutils not - is put into a paragraph.

	:meth:`Translate` translates the tokens of one Markdown document; a translator is used once.
	"""

	_converter:  GitHubMarkdown                                   #: The converter, which links GitHub's references.
	_document:   nodes.document                                   #: The document the nodes are put into.
	_location:   Nullable[str]                                    #: Location the warnings are reported at.
	_root:       nodes.container                                  #: The container collecting the nodes.
	_stack:      list[nodes.Element]                              #: The open nodes, :attr:`_root` first.
	_floors:     list[int]                                        #: Per node a token opened, the stack's length.
	_closers:    list[int]                                        #: Per open token, the number of nodes it opened.
	_implicit:   list[nodes.paragraph]                            #: The open paragraphs nobody wrote.
	_html:       list[tuple[str, Nullable[nodes.Element], int]]   #: Per HTML element: tag, node, stack index.
	_topic:      Nullable[nodes.topic]                            #: The open topic, if any.
	_topicLevel: int                                              #: The level of the topic's heading.
	_checkbox:   Nullable[TaskListCheckbox]                       #: A task's checkbox, until its paragraph.
	_footnotes:  dict[int, nodes.footnote]                        #: The footnotes by the parser's number.
	_line:       int                                              #: The Markdown line of the last block token.
	_warned:     set[str]                                         #: The HTML elements warned about.

	def __init__(self, converter: GitHubMarkdown, document: nodes.document, location: Nullable[str]) -> None:
		"""
		Initializes a translator for one Markdown document.

		:param converter: The converter, which links GitHub's references.
		:param document:  The document the nodes are put into.
		:param location:  Location the warnings are reported at.
		"""
		self._converter =  converter
		self._document =   document
		self._location =   location
		self._root =       nodes.container()
		self._stack =      [self._root]
		self._floors =     []
		self._closers =    []
		self._implicit =   []
		self._html =       []
		self._topic =      None
		self._topicLevel = 0
		self._checkbox =   None
		self._footnotes =  {}
		self._line =       0
		self._warned =     set()

	def Translate(self, tokens: list[Token]) -> list[nodes.Node]:
		"""
		Translate the tokens of a Markdown document.

		An alert's title is skipped: it is the alert's kind, which the admonition's writer writes as title.

		:param tokens: The tokens of the block level, as ``MarkdownIt.parse()`` returns them.
		:returns:      The nodes.
		"""
		iterator = iter(tokens)
		for token in iterator:
			if token.map is not None:
				self._line = token.map[0] + 1

			if token.type == "alert_title_open":
				for titleToken in iterator:
					if titleToken.type == "alert_title_close":
						break

				continue

			self._TranslateToken(token)

		while len(self._stack) > 1:
			self._Pop()

		return list(self._root.children)

	def _TranslateToken(self, token: Token) -> None:
		"""
		Translate a token: open a node for an opening token, close the nodes for a closing one, or write a node.

		:param token: The token.
		"""
		if token.nesting == -1:
			match token.type:
				case "list_item_close" if self._checkbox is not None:
					self._InlineTarget()
				case "table_close":
					tableGroup = self._stack[self._floors[-1] - 1]
					columnCount = max(len(row) for row in tableGroup.findall(nodes.row))
					tableGroup["cols"] = columnCount
					for _ in range(columnCount):
						tableGroup.insert(0, nodes.colspec(colwidth=1))

			for _ in range(self._closers.pop()):
				self._Close()

			return

		opened = 0
		match token.type:
			case "inline":
				for child in token.children:
					self._TranslateToken(child)
			case "text":
				self._AppendText(token.content, html=False)
			case "text_special":
				self._InlineTarget().append(nodes.Text(token.content))
			case "softbreak" if not self._converter.LineBreaks:
				self._InlineTarget().append(nodes.Text("\n"))
			case "softbreak" | "hardbreak":
				self._InlineTarget().append(LineBreak("\n", "\n"))
			case "code_inline":
				self._InlineTarget().append(nodes.literal(token.content, token.content))
			case "em_open":
				opened = self._Open(nodes.emphasis(), inline=True)
			case "strong_open":
				opened = self._Open(nodes.strong(), inline=True)
			case "s_open":
				opened = self._Open(nodes.inline(classes=["strike"]), inline=True)
			case "link_open":
				opened = self._Open(nodes.reference(refuri=token.attrs["href"]), inline=True)
			case "image":
				alternative = "".join(child.content for child in token.children)
				self._InlineTarget().append(nodes.image(uri=token.attrs["src"], alt=alternative, classes=[IMAGE_CLASS]))
			case "html_inline" | "html_block":
				parser = RawHTMLParser(self)
				parser.feed(token.content)
				parser.close()
			case "footnote_ref":
				self._InlineTarget().append(self._FootnoteReference(token.meta["id"]))
			case "footnote_block_open" if self._topic is not None:
				self._CloseTopic()
			case "footnote_block_open" | "footnote_block_close" | "footnote_anchor":
				pass  # a footnote is a node of its own, which links back to its references
			case "paragraph_open":
				opened = self._Open(nodes.paragraph(), inline=False)
			case "heading_open":
				opened = self._OpenHeading(int(token.tag[1:]))
			case "bullet_list_open":
				bulletList = nodes.bullet_list(bullet=token.markup)
				if "contains-task-list" in str(token.attrs.get("class", "")):
					bulletList["classes"].append("github-task-list")
				opened = self._Open(bulletList, inline=False)
			case "ordered_list_open":
				enumeratedList = nodes.enumerated_list(enumtype="arabic", prefix="", suffix=token.markup)
				if (start := int(token.attrs.get("start", 1))) != 1:
					enumeratedList["start"] = start
				opened = self._Open(enumeratedList, inline=False)
			case "list_item_open":
				item = nodes.list_item()
				if "checked" in token.meta:
					item["classes"].append("github-task-list-item")
					symbol = "\u2611" if token.meta["checked"] else "\u2610"
					self._checkbox = TaskListCheckbox(symbol, symbol, checked=token.meta["checked"])
				opened = self._Open(item, inline=False)
			case "blockquote_open":
				opened = self._Open(nodes.block_quote(), inline=False)
			case "alert_open":
				opened = self._Open(ALERTS[token.meta["kind"]](classes=["github-alert"]), inline=False)
			case "hr":
				if (target := self._BlockTarget()) is not None:
					target.extend(nodes.raw("", written, format=writer) for writer, written in BREAK_ROLES["hr"].items())
			case "fence" | "code_block":
				language = token.info.split()[0] if token.info.strip() != "" else "text"
				code = token.content.rstrip("\n")
				if (target := self._BlockTarget()) is not None:
					target.append(nodes.literal_block(code, code, language=language))
			case "table_open":
				opened = self._Open(nodes.table(classes=["github-table"]), inline=False)
				opened += self._Open(nodes.tgroup(), inline=False)
			case "thead_open":
				opened = self._Open(nodes.thead(), inline=False)
			case "tbody_open":
				opened = self._Open(nodes.tbody(), inline=False)
			case "tr_open":
				opened = self._Open(nodes.row(), inline=False)
			case "th_open" | "td_open":
				entry = nodes.entry()
				if (style := str(token.attrs.get("style", ""))).startswith("text-align:"):
					entry["classes"].append(f"github-align-{style.removeprefix('text-align:')}")
				opened = self._Open(entry, inline=False)
			case "footnote_open":
				opened = self._Open(self._Footnote(token.meta["id"]), inline=False)
			case _:
				self._Warn(f"Markdown token '{token.type}' not supported; content kept as text.")
				if token.content != "":
					self._AppendText(token.content, html=False)

		if token.nesting == 1:
			self._closers.append(opened)

	def _Open(self, node: nodes.Element, inline: bool) -> int:
		"""
		Put a node a token opens into the innermost open node, and open it.

		:param node:   The node.
		:param inline: Whether the node is inline - put into a paragraph - or a body element.
		:returns:      The number of nodes opened, ``1``; ``0`` if a body element can't be put into the innermost node.
		"""
		if inline:
			target = self._InlineTarget()
		elif (target := self._BlockTarget()) is None:
			self._Warn(f"'{node.tagname}' not supported inside '{self._stack[-1].tagname}'; content kept.")
			return 0

		self._Push(target, node)
		self._floors.append(len(self._stack))
		return 1

	def _Push(self, target: nodes.Element, node: nodes.Element) -> None:
		"""
		Put a node into a target node, and open it.

		A task list item's checkbox is put into the item's first paragraph.

		:param target: The node the node is put into.
		:param node:   The node.
		"""
		target += node
		self._stack.append(node)

		if self._checkbox is not None and isinstance(node, nodes.paragraph):
			node += self._checkbox
			node += nodes.Text(" ")
			self._checkbox = None

	def _Close(self) -> None:
		"""
		Close the node opened last by a token, and every node opened after it.
		"""
		floor = self._floors.pop()
		while len(self._stack) >= floor:
			self._Pop()

	def _Pop(self) -> None:
		"""
		Close the innermost open node, and forget the HTML elements opened inside it.

		A paragraph loses the whitespace at both ends, which raw HTML leaves, and is removed if nothing remains.
		"""
		node = self._stack.pop()
		if len(self._implicit) > 0 and self._implicit[-1] is node:
			self._implicit.pop()

		depth = len(self._stack)
		self._html = [entry for entry in self._html if entry[2] < depth or (entry[1] is None and entry[2] == depth)]

		if isinstance(node, nodes.paragraph):
			if len(node) > 0 and isinstance(node[0], nodes.Text):
				node[0] = nodes.Text(node[0].lstrip())

			if len(node) > 0 and isinstance(node[-1], nodes.Text):
				node[-1] = nodes.Text(node[-1].rstrip())

			for child in [child for child in node.children if isinstance(child, nodes.Text) and child == ""]:
				node.remove(child)

			if len(node) == 0:
				node.parent.remove(node)

	def _InlineTarget(self) -> nodes.Element:
		"""
		Return the node inline content goes into: the innermost open node, or a new paragraph in it, if it holds body
		elements.

		:returns: The node.
		"""
		if isinstance(top := self._stack[-1], (nodes.TextElement, nodes.Inline)):
			return top

		paragraph = nodes.paragraph()
		self._Push(top, paragraph)
		self._implicit.append(paragraph)
		return paragraph

	def _BlockTarget(self) -> Nullable[nodes.Element]:
		"""
		Return the node a body element goes into: the innermost open node holding body elements.

		The paragraphs nobody wrote and the inline HTML elements still open above the innermost node a token opened are
		closed: a body element ends them, as in HTML.

		:returns: The node, or ``None`` if the innermost node a token opened holds inline content.
		"""
		floor = self._floors[-1] if len(self._floors) > 0 else 1
		while isinstance(self._stack[-1], (nodes.TextElement, nodes.Inline)) and len(self._stack) > floor:
			self._Pop()

		if isinstance(top := self._stack[-1], (nodes.TextElement, nodes.Inline)):
			return None

		return top

	def _OpenHeading(self, level: int) -> int:
		"""
		Open the node of a heading: a topic's title, or a rubric.

		A heading outside of a topic, or of the topic's level or a higher one, opens a new topic; a deeper heading in the
		topic, or a heading inside e.g. a list, opens a rubric.

		:param level:  The heading's level, ``1`` for ``#``.
		:returns:      The number of nodes opened.
		"""
		target = self._BlockTarget()
		if target is None:
			return self._Open(nodes.rubric(classes=["github-heading"]), inline=False)
		elif target is not self._root and target is not self._topic:
			return self._Open(nodes.rubric(classes=["github-heading"]), inline=False)
		elif self._topic is not None and level > self._topicLevel:
			return self._Open(nodes.rubric(classes=["github-heading"]), inline=False)

		if self._topic is not None:
			self._CloseTopic()

		self._topic =      nodes.topic(classes=["github-topic"])
		self._topicLevel = level
		self._Push(self._root, self._topic)
		self._floors.append(len(self._stack))
		self._Push(self._topic, nodes.title())
		self._floors.append(len(self._stack))
		return 1

	def _CloseTopic(self) -> None:
		"""
		Close the open topic, and every node opened in it.
		"""
		while self._stack[-1] is not self._topic:
			self._Close()

		self._Close()
		self._topic =      None
		self._topicLevel = 0

	def _AppendText(self, text: str, html: bool) -> None:
		"""
		Append text to the innermost open node: verbatim in code, else with GitHub's references linked - except in a
		link - and emoji as nodes.

		Raw HTML's whitespace is collapsed to a space; whitespace between HTML elements holding body elements is skipped.

		:param text: The text.
		:param html: Whether the text is raw HTML's.
		"""
		if any(isinstance(node, (nodes.literal, nodes.literal_block)) for node in self._stack):
			self._stack[-1].append(nodes.Text(text))
			return
		elif html:
			text = _WHITESPACE.sub(" ", text)
			if text.strip() == "" and not isinstance(self._stack[-1], (nodes.TextElement, nodes.Inline)):
				return

		references = not any(isinstance(node, nodes.reference) for node in self._stack)
		self._InlineTarget().extend(self._converter.ConvertText(text, references))

	def _Footnote(self, number: int) -> nodes.footnote:
		"""
		Return the footnote of a number, created by its first reference or by its definition.

		A footnote is labeled by its number counted from 1, and gets an ID unique in the document.

		:param number: The parser's number of the footnote, counted from 0.
		:returns:      The footnote.
		"""
		if (footnote := self._footnotes.get(number)) is None:
			footnote = nodes.footnote(backrefs=[])
			footnote += nodes.label(f"{number + 1}", f"{number + 1}")
			self._document.set_id(footnote, suggested_prefix="github-footnote")
			self._footnotes[number] = footnote

		return footnote

	def _FootnoteReference(self, number: int) -> nodes.footnote_reference:
		"""
		Create a reference to a footnote.

		:param number: The parser's number of the footnote, counted from 0.
		:returns:      The reference.
		"""
		footnote = self._Footnote(number)
		reference = nodes.footnote_reference(f"{number + 1}", f"{number + 1}", refid=footnote["ids"][0])
		footnote["backrefs"].append(self._document.set_id(reference, suggested_prefix="github-footnote-reference"))
		return reference

	def StartElement(self, tag: str, attributes: dict[str, str]) -> None:
		"""
		Translate an HTML element's start tag: open the node of the element, or write the node of an empty element.

		An element of :data:`HTML_ELEMENTS` opens its node, an element mapped to ``None`` none. ``<br>``, ``<img>`` and
		``<hr>`` are written as a line break, an image and a horizontal rule. In ``<pre>``, every element is transparent.
		Every other element is warned about once, and transparent.

		A ``<li>`` or ``<p>`` closes an open one of its kind directly before, as HTML allows to omit its end tag.

		:param tag:        The element's name, in lower case.
		:param attributes: The element's attributes; an attribute without value has value ``""``.
		"""
		inCode = any(isinstance(node, nodes.literal_block) for node in self._stack)
		if tag == "br":
			self._InlineTarget().append(nodes.Text("\n") if inCode else LineBreak("\n", "\n"))
			return
		elif tag == "img":
			image = nodes.image(uri=attributes.get("src", ""), alt=attributes.get("alt", ""), classes=[IMAGE_CLASS])
			for dimension in ("width", "height"):
				if (value := attributes.get(dimension, "")).isdigit():
					image[dimension] = f"{value}px"
			self._InlineTarget().append(image)
			return
		elif tag == "hr":
			if (target := self._BlockTarget()) is not None:
				target.extend(nodes.raw("", written, format=writer) for writer, written in BREAK_ROLES["hr"].items())
			return
		elif tag in ("area", "base", "col", "embed", "input", "link", "meta", "source", "track", "wbr"):
			self._WarnElement(tag)
			return

		if tag in ("li", "p") and len(self._html) > 0 and self._html[-1][0] == tag:
			self.EndElement(tag)

		nodeClass, classes = HTML_ELEMENTS.get(tag, (None, ()))
		if inCode or nodeClass is None or (tag == "a" and attributes.get("href", "") == ""):
			if not inCode and tag not in HTML_ELEMENTS:
				self._WarnElement(tag)
			self._html.append((tag, None, len(self._stack)))
			return

		node = nodeClass(classes=list(classes))
		if tag == "a":
			node["refuri"] = attributes["href"]
		elif tag == "ul":
			node["bullet"] = "*"
		elif tag == "ol":
			node["enumtype"] = "arabic"
			node["prefix"] =   ""
			node["suffix"] =   "."
			if (start := attributes.get("start", "")).isdigit() and start != "1":
				node["start"] = int(start)
		elif tag == "pre":
			node["language"] = attributes.get("lang", "text")

		if issubclass(nodeClass, nodes.Inline):
			target = self._InlineTarget()
		elif (target := self._BlockTarget()) is None:
			self._Warn(f"HTML element '<{tag}>' not supported inside '{self._stack[-1].tagname}'; content kept.")
			self._html.append((tag, None, len(self._stack)))
			return

		self._html.append((tag, node, len(self._stack)))
		self._Push(target, node)

	def EndElement(self, tag: str) -> None:
		"""
		Translate an HTML element's end tag: close the node of the innermost open element of that name, and every node
		opened after it.

		An end tag without an open element of that name, or whose element is outside the innermost node a token opened,
		is ignored.

		:param tag: The element's name, in lower case.
		"""
		for index in range(len(self._html) - 1, -1, -1):
			if self._html[index][0] == tag:
				break
		else:
			return

		_, node, depth = self._html[index]
		if node is None:
			del self._html[index]
			return

		floor = self._floors[-1] if len(self._floors) > 0 else 1
		if depth < floor:
			return

		while len(self._stack) > depth:
			self._Pop()

	def AppendHTMLText(self, text: str) -> None:
		"""
		Translate the text of raw HTML, whose character references are resolved.

		:param text: The text.
		"""
		self._AppendText(text, html=True)

	def _WarnElement(self, tag: str) -> None:
		"""
		Warn about an HTML element without docutils counterpart, once per element name.

		:param tag: The element's name.
		"""
		if tag not in self._warned:
			self._warned.add(tag)
			self._Warn(f"HTML element '<{tag}>' not supported; content kept as text.")

	def _Warn(self, message: str) -> None:
		"""
		Warn about something the Markdown holds, which has no docutils counterpart, with type ``github`` and subtype
		``markdown``.

		:param message: The message, which is prefixed by the Markdown line.
		"""
		getLogger(__name__).warning(
			f"Markdown line {self._line}: {message}", type="github", subtype="markdown", location=self._location
		)


@export
class RawHTMLParser(HTMLParser):
	"""
	A parser of the raw HTML in Markdown, which hands the elements and the text to a :class:`MarkdownTranslator`.

	A comment is skipped, as GitHub doesn't show it either. A classic class, because :class:`~html.parser.HTMLParser`
	has no slots.
	"""

	def __init__(self, translator: MarkdownTranslator) -> None:
		"""
		Initializes a parser for one piece of raw HTML.

		:param translator: The translator, which gets the elements and the text.
		"""
		super().__init__(convert_charrefs=True)
		self._translator = translator

	def handle_starttag(self, tag: str, attrs: list[tuple[str, Nullable[str]]]) -> None:
		"""
		Hand an element's start tag to the translator.

		:param tag:   The element's name, in lower case.
		:param attrs: The element's attributes, as pairs of name and value; ``None`` for an attribute without value.
		"""
		self._translator.StartElement(tag, {name: "" if value is None else value for name, value in attrs})

	def handle_endtag(self, tag: str) -> None:
		"""
		Hand an element's end tag to the translator.

		:param tag: The element's name, in lower case.
		"""
		self._translator.EndElement(tag)

	def handle_data(self, data: str) -> None:
		"""
		Hand text to the translator.

		:param data: The text.
		"""
		self._translator.AppendHTMLText(data)
