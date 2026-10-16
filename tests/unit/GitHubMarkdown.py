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
Unit tests for :mod:`pyTooling.Sphinx.GitHubMarkdown`: parameters, GitHub's references, emoji, release notes, output.

The release notes are real ones of pyTooling, GHDL and OSVVM; the output is a built page in HTML and LaTeX.
"""
from os                                         import environ
from pathlib                                    import Path
from subprocess                                 import run as subprocess_run
from sys                                        import executable
from textwrap                                   import dedent
from unittest.mock                              import patch

from docutils                                   import nodes
from docutils.frontend                          import get_default_settings
from docutils.parsers.rst                       import Parser
from docutils.utils                             import new_document
from sphinx.transforms.post_transforms.images   import ImageDownloader

from pyTooling.Exceptions                       import MissingDependencyError
from pyTooling.Sphinx                           import LATEX_PREAMBLE
from pyTooling.Sphinx.GitHubMarkdown            import GitHubMarkdown
from pyTooling.Sphinx.Node                      import Emoji
from pyTooling.Testing                          import Testcase, testsuite, testcase

from tests.unit.Extension                       import Project


if __name__ == "__main__":  # pragma: no cover
	print("ERROR: you called a testcase declaration file as an executable module.")
	print("Use: 'python -m unittest <testcase module>'")
	exit(1)


DATA = Path(__file__).parent.parent / "data" / "GitHubMarkdown"
"""The release notes of pyTooling, GHDL and OSVVM, and a file of GitHub-flavoured Markdown's constructs."""

LOGGER = "sphinx.pyTooling.Sphinx"
"""Name of the logger every module of the package warns with, as parent logger."""


def document() -> nodes.document:
	"""
	Create an empty document, which converted nodes get their IDs in.

	:returns: The document.
	"""
	return new_document("test", get_default_settings(Parser))


@testsuite("Converter")
class Converter(Testcase):
	"""The converter's parameters: repository, server URL and line breaks."""

	@testcase("Defaults")
	def Defaults(self) -> None:
		"""
		The server is github.com, and a line break is written as a line break.
		"""
		converter = GitHubMarkdown("pyTooling/pyTooling.Sphinx")

		self.assertEqual("pyTooling/pyTooling.Sphinx", converter.Repository)
		self.assertEqual("https://github.com", converter.ServerURL)
		self.assertTrue(converter.LineBreaks)

	@testcase("Server URL")
	def ServerURL(self) -> None:
		"""
		A server URL loses a trailing slash, and every link starts with it.
		"""
		converter = GitHubMarkdown("owner/name", serverURL="https://git.example.org/", lineBreaks=False)

		self.assertEqual("https://git.example.org", converter.ServerURL)
		self.assertFalse(converter.LineBreaks)
		self.assertEqual("https://git.example.org/owner/name/issues/1", converter.ConvertText("#1")[0]["refuri"])

	@testcase("Repository is None")
	def RepositoryNone(self) -> None:
		"""
		A repository of ``None`` is a ValueError.
		"""
		with self.assertRaises(ValueError) as context:
			GitHubMarkdown(None)

		self.assertEqual("Parameter 'repository' is None.", str(context.exception))

	@testcase("Repository of wrong type")
	def RepositoryType(self) -> None:
		"""
		A repository, which isn't a string, is a TypeError, whose note names the type.
		"""
		with self.assertRaises(TypeError) as context:
			GitHubMarkdown(42)

		self.assertEqual("Parameter 'repository' is not of type 'str'.", str(context.exception))
		self.assertEqual(["Got type 'int'."], context.exception.__notes__)

	@testcase("Repository of wrong form")
	def RepositoryForm(self) -> None:
		"""
		A repository, which isn't ``<owner>/<name>``, is a ValueError, whose note names the value.
		"""
		for repository in ("pyTooling", "pyTooling/", "/pyTooling", "a/b/c", "-a/b"):
			with self.subTest(repository=repository), self.assertRaises(ValueError) as context:
				GitHubMarkdown(repository)

			self.assertEqual("Parameter 'repository' is not of form '<owner>/<name>'.", str(context.exception))
			self.assertEqual([f"Got value '{repository}'."], context.exception.__notes__)

	@testcase("Server URL of wrong form")
	def ServerURLForm(self) -> None:
		"""
		A server URL, which isn't an HTTP or HTTPS URL, is a ValueError; ``None`` too.
		"""
		with self.assertRaises(ValueError) as context:
			GitHubMarkdown("a/b", serverURL="github.com")

		self.assertEqual("Parameter 'serverURL' is not an HTTP or HTTPS URL.", str(context.exception))

		with self.assertRaises(ValueError) as context:
			GitHubMarkdown("a/b", serverURL=None)

		self.assertEqual("Parameter 'serverURL' is None.", str(context.exception))

	@testcase("Line breaks of wrong type")
	def LineBreaksType(self) -> None:
		"""
		A line break setting, which isn't a boolean, is a TypeError.
		"""
		with self.assertRaises(TypeError) as context:
			GitHubMarkdown("a/b", lineBreaks="yes")

		self.assertEqual("Parameter 'lineBreaks' is not of type 'bool'.", str(context.exception))

	@testcase("Convert's parameters")
	def ConvertParameters(self) -> None:
		"""
		Convert checks the Markdown, the document, the title and the location.
		"""
		converter = GitHubMarkdown("a/b")
		for arguments, exception, message in (
			((None, document()),          ValueError, "Parameter 'markdown' is None."),
			((b"x", document()),          TypeError,  "Parameter 'markdown' is not of type 'str'."),
			(("x", None),                 ValueError, "Parameter 'document' is None."),
			(("x", "document"),           TypeError,  "Parameter 'document' is not of type 'docutils.nodes.document'."),
			(("x", document(), None),     ValueError, "Parameter 'repeatedTitle' is None."),
			(("x", document(), "", 12),   TypeError,  "Parameter 'location' is not of type 'str'."),
		):
			with self.subTest(message=message), self.assertRaises(exception) as context:
				converter.Convert(*arguments)

			self.assertEqual(message, str(context.exception))


