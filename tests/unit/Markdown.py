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
Unit tests for :mod:`pyTooling.Sphinx.Markdown`: the translation of Markdown's blocks and inlines, of headings into
topics and rubrics, and of raw HTML into docutils nodes.
"""
from textwrap                        import dedent

from docutils                        import nodes
from docutils.frontend               import get_default_settings
from docutils.parsers.rst            import Parser
from docutils.utils                  import new_document

from pyTooling.Sphinx.GitHubMarkdown import GitHubMarkdown
from pyTooling.Sphinx.Markdown       import IMAGE_CLASS
from pyTooling.Sphinx.Node           import LineBreak, TaskListCheckbox
from pyTooling.Testing               import Testcase, testsuite, testcase


if __name__ == "__main__":  # pragma: no cover
	print("ERROR: you called a testcase declaration file as an executable module.")
	print("Use: 'python -m unittest <testcase module>'")
	exit(1)


LOGGER = "sphinx.pyTooling.Sphinx.Markdown"
"""Name of the logger the translator warns with."""


def convert(markdown: str, lineBreaks: bool = True, repeatedTitle: str = "") -> list[nodes.Node]:
	"""
	Convert Markdown in the context of repository ``pyTooling/pyTooling``.

	:param markdown:      The Markdown.
	:param lineBreaks:    Optional, whether a line break is written as a line break. Default: ``True``.
	:param repeatedTitle: Optional, the title a heading opening the Markdown is skipped for. Default: ``""``.
	:returns:             The nodes.
	"""
	document = new_document("test", get_default_settings(Parser))
	return GitHubMarkdown("pyTooling/pyTooling", lineBreaks=lineBreaks).Convert(markdown, document, repeatedTitle)


def tree(converted: list[nodes.Node]) -> str:
	"""
	Return the nodes' pseudo-XML, without the trailing newline.

	:param converted: The nodes.
	:returns:         The pseudo-XML of all nodes.
	"""
	return "".join(node.pformat() for node in converted).rstrip("\n")


@testsuite("Markdown blocks")
class Blocks(Testcase):
	"""CommonMark's and GFM's blocks: paragraphs, lists, block quotes, code, tables and horizontal rules."""

	@testcase("Paragraphs")
	def Paragraphs(self) -> None:
		"""
		Two paragraphs become two paragraph nodes.
		"""
		converted = convert("First.\n\nSecond.\n")

		self.assertEqual("<paragraph>\n    First.\n<paragraph>\n    Second.", tree(converted))

	@testcase("Bullet list")
	def BulletList(self) -> None:
		"""
		A bullet list keeps its bullet character; a nested list is put into its item.
		"""
		converted = convert("- a\n  * b\n")

		self.assertEqual(dedent("""\
			<bullet_list bullet="-">
			    <list_item>
			        <paragraph>
			            a
			        <bullet_list bullet="*">
			            <list_item>
			                <paragraph>
			                    b"""
		), tree(converted))

	@testcase("Ordered list")
	def OrderedList(self) -> None:
		"""
		An ordered list is an arabic enumerated list with its suffix, and keeps a start other than 1.
		"""
		converted = convert("3) three\n4) four\n")

		self.assertIsInstance(converted[0], nodes.enumerated_list)
		self.assertEqual(3, converted[0]["start"])
		self.assertEqual(")", converted[0]["suffix"])
		self.assertEqual(2, len(converted[0]))

	@testcase("Task list")
	def TaskList(self) -> None:
		"""
		A task list item's checkbox opens its paragraph; list and item are marked by classes.
		"""
		converted = convert("- [x] done\n- [ ] open\n- plain\n")

		bulletList = converted[0]
		self.assertIn("github-task-list", bulletList["classes"])
		done = bulletList[0][0]
		self.assertIsInstance(done[0], TaskListCheckbox)
		self.assertTrue(done[0]["checked"])
		self.assertEqual("\N{BALLOT BOX WITH CHECK} done", done.astext())
		self.assertFalse(bulletList[1][0][0]["checked"])
		self.assertEqual("\N{BALLOT BOX} open", bulletList[1].astext())
		self.assertNotIn("github-task-list-item", bulletList[2]["classes"])
		self.assertEqual(2, len(list(bulletList.findall(TaskListCheckbox))))

	@testcase("Empty task")
	def EmptyTask(self) -> None:
		"""
		A task list item without text gets a paragraph for its checkbox.
		"""
		converted = convert("- [ ] \n- [x] y\n")

		self.assertEqual(["\N{BALLOT BOX}", "\N{BALLOT BOX WITH CHECK} y"], [item.astext() for item in converted[0]])
		self.assertIsInstance(converted[0][0][0][0], TaskListCheckbox)

	@testcase("Block quote")
	def BlockQuote(self) -> None:
		"""
		A block quote holds its paragraphs.
		"""
		converted = convert("> quoted\n")

		self.assertEqual("<block_quote>\n    <paragraph>\n        quoted", tree(converted))

	@testcase("Alerts")
	def Alerts(self) -> None:
		"""
		A GitHub alert of each kind is the admonition of that kind, marked by class ``github-alert``; its title isn't
		written into it, as the admonition has its own.
		"""
		for kind, admonition in (
			("NOTE",      nodes.note),
			("TIP",       nodes.tip),
			("IMPORTANT", nodes.important),
			("WARNING",   nodes.warning),
			("CAUTION",   nodes.caution),
		):
			with self.subTest(kind=kind):
				converted = convert(f"> [!{kind}]\n> Careful *now*.\n>\n> - item\n")

				self.assertEqual(1, len(converted))
				self.assertIsInstance(converted[0], admonition)
				self.assertEqual(["github-alert"], converted[0]["classes"])
				self.assertEqual(["paragraph", "bullet_list"], [node.tagname for node in converted[0]])
				self.assertEqual("Careful now.", converted[0][0].astext())

	@testcase("Alert written in lower case")
	def AlertLowerCase(self) -> None:
		"""
		An alert's kind is matched in any case, as GitHub does.
		"""
		converted = convert("> [!tip]\n> Hint.\n")

		self.assertIsInstance(converted[0], nodes.tip)

	@testcase("Not an alert")
	def NotAlert(self) -> None:
		"""
		A block quote with an unknown kind stays a block quote, holding the marker as text.
		"""
		converted = convert("> [!HINT]\n> Hint.\n")

		self.assertIsInstance(converted[0], nodes.block_quote)
		self.assertEqual("[!HINT]\nHint.", converted[0].astext())

	@testcase("Fenced code")
	def FencedCode(self) -> None:
		"""
		Fenced code is a literal block in the info string's language; without one, its language is ``text``.
		"""
		converted = convert("```vhdl {.x}\nentity e is end entity;\n```\n\n```\n#12\n```\n")

		self.assertEqual("vhdl", converted[0]["language"])
		self.assertEqual("entity e is end entity;", converted[0].astext())
		self.assertEqual("text", converted[1]["language"])
		self.assertEqual("#12", converted[1].astext())

	@testcase("Indented code")
	def IndentedCode(self) -> None:
		"""
		Indented code is a literal block of language ``text``, which isn't highlighted.
		"""
		converted = convert("    x = 1\n")

		self.assertIsInstance(converted[0], nodes.literal_block)
		self.assertEqual("text", converted[0]["language"])
		self.assertEqual("x = 1", converted[0].astext())

	@testcase("Table")
	def Table(self) -> None:
		"""
		A table has a column specification per column, a header row and the body rows; a cell's alignment is a class.
		"""
		converted = convert("| A | B |\n|:--|--:|\n| 1 | 2 |\n| 3 |\n")

		table = converted[0]
		self.assertIn("github-table", table["classes"])
		tableGroup = table[0]
		self.assertEqual(2, tableGroup["cols"])
		self.assertEqual(2, len(list(tableGroup.findall(nodes.colspec))))
		self.assertEqual(["A", "B"], [entry.astext() for entry in tableGroup.next_node(nodes.thead).findall(nodes.entry)])
		rows = list(tableGroup.next_node(nodes.tbody).findall(nodes.row))
		self.assertEqual(2, len(rows))
		self.assertEqual(["github-align-left"], rows[0][0]["classes"])
		self.assertEqual(["github-align-right"], rows[0][1]["classes"])
		self.assertEqual("1", rows[0][0].astext())

	@testcase("Horizontal rule")
	def HorizontalRule(self) -> None:
		"""
		A horizontal rule is written as the ``|hr|`` substitution writes it: a raw node per format.
		"""
		converted = convert("a\n\n---\n\nb\n")

		self.assertEqual(["html", "latex"], [node["format"] for node in converted if isinstance(node, nodes.raw)])


@testsuite("Markdown inlines")
class Inlines(Testcase):
	"""CommonMark's and GFM's inlines: emphasis, code, links, images, line breaks and footnotes."""

	@testcase("Emphasis, strong and strikethrough")
	def Emphasis(self) -> None:
		"""
		Emphasis and strong emphasis are their nodes; strikethrough is an inline of class ``strike``, as the ``:strike:``
		role writes it.
		"""
		converted = convert("*a* **b** ~~c~~ ~d~\n")

		paragraph = converted[0]
		self.assertIsInstance(paragraph[0], nodes.emphasis)
		self.assertIsInstance(paragraph[2], nodes.strong)
		self.assertEqual(["strike"], paragraph[4]["classes"])
		self.assertEqual(["strike"], paragraph[6]["classes"])
		self.assertEqual("a b c d", paragraph.astext())

	@testcase("Code")
	def Code(self) -> None:
		"""
		Inline code is a literal, in which a reference isn't linked.
		"""
		converted = convert("`#12 @user`\n")

		self.assertEqual("<paragraph>\n    <literal>\n        #12 @user", tree(converted))

	@testcase("Link")
	def Link(self) -> None:
		"""
		A link is a reference, in whose text a reference isn't linked.
		"""
		converted = convert("[see #12](https://example.org)\n")

		reference = converted[0][0]
		self.assertEqual("https://example.org", reference["refuri"])
		self.assertEqual("see #12", reference.astext())
		self.assertEqual(0, len(list(reference.findall(nodes.reference, include_self=False))))

	@testcase("Autolinks")
	def Autolinks(self) -> None:
		"""
		A URL in the text is linked, without the punctuation ending the sentence or a parenthesis around it.
		"""
		converted = convert("See https://example.org/a). (https://example.org/b) and www.example.org.\n")

		references = list(converted[0].findall(nodes.reference))
		self.assertEqual(
			["https://example.org/a", "https://example.org/b", "http://www.example.org"],
			[reference["refuri"] for reference in references]
		)
		self.assertEqual("See https://example.org/a). (https://example.org/b) and www.example.org.", converted[0].astext())

	@testcase("Image")
	def Image(self) -> None:
		"""
		An image keeps its alternative text, and is marked by class ``github-image``.
		"""
		converted = convert("![a *badge*](https://example.org/badge.png)\n")

		image = converted[0][0]
		self.assertIsInstance(image, nodes.image)
		self.assertEqual("https://example.org/badge.png", image["uri"])
		self.assertEqual("a badge", image["alt"])
		self.assertEqual([IMAGE_CLASS], image["classes"])

	@testcase("Line breaks")
	def LineBreaks(self) -> None:
		"""
		A line break in a paragraph and a hard line break are line breaks, as GitHub writes them in a release's notes.
		"""
		converted = convert("a\nb  \nc\n")

		self.assertEqual(2, len(list(converted[0].findall(LineBreak))))
		self.assertEqual("a\nb\nc", converted[0].astext())

	@testcase("Line breaks as spaces")
	def LineBreaksAsSpaces(self) -> None:
		"""
		Without ``lineBreaks``, a line break in a paragraph is a newline in the text, which a writer writes as a space; a
		hard line break stays a line break.
		"""
		converted = convert("a\nb  \nc\n", lineBreaks=False)

		self.assertEqual(1, len(list(converted[0].findall(LineBreak))))
		self.assertEqual("a\nb\nc", converted[0].astext())

	@testcase("Escaped reference")
	def EscapedReference(self) -> None:
		"""
		An escaped ``#`` isn't a reference.
		"""
		converted = convert("\\#12\n")

		self.assertEqual("<paragraph>\n    #\n    12", tree(converted))

	@testcase("Footnotes")
	def Footnotes(self) -> None:
		"""
		A footnote is numbered in the order of its references, follows the text and links back to every reference; its
		ID is unique in the document.
		"""
		converted = convert("a[^n] b[^n] c[^m]\n\n[^m]: M.\n[^n]: N.\n")

		references = list(converted[0].findall(nodes.footnote_reference))
		footnotes = [node for node in converted if isinstance(node, nodes.footnote)]
		self.assertEqual(["1", "1", "2"], [reference.astext() for reference in references])
		self.assertEqual(["1N.", "2M."], [footnote.astext().replace("\n", "") for footnote in footnotes])
		self.assertEqual(footnotes[0]["ids"][0], references[0]["refid"])
		self.assertEqual(footnotes[0]["ids"][0], references[1]["refid"])
		self.assertEqual([references[0]["ids"][0], references[1]["ids"][0]], footnotes[0]["backrefs"])
		self.assertNotEqual(references[0]["ids"], references[1]["ids"])


@testsuite("Headings")
class Headings(Testcase):
	"""Headings become topics and rubrics, never sections."""

	@testcase("Topics")
	def Topics(self) -> None:
		"""
		A heading opens a topic, holding what follows up to the next heading of its level; text before the first
		heading stays outside.
		"""
		converted = convert("Intro.\n\n# A\n\na\n\n# B\n\nb\n")

		self.assertEqual(["paragraph", "topic", "topic"], [node.tagname for node in converted])
		self.assertEqual(["A", "a"], [child.astext() for child in converted[1]])
		self.assertIsInstance(converted[1][0], nodes.title)
		self.assertEqual(["github-topic"], converted[1]["classes"])

	@testcase("Rubrics in a topic")
	def Rubrics(self) -> None:
		"""
		A deeper heading in a topic is a rubric; a heading of a higher level than the topic's opens a new topic.
		"""
		converted = convert("## A\n\n### A.1\n\na\n\n#### A.1.1\n\n# B\n\n## B.1\n")

		self.assertEqual(["topic", "topic"], [node.tagname for node in converted])
		self.assertEqual(["title", "rubric", "paragraph", "rubric"], [node.tagname for node in converted[0]])
		self.assertEqual(["title", "rubric"], [node.tagname for node in converted[1]])
		self.assertEqual(["github-heading"], converted[1][1]["classes"])

	@testcase("Heading in a list")
	def HeadingInList(self) -> None:
		"""
		A heading in a list item or block quote is a rubric, and doesn't close the open topic.
		"""
		converted = convert("# A\n\n- # x\n\n> ## y\n\nz\n")

		self.assertEqual(["topic"], [node.tagname for node in converted])
		self.assertEqual(2, len(list(converted[0].findall(nodes.rubric))))
		self.assertEqual("z", converted[0][-1].astext())

	@testcase("Repeated title")
	def RepeatedTitle(self) -> None:
		"""
		The first heading, which repeats the given title, is skipped - also after a paragraph -, so the headings after it
		are the topics; the comparison ignores repeated whitespace.
		"""
		converted = convert(
			"![badge](https://example.org/b.png)\n# GHDL  5.0.1\n\nText.\n\n## Docker\n\nd\n", repeatedTitle="GHDL 5.0.1"
		)

		self.assertEqual(["paragraph", "paragraph", "topic"], [node.tagname for node in converted])
		self.assertEqual("Docker", converted[2][0].astext())

	@testcase("Other title")
	def OtherTitle(self) -> None:
		"""
		The first heading, which doesn't repeat the given title, is kept, and so is a later one repeating it.
		"""
		converted = convert("# GHDL 5.0.1\n\nText.\n\n# v5.0.1\n", repeatedTitle="v5.0.1")

		self.assertEqual(["GHDL 5.0.1", "v5.0.1"], [node[0].astext() for node in converted])

	@testcase("Footnotes after topics")
	def FootnotesAfterTopics(self) -> None:
		"""
		The footnotes follow the last topic, outside of it.
		"""
		converted = convert("# A\n\na[^1]\n\n[^1]: Note.\n")

		self.assertEqual(["topic", "footnote"], [node.tagname for node in converted])


@testsuite("Raw HTML")
class RawHTML(Testcase):
	"""Raw HTML in Markdown: elements with a docutils counterpart, transparent elements and unknown ones."""

	@testcase("Block list")
	def BlockList(self) -> None:
		"""
		A list of raw HTML, as OSVVM writes its notes: text directly in an item is put into a paragraph; an item without
		end tag is closed by the next one.
		"""
		with self.assertNoLogs(LOGGER):
			converted = convert("<ul>\n\t<li>One\n\t<ul>\n\t\t<li>Nested</li>\n\t</ul></li>\n\t<li>Two\n</ul>\n")

		self.assertEqual(dedent("""\
			<bullet_list bullet="*">
			    <list_item>
			        <paragraph>
			            One
			        <bullet_list bullet="*">
			            <list_item>
			                <paragraph>
			                    Nested
			    <list_item>
			        <paragraph>
			            Two"""
		), tree(converted))

	@testcase("Ordered list")
	def OrderedList(self) -> None:
		"""
		An ``<ol>`` keeps its start.
		"""
		converted = convert('<ol start="5"><li>five</li></ol>\n')

		self.assertIsInstance(converted[0], nodes.enumerated_list)
		self.assertEqual(5, converted[0]["start"])

	@testcase("Details")
	def Details(self) -> None:
		"""
		``<details>`` is a container, ``<summary>`` its rubric; Markdown between them is put into the container.
		"""
		converted = convert("<details><summary>More</summary>\n\nHidden *text*.\n\n</details>\n\nAfter.\n")

		self.assertEqual(["container", "paragraph"], [node.tagname for node in converted])
		self.assertEqual(["github-details"], converted[0]["classes"])
		self.assertEqual(["rubric", "paragraph"], [node.tagname for node in converted[0]])
		self.assertEqual(["github-summary"], converted[0][0]["classes"])
		self.assertEqual(["More", "Hidden text."], [node.astext() for node in converted[0]])

	@testcase("Inline elements")
	def InlineElements(self) -> None:
		"""
		``<kbd>``, ``<sub>``, ``<sup>``, ``<b>``, ``<del>`` and ``<a href>`` in a paragraph are their nodes.
		"""
		with self.assertNoLogs(LOGGER):
			converted = convert(
				'<kbd>Ctrl</kbd> H<sub>2</sub>O x<sup>2</sup> <b>b</b> <del>d</del> <a href="https://example.org">a</a>\n'
			)

		paragraph = converted[0]
		self.assertEqual(
			["literal", "subscript", "superscript", "strong", "inline", "reference"],
			[child.tagname for child in paragraph.children if isinstance(child, nodes.Element)]
		)
		self.assertEqual(["kbd"], paragraph[0]["classes"])
		self.assertEqual("https://example.org", paragraph.next_node(nodes.reference)["refuri"])

	@testcase("Line break and image")
	def BreakAndImage(self) -> None:
		"""
		``<br>`` is a line break; ``<img>`` an image with its alternative text and size in pixels.
		"""
		converted = convert('a<br>b <img src="https://example.org/i.png" alt="i" width="20">\n')

		self.assertIsInstance(converted[0][1], LineBreak)
		image = converted[0].next_node(nodes.image)
		self.assertEqual("https://example.org/i.png", image["uri"])
		self.assertEqual("i", image["alt"])
		self.assertEqual("20px", image["width"])
		self.assertEqual([IMAGE_CLASS], image["classes"])

	@testcase("Preformatted text")
	def Preformatted(self) -> None:
		"""
		``<pre>`` is a literal block, which keeps its whitespace and in which elements are transparent.
		"""
		with self.assertNoLogs(LOGGER):
			converted = convert("<pre><code>a  #12\n<b>b</b></code></pre>\n")

		self.assertIsInstance(converted[0], nodes.literal_block)
		self.assertEqual("a  #12\nb", converted[0].astext())

	@testcase("Text and references")
	def TextAndReferences(self) -> None:
		"""
		Raw HTML's text has its whitespace collapsed and GitHub's references linked.
		"""
		converted = convert("<p>Fixes\n   #12.</p>\n")

		self.assertEqual("Fixes #12.", converted[0].astext())
		self.assertIsInstance(converted[0][1], nodes.reference)

	@testcase("Comment")
	def Comment(self) -> None:
		"""
		A comment is skipped, without a warning.
		"""
		with self.assertNoLogs(LOGGER):
			converted = convert("a <!-- hidden --> b\n")

		self.assertEqual("a  b", converted[0].astext())

	@testcase("Unknown element")
	def UnknownElement(self) -> None:
		"""
		An element without docutils counterpart is warned about once per name, with the Markdown line; its content is
		kept.
		"""
		with self.assertLogs(LOGGER, "WARNING") as logs:
			converted = convert("a\n\n<center>x <font>y</font> <font>z</font></center>\n")

		self.assertEqual(
			[
				"Markdown line 3: HTML element '<center>' not supported; content kept as text.",
				"Markdown line 3: HTML element '<font>' not supported; content kept as text."
			],
			[record.getMessage() for record in logs.records]
		)
		self.assertEqual("x y z", converted[1].astext())

	@testcase("Block element in a paragraph")
	def BlockInParagraph(self) -> None:
		"""
		A block element inside a Markdown paragraph is warned about; its content is kept in the paragraph.
		"""
		with self.assertLogs(LOGGER, "WARNING") as logs:
			converted = convert("a <ul>b</ul> c\n")

		self.assertEqual(
			["Markdown line 1: HTML element '<ul>' not supported inside 'paragraph'; content kept."],
			[record.getMessage() for record in logs.records]
		)
		self.assertEqual("a b c", converted[0].astext())

	@testcase("Unbalanced end tags")
	def Unbalanced(self) -> None:
		"""
		An end tag without open element is ignored; an element left open is closed with the Markdown node around it.
		"""
		with self.assertNoLogs(LOGGER):
			converted = convert("a </b> <em>b\n\nc\n")

		self.assertEqual(["a  b", "c"], [node.astext() for node in converted])
		self.assertIsInstance(converted[0].next_node(nodes.emphasis), nodes.emphasis)
		self.assertIsNone(converted[1].next_node(nodes.emphasis))