@testsuite("Dependencies")
class Dependencies(Testcase):
	"""The extra ``markdown``: imported when a converter is created, not before."""

	@testcase("Missing markdown-it-py")
	def MissingMarkdownIt(self) -> None:
		"""
		Without markdown-it-py, creating a converter raises a MissingDependencyError naming the package and the extra.
		"""
		with patch.dict("sys.modules", {"markdown_it": None}), self.assertRaises(MissingDependencyError) as context:
			GitHubMarkdown("a/b")

		self.assertEqual("Optional dependency 'markdown-it-py' not installed.", str(context.exception))

	@testcase("Missing mdit-py-plugins")
	def MissingPlugins(self) -> None:
		"""
		Without mdit-py-plugins, creating a converter raises a MissingDependencyError naming the package.
		"""
		with patch.dict("sys.modules", {"mdit_py_plugins.gfm": None}), self.assertRaises(MissingDependencyError) as context:
			GitHubMarkdown("a/b")

		self.assertEqual("Optional dependency 'mdit-py-plugins' not installed.", str(context.exception))

	@testcase("Extension without markdown-it-py")
	def Extension(self) -> None:
		"""
		Setting up 'pyTooling.Sphinx', which registers the post-transform of this module, imports neither package.

		Runs a Python process that sets up the extension with a mocked application, and checks 'sys.modules'.
		"""
		script = dedent("""\
			import sys
			from unittest.mock import MagicMock

			import pyTooling.Sphinx

			pyTooling.Sphinx.setup(MagicMock())
			assert "pyTooling.Sphinx.GitHubMarkdown" in sys.modules, "the converter's module wasn't imported"
			assert "markdown_it" not in sys.modules, "markdown-it-py was imported"
			assert "mdit_py_plugins" not in sys.modules, "mdit-py-plugins was imported"
		""")
		root = Path(__file__).parent.parent.parent
		result = subprocess_run(
			[executable, "-c", script], cwd=root, env=environ.copy(), capture_output=True, text=True, check=False
		)

		self.assertEqual(0, result.returncode, result.stderr)


@testsuite("GitHub's references")
class References(Testcase):
	"""Issues, pull requests, users and commits referred to in a text."""

	_converter = GitHubMarkdown("pyTooling/pyTooling")

	def _references(self, text: str) -> list[tuple[str, str]]:
		"""
		Convert a text, and return its links.

		:param text: The text.
		:returns:    Per link the URL and the text.
		"""
		return [
			(node["refuri"], node.astext()) for node in self._converter.ConvertText(text) if isinstance(node, nodes.reference)
		]

	@testcase("Issues")
	def Issues(self) -> None:
		"""
		``#12``, ``GH-12`` and ``owner/name#12`` refer to an issue, which GitHub redirects to a pull request.
		"""
		converted = self._converter.ConvertText("Fixes #12, GH-13 and pyTooling/Actions#307.")

		self.assertEqual(
			[
				("https://github.com/pyTooling/pyTooling/issues/12", "#12"),
				("https://github.com/pyTooling/pyTooling/issues/13", "GH-13"),
				("https://github.com/pyTooling/Actions/issues/307", "pyTooling/Actions#307"),
			],
			self._references("Fixes #12, GH-13 and pyTooling/Actions#307.")
		)
		self.assertEqual(["github-issue"], converted[1]["classes"])
		self.assertEqual("Fixes #12, GH-13 and pyTooling/Actions#307.", "".join(node.astext() for node in converted))

	@testcase("Not an issue")
	def NotIssues(self) -> None:
		"""
		A ``#`` in a word, a path or a URL, or followed by a word, isn't a reference.
		"""
		for text in ("C#12", "example.org/#12", "#12a", "#abc", "page#12", "##12", "#12-x"):
			with self.subTest(text=text):
				self.assertEqual([], self._references(text))

	@testcase("Users")
	def Users(self) -> None:
		"""
		``@user`` refers to a user, also at the end of a sentence; a team, an e-mail address and a decorator in a word
		don't.
		"""
		self.assertEqual(
			[("https://github.com/Paebbels", "@Paebbels"), ("https://github.com/umarcor", "@umarcor")],
			self._references("Thanks @Paebbels, @pyTooling/maintainers, jim@synthworks and @umarcor.")
		)

	@testcase("Commits")
	def Commits(self) -> None:
		"""
		A commit's hash refers to the commit, shown as its first seven characters; one of another repository is
		prefixed by it.
		"""
		converted = self._converter.ConvertText(
			"d1d186cdb73f55bfa7846095ff4fe02f74570587, d1d186c and pyTooling/Actions@d1d186c."
		)
		references = [node for node in converted if isinstance(node, nodes.reference)]

		self.assertEqual(
			[
				"https://github.com/pyTooling/pyTooling/commit/d1d186cdb73f55bfa7846095ff4fe02f74570587",
				"https://github.com/pyTooling/pyTooling/commit/d1d186c",
				"https://github.com/pyTooling/Actions/commit/d1d186c",
			],
			[reference["refuri"] for reference in references]
		)
		self.assertEqual(["d1d186c", "d1d186c", "pyTooling/Actions@d1d186c"], [node.astext() for node in references])
		self.assertIsInstance(references[0][0], nodes.literal)
		self.assertEqual(["github-commit"], references[0]["classes"])

	@testcase("Not a commit")
	def NotCommits(self) -> None:
		"""
		Digits only, hexadecimal letters only, fewer than 7 or more than 40 characters, upper case or a word around the
		hash aren't a commit.
		"""
		for text in ("1234567", "20261015", "deadbee", "d1d186", "a" * 39 + "12", "D1D186C", "xd1d186c", "d1d186c-1"):
			with self.subTest(text=text):
				self.assertEqual([], self._references(text))

	@testcase("References off")
	def ReferencesOff(self) -> None:
		"""
		Without references - e.g. in a link's text - only emoji are converted.
		"""
		converted = self._converter.ConvertText("#12 @user :tada:", references=False)

		self.assertEqual(["#12 @user ", "\N{PARTY POPPER}"], [node.astext() for node in converted])
		self.assertIsInstance(converted[1], Emoji)


@testsuite("Emoji")
class Emojis(Testcase):
	"""Emoji written as shortcodes and as characters."""

	_converter = GitHubMarkdown("pyTooling/pyTooling")

	def _emoji(self, text: str) -> list[tuple[str, str]]:
		"""
		Convert a text, and return its emoji.

		:param text: The text.
		:returns:    Per emoji the characters and the shortcode.
		"""
		return [(node.astext(), node["shortcode"]) for node in self._converter.ConvertText(text) if isinstance(node, Emoji)]

	@testcase("Shortcodes")
	def Shortcodes(self) -> None:
		"""
		A shortcode is the emoji's characters, an alias too; the variation selector is restored where GitHub's table
		leaves it out.
		"""
		self.assertEqual(
			[
				("\N{PARTY POPPER}", "tada"),
				("\N{THUMBS UP SIGN}", "+1"),
				("\N{THUMBS UP SIGN}", "thumbsup"),
				("\N{WARNING SIGN}\N{VARIATION SELECTOR-16}", "warning"),
			],
			self._emoji(":tada: :+1: :thumbsup: :warning:")
		)

	@testcase("Unknown shortcodes")
	def UnknownShortcodes(self) -> None:
		"""
		A shortcode GitHub doesn't know, a custom GitHub emoji without characters, and a time stay text.
		"""
		converted = self._converter.ConvertText(":returns: :octocat: 12:30:45")

		self.assertEqual([], [node for node in converted if isinstance(node, Emoji)])
		self.assertEqual(":returns: :octocat: 12:30:45", "".join(node.astext() for node in converted))

	@testcase("Characters")
	def Characters(self) -> None:
		"""
		An emoji written as characters - with or without variation selector, also a sequence - is an emoji node.
		"""
		self.assertEqual(
			[
				("\N{SPARKLES}", "sparkles"),
				("\N{GEAR}\N{VARIATION SELECTOR-16}", "gear"),
				("\N{MAN}\N{ZERO WIDTH JOINER}\N{PERSONAL COMPUTER}", "man_technologist"),
				("#\N{VARIATION SELECTOR-16}\N{COMBINING ENCLOSING KEYCAP}", "hash"),
			],
			self._emoji(
				"\N{SPARKLES} new, \N{GEAR}\N{VARIATION SELECTOR-16} changed by "
				"\N{MAN}\N{ZERO WIDTH JOINER}\N{PERSONAL COMPUTER} at #\N{VARIATION SELECTOR-16}\N{COMBINING ENCLOSING KEYCAP}"
			)
		)

	@testcase("Text characters")
	def TextCharacters(self) -> None:
		"""
		A character below U+2190, e.g. the copyright sign, is an emoji only if followed by variation selector 16.
		"""
		self.assertEqual(
			[("\N{COPYRIGHT SIGN}\N{VARIATION SELECTOR-16}", "copyright")],
			self._emoji("\N{COPYRIGHT SIGN} 2026, \N{TRADE MARK SIGN}, \N{COPYRIGHT SIGN}\N{VARIATION SELECTOR-16}")
		)


@testsuite("Release notes")
class ReleaseNotes(Testcase):
	"""Real release notes of pyTooling, GHDL and OSVVM, with Markdown, raw HTML and emoji."""

	def _convert(self, fileName: str, repository: str, repeatedTitle: str = "") -> nodes.container:
		"""
		Convert release notes, which mustn't cause a warning.

		:param fileName:      Name of the file in the test data.
		:param repository:    The repository.
		:param repeatedTitle: Optional, the title the first heading is skipped for. Default: ``""``.
		:returns:             A container holding the nodes.
		"""
		markdown = (DATA / fileName).read_text(encoding="utf-8")
		with self.assertNoLogs(LOGGER):
			converted = GitHubMarkdown(repository).Convert(markdown, document(), repeatedTitle)

		container = nodes.container()
		container.extend(converted)
		return container

	@testcase("pyTooling v8.0.0")
	def pyTooling8(self) -> None:
		"""
		pyTooling's headings are topics.
		"""
		container = self._convert("pyTooling-v8.0.0.md", "pyTooling/pyTooling")

		self.assertEqual(
			["New Features", "Changes", "Bug Fixes", "Documentation", "Unit Tests", "Related Issues"],
			[topic[0].astext() for topic in container.findall(nodes.topic)]
		)
		self.assertEqual(33, len(list(container.findall(nodes.list_item))))

	@testcase("pyTooling v9.0.0")
	def pyTooling9(self) -> None:
		"""
		pyTooling v9.0.0 has emoji written as characters, a table and many references.
		"""
		container = self._convert("pyTooling-v9.0.0.md", "pyTooling/pyTooling")

		self.assertEqual(8, len(list(container.findall(nodes.topic))))
		self.assertEqual(19, len(list(container.findall(Emoji))))
		self.assertEqual(1, len(list(container.findall(nodes.table))))
		self.assertEqual(84, len(list(container.findall(nodes.reference))))

	@testcase("GHDL v5.0.1")
	def GHDL(self) -> None:
		"""
		GHDL's notes open with a heading repeating the title; without it, the two subheadings are the topics.
		"""
		container = self._convert("GHDL-v5.0.1.md", "ghdl/ghdl", "GHDL 5.0.1")

		self.assertEqual(
			["Docker Images", "pyGHDL 5.0.1"], [topic[0].astext() for topic in container.findall(nodes.topic)]
		)
		self.assertEqual(13, len(list(container.findall(nodes.list_item))))

	@testcase("OSVVM 2024.07")
	def OSVVM202407(self) -> None:
		"""
		OSVVM's notes are a nested list in raw HTML.
		"""
		container = self._convert("OSVVM-2024.07.md", "OSVVM/OsvvmLibraries")

		self.assertEqual(["paragraph", "bullet_list", "paragraph"], [node.tagname for node in container])
		self.assertEqual(52, len(list(container.findall(nodes.list_item))))

	@testcase("OSVVM 2026.05")
	def OSVVM202605(self) -> None:
		"""
		OSVVM 2026.05 opens with a badge before the heading repeating the title, and has a table of its files.
		"""
		container = self._convert("OSVVM-2026.05.md", "OSVVM/OsvvmLibraries", "OSVVM 2026.05")

		self.assertEqual(["Release Files", "Changes"], [topic[0].astext() for topic in container.findall(nodes.topic)])
		self.assertEqual(1, len(list(container.findall(nodes.table))))
		self.assertEqual(16, len(list(container.findall(nodes.list_item))))

	@testcase("OSVVM 2026.09")
	def OSVVM202609(self) -> None:
		"""
		OSVVM 2026.09 mixes a Markdown table, raw HTML lists and a horizontal rule.
		"""
		container = self._convert("OSVVM-2026.09.md", "OSVVM/OsvvmLibraries", "OSVVM 2026.09")

		self.assertEqual(["Release Files", "Changes"], [topic[0].astext() for topic in container.findall(nodes.topic)])
		self.assertEqual(11, len(list(container.findall(nodes.list_item))))
		self.assertEqual(2, len(list(container.findall(nodes.raw))))

	@testcase("GFM constructs")
	def Constructs(self) -> None:
		"""
		Every construct of GitHub-flavoured Markdown converts without a warning.
		"""
		container = self._convert("GFM-constructs.md", "pyTooling/pyTooling")

		self.assertEqual(["topic", "footnote"], [node.tagname for node in container])
		self.assertEqual(8, len(list(container.findall(nodes.reference))))
		self.assertEqual(2, len(list(container.findall(Emoji))))


@testsuite("Rendering in a document")
class Rendering(Project):
	"""What converted Markdown puts into a built page in HTML and LaTeX, through a directive of the test project."""

	_conf = dedent("""\
		from sphinx.util.docutils import SphinxDirective
		from pyTooling.Sphinx.GitHubMarkdown import GitHubMarkdown

		class Markdown(SphinxDirective):
			has_content = True

			def run(self):
				converter = GitHubMarkdown("pyTooling/pyTooling")
				return converter.Convert("\\n".join(self.content), self.state.document, location=self.get_location())

		def setup(app):
			app.add_directive("markdown", Markdown)
		""")

	_document = (
		"Index\n#####\n\n"
		".. markdown::\n\n"
		"   # Notes\n\n"
		"   :tada: ~~gone~~ #12 :hash: :man_technologist:\n"
		"   line\n\n"
		"   - [x] done\n"
		"   - [ ] open\n"
	)

	@testcase("HTML")
	def HTML(self) -> None:
		"""
		HTML writes an emoji with its shortcode as tooltip, a disabled checkbox, a line break and a struck-out text.
		"""
		self._build(self._document, conf=self._conf)

		self.assertEqual([], self._warningLines())
		html = self._html("index")
		self.assertIn('<aside class="topic github-topic">', html)
		self.assertIn('<span class="github-emoji" title=":tada:">\N{PARTY POPPER}</span>', html)
		self.assertIn('<span class="strike">gone</span>', html)
		self.assertIn('href="https://github.com/pyTooling/pyTooling/issues/12"', html)
		self.assertIn('title=":man_technologist:">\N{MAN}\N{ZERO WIDTH JOINER}\N{PERSONAL COMPUTER}</span><br />', html)
		self.assertIn(
			'<input class="github-task-list-checkbox" type="checkbox" disabled="" checked="" aria-label="Completed task" />',
			html
		)
		self.assertIn(
			'<input class="github-task-list-checkbox" type="checkbox" disabled="" aria-label="Incomplete task" />', html
		)

	@testcase("LaTeX")
	def LaTeX(self) -> None:
		"""
		LaTeX writes emoji as Unicode characters, checkboxes as box symbols, line breaks and strikethrough with commands.

		An emoji's ASCII characters - the ``#`` of a keycap - are escaped. A line break is written as ``\\newline`` and
		strikethrough with package ``ulem``, whose commands the preamble defines.
		"""
		self._build(self._document, "latex", conf=self._conf)

		self.assertEqual([], self._warningLines())
		latex = next((self._path / "build" / "latex").glob("*.tex")).read_text(encoding="utf-8")
		self.assertIn(
			"\N{PARTY POPPER} \\DUrole{strike}{gone} \\sphinxhref{https://github.com/pyTooling/pyTooling/issues/12}{\\#12} "
			"\\#\N{VARIATION SELECTOR-16}\N{COMBINING ENCLOSING KEYCAP} \N{MAN}\N{ZERO WIDTH JOINER}\N{PERSONAL COMPUTER}",
			latex
		)
		self.assertIn("\\newline{}", latex)
		self.assertIn("\\(\\boxtimes\\) done", latex)
		self.assertIn("\\(\\square\\) open", latex)
		self.assertIn("\\usepackage[normalem]{ulem}", latex)
		self.assertIn(LATEX_PREAMBLE, latex)

	_alerts = (
		"Index\n#####\n\n"
		".. markdown::\n\n"
		"   > [!NOTE]\n   > N.\n\n"
		"   > [!TIP]\n   > T.\n\n"
		"   > [!IMPORTANT]\n   > I.\n\n"
		"   > [!WARNING]\n   > W.\n\n"
		"   > [!CAUTION]\n   > C.\n"
	)

	@testcase("Alerts in HTML")
	def AlertsHTML(self) -> None:
		"""
		HTML writes each kind of alert as the admonition of that kind, titled by the kind.
		"""
		self._build(self._alerts, conf=self._conf)

		self.assertEqual([], self._warningLines())
		html = self._html("index")
		for kind, title, text in (
			("note",      "Note",      "N."),
			("tip",       "Tip",       "T."),
			("important", "Important", "I."),
			("warning",   "Warning",   "W."),
			("caution",   "Caution",   "C."),
		):
			with self.subTest(kind=kind):
				self.assertIn(
					f'<div class="github-alert admonition {kind}">\n<p class="admonition-title">{title}</p>\n<p>{text}</p>',
					html
				)

	@testcase("Alerts in LaTeX")
	def AlertsLaTeX(self) -> None:
		"""
		LaTeX writes each kind of alert as Sphinx' admonition environment of that kind.
		"""
		self._build(self._alerts, "latex", conf=self._conf)

		self.assertEqual([], self._warningLines())
		latex = next((self._path / "build" / "latex").glob("*.tex")).read_text(encoding="utf-8")
		for kind, title, text in (
			("note",      "Note",      "N."),
			("tip",       "Tip",       "T."),
			("important", "Important", "I."),
			("warning",   "Warning",   "W."),
			("caution",   "Caution",   "C."),
		):
			with self.subTest(kind=kind):
				self.assertRegex(latex, rf"\\begin{{sphinxadmonition}}{{{kind}}}{{{title}:}}\s+\\sphinxAtStartPar\s+{text}")

	@testcase("LaTeX preamble of the project")
	def ProjectPreamble(self) -> None:
		"""
		The preamble of the project's configuration is kept, the extension's commands follow it.
		"""
		self._build("Index\n#####\n", "latex", latex_elements={"preamble": "% project preamble"})

		latex = next((self._path / "build" / "latex").glob("*.tex")).read_text(encoding="utf-8")
		self.assertIn(f"% project preamble{LATEX_PREAMBLE}", latex)

	@testcase("SVG image in LaTeX")
	def SVGImage(self) -> None:
		"""
		An SVG image is replaced by its alternative text in LaTeX, with a warning at the image's line; HTML keeps it.
		"""
		document = "Index\n#####\n\n.. markdown::\n\n   ![build status](https://example.org/badge.svg)\n"
		self._build(document, "latex", conf=self._conf)

		self.assertEqual(
			[
				"src/index.rst:6: WARNING: SVG image 'https://example.org/badge.svg' not supported by LaTeX; replaced by its "
				"alternative text. [github.image]"
			],
			self._warningLines()
		)
		latex = next((self._path / "build" / "latex").glob("*.tex")).read_text(encoding="utf-8")
		self.assertIn("build status", latex)
		self.assertNotIn("badge.svg", latex)

		self._build(document, conf=self._conf)

		self.assertEqual([], self._warningLines())
		self.assertIn('src="https://example.org/badge.svg"', self._html("index"))

	@testcase("shields.io badge in LaTeX")
	def ShieldsBadge(self) -> None:
		"""
		A shields.io badge is fetched from ``raster.shields.io`` in LaTeX, as PNG - without the suffix ``.svg``.
		"""
		requested: list[str] = []
		document = (
			"Index\n#####\n\n.. markdown::\n\n"
			"   ![tests](https://img.shields.io/badge/tests-passing-green)\n"
			"   ![x](https://img.shields.io/badge/x-y-red.svg?style=flat)\n"
		)
		with patch.object(ImageDownloader, "handle", lambda transform, node: requested.append(node["uri"])):
			self._build(document, "latex", conf=self._conf)

		self.assertEqual(
			["https://raster.shields.io/badge/tests-passing-green", "https://raster.shields.io/badge/x-y-red?style=flat"],
			requested
		)

	@testcase("Warning location and type")
	def Warning(self) -> None:
		"""
		A warning of the conversion names the directive's location and the Markdown line, and has type ``github`` and
		subtype ``markdown``, so it can be suppressed.
		"""
		document = "Index\n#####\n\n.. markdown::\n\n   a\n\n   <font>b</font>\n"
		self._build(document, conf=self._conf)

		self.assertEqual(
			[
				"src/index.rst:4: WARNING: Markdown line 3: HTML element '<font>' not supported; content kept as text. "
				"[github.markdown]"
			],
			self._warningLines()
		)

		self._build(document, conf=self._conf, suppress_warnings=["github.markdown"])

		self.assertEqual([], self._warningLines())
