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
Unit tests for the Sphinx extension :mod:`pyTooling.Sphinx`, each built in a small Sphinx project.
"""
from io                            import StringIO
from os                            import sep
from pathlib                       import Path
from tempfile                      import TemporaryDirectory
from typing                        import Any, Optional as Nullable
from unittest.mock                 import MagicMock

from sphinx.ext.graphviz           import graphviz
from sphinx.testing.util           import SphinxTestApp
from sphinx.util.console           import strip_colors

from pyTooling.Testing             import Testcase, testsuite, testcase

from pyTooling.Sphinx              import __version__, NODES, REPORT_ROLES, SUBSTITUTIONS, setup
from pyTooling.Sphinx              import HTML, LaTeX
from pyTooling.Sphinx.Abbreviation import ROLES as ABBREVIATION_ROLES, AbbreviationDomain
from pyTooling.Sphinx.Node         import Landscape
from pyTooling.Sphinx.Roles        import BREAK_ROLES, PYTHON_CODE_ROLE, STYLE_ROLES


if __name__ == "__main__":  # pragma: no cover
	print("ERROR: you called a testcase declaration file as an executable module.")
	print("Use: 'python -m unittest <testcase module>'")
	exit(1)


class Project(Testcase):
	"""Base-class of the testcases: a temporary directory holding a Sphinx project per testcase."""

	_directory: TemporaryDirectory
	_path:      Path
	_warnings:  StringIO

	def setUp(self) -> None:
		self._directory = TemporaryDirectory()
		self._path = Path(self._directory.name)
		(self._path / "src").mkdir()

	def tearDown(self) -> None:
		self._directory.cleanup()

	def _build(
		self,
		index: str,
		builder: str = "html",
		documents: Nullable[dict[str, str]] = None,
		parallel: int = 0,
		**config: Any
	) -> "SphinxTestApp":
		"""
		Write the documents and build the project.

		:param index:     Content of the document ``index``.
		:param builder:   Optional, name of the builder. Default: ``"html"``.
		:param documents: Optional, more documents, keyed by name; ``index`` lists them in a hidden toctree.
		:param parallel:  Optional, number of processes reading in parallel; ``0`` reads serially.
		:param config:    Configuration values overriding the defaults.
		:returns:         The Sphinx application after the build.
		"""
		source = self._path / "src"
		(source / "conf.py").write_text('extensions = ["pyTooling.Sphinx"]\n', encoding="utf-8")
		if documents is not None:
			index += "\n.. toctree::\n   :hidden:\n\n" + "".join(f"   {name}\n" for name in documents)
			for name, content in documents.items():
				(source / f"{name}.rst").write_text(content, encoding="utf-8")

		(source / "index.rst").write_text(index, encoding="utf-8")

		self._warnings = StringIO()
		app = SphinxTestApp(
			builder, source, self._path / "build", freshenv=True, confoverrides=config, status=StringIO(),
			warning=self._warnings, parallel=parallel
		)
		try:
			app.build()
		finally:
			app.cleanup()

		return app

	def _html(self, name: str) -> str:
		"""
		Read a built page.

		:param name: Name of the document.
		:returns:    The page's HTML.
		"""
		return (self._path / "build" / "html" / f"{name}.html").read_text(encoding="utf-8")

	def _warningLines(self) -> list[str]:
		"""
		Return the warnings of the last build, without the temporary directory's path and with ``/`` as path separator.

		The temporary directory is removed as given and as resolved, e.g. below ``/private/var`` on macOS.

		:returns: One line per warning.
		"""
		prefixes = sorted({str(self._path), str(self._path.resolve())}, key=len, reverse=True)
		lines = []
		for line in self._warnings.getvalue().splitlines():
			line = strip_colors(line)
			for prefix in prefixes:
				line = line.replace(f"{prefix}{sep}", "").replace(f"{prefix}/", "")
			lines.append(line.replace("\\", "/") if sep == "\\" else line)

		return lines


@testsuite("Extension registration")
class Registration(Project):
	"""What the extension registers with Sphinx."""

	@testcase("Extension metadata")
	def Metadata(self) -> None:
		"""
		The extension reports its version and is safe for parallel reading.

		Builds an empty project with the extension and checks the build has no warnings, the version Sphinx reports is the
		package's '__version__', and 'parallel_read_safe' is set.
		"""
		app = self._build("Index\n#####\n")

		self.assertEqual([], self._warningLines())
		self.assertEqual(__version__, app.extensions["pyTooling.Sphinx"].version)
		self.assertTrue(app.extensions["pyTooling.Sphinx"].parallel_read_safe)

	@testcase("Registered roles and directives")
	def RolesAndDirectives(self) -> None:
		"""
		The extension's setup() registers every role and directive it brings.

		Calls setup() with a mocked application and compares the names passed to 'add_role' and 'add_directive' with the
		style, break, code, abbreviation and unit test roles and the six directives, and checks the abbreviation domain
		is added.
		"""
		app = MagicMock()
		metadata = setup(app)

		roles = {call.args[0] for call in app.add_role.call_args_list}
		directives = {call.args[0] for call in app.add_directive.call_args_list}
		self.assertEqual(
			set(STYLE_ROLES) | set(BREAK_ROLES) | {PYTHON_CODE_ROLE} | set(ABBREVIATION_ROLES) | set(REPORT_ROLES), roles
		)
		self.assertEqual(
			{"condensed-class", "dependency-table", "xmlschema-graph", "shields", "tree", "abbreviations"},
			directives
		)
		app.add_domain.assert_any_call(AbbreviationDomain)
		self.assertEqual(__version__, metadata["version"])

	@testcase("Registered nodes")
	def Nodes(self) -> None:
		"""
		The extension's setup() registers every node in NODES with its visitors.

		Calls setup() with a mocked application and compares the arguments passed to 'add_node' with NODES: HTML visitors
		for every node, LaTeX visitors where NODES has them.
		"""
		app = MagicMock()
		setup(app)

		registered = [(call.args[0], call.kwargs) for call in app.add_node.call_args_list]
		expected = [(entry["node"], {key: entry[key] for key in ("html", "latex") if key in entry}) for entry in NODES]
		self.assertEqual(expected, registered)

	@testcase("Landscape node")
	def Landscape(self) -> None:
		"""
		The 'Landscape' node is registered with visitors for HTML and LaTeX.

		Looks up 'Landscape' in NODES and checks it carries the visitors of 'pyTooling.Sphinx.HTML' and
		'pyTooling.Sphinx.LaTeX'.
		"""
		entry = next(entry for entry in NODES if entry["name"] == "Landscape")

		self.assertIs(Landscape, entry["node"])
		self.assertEqual((HTML.visit_Landscape, HTML.depart_Landscape), entry["html"])
		self.assertEqual((LaTeX.visit_Landscape, LaTeX.depart_Landscape), entry.get("latex"))

	@testcase("Substitutions in the prolog")
	def Substitutions(self) -> None:
		"""
		The extension adds its substitutions to 'rst_prolog'.

		Builds an empty project and checks the configured prolog contains 'SUBSTITUTIONS'.
		"""
		app = self._build("Index\n#####\n")

		self.assertIn(SUBSTITUTIONS, app.config.rst_prolog)


@testsuite("Rendering in a document")
class Rendering(Project):
	"""What the extension's roles and stylesheet put into a built page."""

	@testcase("Style roles")
	def StyleRoles(self) -> None:
		"""
		The style, diff, code and break roles render without warnings.

		Builds a document using ':red:', ':addition:', ':pycode:' and '|br|', and checks the page holds their output, e.g.
		the CSS class 'colorred'.
		"""
		self._build("Index\n#####\n\n:red:`red` :addition:`added` :pycode:`print(1)` line|br|break\n")

		self.assertEqual([], self._warningLines())
		html = self._html("index")
		self.assertIn('class="colorred"', html)
		self.assertIn("added", html)
		self.assertIn("print", html)

	@testcase("Parallel build")
	def Parallel(self) -> None:
		"""
		A project builds with parallel readers, which makes Sphinx merge every domain's data.

		Builds seven documents with two processes - Sphinx reads in parallel from six documents on - and checks there is
		no warning, and the documents were built.
		"""
		documents = {f"doc{number}": f"Document {number}\n##########\n\n:acs:`FSM`\n" for number in range(6)}
		self._build(
			"Index\n#####\n\n.. abbreviations::\n\n   FSM\n      :long: finite-state machine\n",
			documents=documents,
			parallel=2
		)

		self.assertEqual([], self._warningLines())
		self.assertIn('href="index.html#abbreviation-FSM"', self._html("doc5"))

	@testcase("Stylesheet linked")
	def Stylesheet(self) -> None:
		"""
		Every page links the extension's stylesheet.

		Builds an empty project and checks the page links 'pyTooling.css' under the hashed name Sphinx gives a static
		file.
		"""
		self._build("Index\n#####\n")

		html = self._html("index")
		self.assertRegex(html, r'_static/pyTooling\.[0-9a-f]{32}\.css')


@testsuite("Trees in a document")
class TreeRendering(Project):
	"""What the 'tree' directive puts into a built page, in HTML and in LaTeX."""

	_document = (
		"Index\n#####\n\n"
		".. _target:\n\n"
		"Target\n******\n\n"
		".. tree::\n"
		"   :root-icon: U+1F4E6\n"
		"   :leaf-icon: U+1F4C4\n"
		"   :icons:     > U+1F4C1\n"
		"{options}"
		"\n"
		"   - root\n"
		"     - node\n"
		"       - see :ref:`target`\n"
		"     > empty\n"
	)

	@testcase("HTML")
	def HTML(self) -> None:
		"""
		An entry with children is a 'details' element with both expander icons; every entry has its kind's class.

		Builds a tree with a root, a node, a leaf linking to a label and a leaf with a declared marker, and checks the
		page.
		"""
		self._build(self._document.format(options=""))

		self.assertEqual([], self._warningLines())
		html = self._html("index")
		self.assertIn('<ul class="pytooling-tree">', html)
		self.assertIn('<li class="tree-root tree-expandable"><details open><summary>', html)
		self.assertIn('<span class="tree-expander tree-expanded" aria-hidden="true">\u25be</span>', html)
		self.assertIn('<span class="tree-expander tree-collapsed" aria-hidden="true">\u25b8</span>', html)
		self.assertIn(
			'<span class="tree-icon" aria-hidden="true">\U0001f4e6</span><span class="tree-text">root</span>', html
		)
		self.assertIn('<li class="tree-node tree-expandable"><details open>', html)
		self.assertIn('<a class="reference internal" href="#target">', html)
		self.assertIn(
			'<li class="tree-leaf"><span class="tree-expander" aria-hidden="true"></span>'
			'<span class="tree-icon" aria-hidden="true">\U0001f4c1</span><span class="tree-text">empty</span></li>',
			html
		)

	@testcase("Expanded levels")
	def ExpandedLevels(self) -> None:
		"""
		':expanded-levels:' expands that many levels and collapses the rest.

		Builds the tree with one expanded level and checks the root is open and the node isn't.
		"""
		self._build(self._document.format(options="   :expanded-levels: 1\n"))

		self.assertEqual([], self._warningLines())

		html = self._html("index")
		self.assertIn('<li class="tree-root tree-expandable"><details open>', html)
		self.assertIn('<li class="tree-node tree-expandable"><details><summary>', html)

	@testcase("LaTeX")
	def LaTeX(self) -> None:
		"""
		LaTeX renders the tree as nested bullet lists, without icons.

		Builds the tree as LaTeX and checks the three nested 'itemize' environments and that no icon is written.
		"""
		self._build(self._document.format(options=""), "latex")

		self.assertEqual([], self._warningLines())
		latex = next((self._path / "build" / "latex").glob("*.tex")).read_text(encoding="utf-8")
		self.assertEqual(3, latex.count("\\begin{itemize}"))
		self.assertNotIn("\U0001f4e6", latex)
		self.assertNotIn("\u25be", latex)

	@testcase("Content error")
	def ContentError(self) -> None:
		"""
		A mistake in the content is reported at the directive's line.

		Builds a tree whose content isn't an entry, and checks the warning.
		"""
		self._build("Index\n#####\n\n.. tree::\n\n   root\n")

		self.assertEqual(
			["src/index.rst:4: ERROR: tree: 'root' is not an entry, which starts with '- '. [docutils]"],
			self._warningLines()
		)

	@testcase("Error in an entry")
	def EntryError(self) -> None:
		"""
		A mistake in an entry's text is reported at the entry's line.

		Builds a tree whose second entry uses an unknown role, and checks the warning names line 7.
		"""
		self._build("Index\n#####\n\n.. tree::\n\n   - root\n     - :unknown:`x`\n")

		self.assertEqual(
			['src/index.rst:7: ERROR: Unknown interpreted text role "unknown". [docutils]'],
			self._warningLines()
		)


@testsuite("Trees with descriptions in a document")
class TreeDescriptionRendering(Project):
	"""What the 'tree' directive puts into a built page for entries with descriptions, in HTML, text and LaTeX."""

	_document = (
		"Index\n#####\n\n"
		".. tree::\n"
		"   :leaf-icon: U+1F4C4\n"
		"\n"
		"   - root     | the root\n"
		"     - node\n"
		"       - leaf | e.g. ``leaf.py``\n"
	)

	@testcase("HTML")
	def HTML(self) -> None:
		"""
		Every entry is a row of the label and the description, which is empty for an entry without one; the roots state
		the column's width, each row its level, and the separator isn't written.

		Builds a tree with a described root, a node without description and a described leaf with an icon, and checks
		the page.
		"""
		self._build(self._document)

		self.assertEqual([], self._warningLines())
		html = self._html("index")
		self.assertIn(
			'<li class="tree-root tree-expandable" style="--pyTooling-tree-column: '
			'calc(var(--pyTooling-tree-expander-width) + max(4ch, calc(1 * var(--pyTooling-tree-level) + 4ch), '
			'calc(2 * var(--pyTooling-tree-level) + 7ch)))"><details open><summary>'
			'<span class="tree-row" style="--pyTooling-tree-depth: 0"><span class="tree-label">'
			'<span class="tree-expander tree-expanded" aria-hidden="true">\u25be</span>',
			html
		)
		self.assertIn(
			'<span class="tree-text">root</span></span><span class="tree-description">the root</span></span></summary>',
			html
		)
		self.assertIn(
			'<li class="tree-node tree-expandable"><details open><summary>'
			'<span class="tree-row" style="--pyTooling-tree-depth: 1"><span class="tree-label">',
			html
		)
		self.assertIn(
			'<span class="tree-text">node</span></span><span class="tree-description"></span></span></summary>', html
		)
		self.assertIn(
			'<li class="tree-leaf"><span class="tree-row" style="--pyTooling-tree-depth: 2"><span class="tree-label">'
			'<span class="tree-expander" aria-hidden="true"></span>'
			'<span class="tree-icon" aria-hidden="true">\U0001f4c4</span><span class="tree-text">leaf</span></span>'
			'<span class="tree-description">e.g. <code class="docutils literal notranslate"><span class="pre">leaf.py</span>'
			'</code></span></span></li>',
			html
		)
		self.assertNotIn("\u2013", html)

	@testcase("Text")
	def Text(self) -> None:
		"""
		A format without visitors of its own writes the description behind the entry's text and an en dash.

		Builds the tree as plain text and checks each entry's line.
		"""
		self._build(self._document, "text")

		self.assertEqual([], self._warningLines())
		text = (self._path / "build" / "text" / "index.txt").read_text(encoding="utf-8")
		self.assertIn("* root \u2013 the root\n", text)
		self.assertIn("  * node\n", text)
		self.assertIn('    * leaf \u2013 e.g. "leaf.py"\n', text)

	@testcase("LaTeX")
	def LaTeX(self) -> None:
		"""
		LaTeX writes the description behind the entry's text and an en dash.

		Builds the tree as LaTeX and checks the root's and the leaf's item.
		"""
		self._build(self._document, "latex")

		self.assertEqual([], self._warningLines())
		latex = next((self._path / "build" / "latex").glob("*.tex")).read_text(encoding="utf-8")
		self.assertIn("root \\textendash{} the root", latex)
		self.assertIn("leaf \\textendash{} e.g. \\sphinxcode{\\sphinxupquote{leaf.py}}", latex)

	@testcase("Error in a description")
	def DescriptionError(self) -> None:
		"""
		A mistake in a description is reported at the entry's line.

		Builds a tree whose second entry's description uses an unknown role, and checks the warning names line 7.
		"""
		self._build("Index\n#####\n\n.. tree::\n\n   - root\n     - child | :unknown:`x`\n")

		self.assertEqual(
			['src/index.rst:7: ERROR: Unknown interpreted text role "unknown". [docutils]'],
			self._warningLines()
		)


@testsuite("Abbreviations in a document")
class AbbreviationRendering(Project):
	"""What the 'abbreviations' directive and the abbreviation roles put into a built page."""

	_list = (
		".. abbreviations::\n\n"
		"   FSM\n"
		"      :long:        finite-state machine\n"
		"      :long-plural: finite-state machines\n\n"
		"      A machine in one of a finite number of states, see :acs:`HDL`.\n\n"
		"      Its transitions are drawn as a graph.\n\n"
		"   HDL\n"
		"      :long: hardware description language\n"
	)

	def _abbr(self, short: str, long: str, text: Nullable[str] = None, summary: Nullable[str] = None) -> str:
		"""
		Return the HTML of a short form with its box.

		:param short:   The short form; the box shows it only if a title replaced it.
		:param long:    The long form the box shows.
		:param text:    Optional, the title shown instead of the short form.
		:param summary: Optional, the description's summary the box shows.
		:returns:       The ``<abbr>`` element.
		"""
		box = (
			("" if text is None else f"<strong>{short}</strong> ") + long +
			("" if summary is None else f'<span class="pytooling-abbreviation-summary">{summary}</span>')
		)
		return (
			f'<abbr class="pytooling-abbreviation">{short if text is None else text}<span class="pytooling-abbreviation-box" '
			f'role="tooltip">{box}</span></abbr>'
		)

	@testcase("List")
	def List(self) -> None:
		"""
		The list is a definition list; each abbreviation is a target, its long form opens its definition.

		Builds a list of two abbreviations, one with a description, and checks the terms and definitions.
		"""
		self._build(f"Index\n#####\n\n{self._list}")

		self.assertEqual([], self._warningLines())
		html = self._html("index")
		self.assertIn('<dl class="pytooling-abbreviations">', html)
		self.assertIn('<dt id="abbreviation-FSM">FSM</dt><dd><p class="abbreviation-long">finite-state machine</p>', html)
		self.assertIn("A machine in one of a finite number of states, see", html)
		self.assertIn('<dt id="abbreviation-HDL">HDL</dt>', html)

	@testcase("Roles")
	def Roles(self) -> None:
		"""
		Each role writes the form it names, linked to the abbreviation; a short form carries the box.

		Builds a paragraph using every role and checks each one's output.
		"""
		roles = ", ".join(f":{role}:`FSM`" for role in ("ac", "acs", "acl", "acf", "acp", "acsp", "aclp", "acfp"))
		self._build(f"Index\n#####\n\n{roles}\n\n{self._list}")

		self.assertEqual([], self._warningLines())
		html = self._html("index")
		singular = self._abbr("FSM", "finite-state machine")
		plural = self._abbr("FSMs", "finite-state machines")
		for role, content in (
			("ac",   singular),
			("acs",  singular),
			("acl",  "finite-state machine"),
			("acf",  f"finite-state machine ({singular})"),
			("acp",  plural),
			("acsp", plural),
			("aclp", "finite-state machines"),
			("acfp", f"finite-state machines ({plural})"),
		):
			with self.subTest(role=role):
				self.assertIn(
					f'<a class="reference internal" href="#abbreviation-FSM"><span class="xref abbreviation abbreviation-{role}">'
					f'{content}</span></a>',
					html
				)

	@testcase("Title and domain prefix")
	def Title(self) -> None:
		"""
		A title replaces the form, the box still explains the abbreviation; the roles also exist in their domain.

		Builds a reference with a title and one written ':abbreviation:acl:', and checks both.
		"""
		self._build(f"Index\n#####\n\n:acs:`FSM-based <FSM>` and :abbreviation:acl:`HDL`\n\n{self._list}")

		self.assertEqual([], self._warningLines())
		html = self._html("index")
		self.assertIn(self._abbr("FSM", "finite-state machine", "FSM-based"), html)
		self.assertIn('abbreviation-acl">hardware description language</span></a>', html)

	@testcase("Summary in the box")
	def Summary(self) -> None:
		"""
		With 'pyTooling_Abbreviation_ShowSummary', the box also shows the summary of the description: its first paragraph.

		Builds ':acs:' of an abbreviation with a two-paragraph description and of one without a description, with the
		option set, and checks both boxes.
		"""
		self._build(
			f"Index\n#####\n\n:acs:`FSM` and :acs:`HDL`\n\n{self._list}", pyTooling_Abbreviation_ShowSummary=True
		)

		self.assertEqual([], self._warningLines())
		html = self._html("index")
		self.assertIn(
			self._abbr("FSM", "finite-state machine", summary="A machine in one of a finite number of states, see HDL."),
			html
		)
		self.assertIn(self._abbr("HDL", "hardware description language"), html)
		self.assertNotIn("Its transitions are drawn as a graph.</span>", html)

	@testcase("Default plurals")
	def DefaultPlurals(self) -> None:
		"""
		Without ':plural:' and ':long-plural:', a plural appends an 's'.

		Builds ':aclp:' and ':acsp:' of an abbreviation stating neither plural, and checks both.
		"""
		self._build(f"Index\n#####\n\n:aclp:`HDL`, :acsp:`HDL`\n\n{self._list}")

		html = self._html("index")
		self.assertIn("hardware description languages</span></a>", html)
		self.assertIn(self._abbr("HDLs", "hardware description languages"), html)

	@testcase("Another document")
	def OtherDocument(self) -> None:
		"""
		A role refers to an abbreviation listed in another document.

		Builds the list in one document and a reference in another, and checks the link points to the list's page.
		"""
		listing = f"Abbreviations\n#############\n\n{self._list}"
		self._build("Index\n#####\n\n:acf:`HDL`\n", documents={"abbreviations": listing})

		self.assertEqual([], self._warningLines())
		self.assertIn('href="abbreviations.html#abbreviation-HDL"', self._html("index"))

	@testcase("LaTeX")
	def LaTeX(self) -> None:
		"""
		LaTeX writes the form as an abbreviation with a hyperlink, without the box.

		Builds a short form as LaTeX and checks the hyperlink, and that the long form isn't written beside it.
		"""
		self._build(f"Index\n#####\n\n:acs:`FSM`\n\n{self._list}", "latex")

		self.assertEqual([], self._warningLines())
		latex = next((self._path / "build" / "latex").glob("*.tex")).read_text(encoding="utf-8")
		self.assertIn("\\hyperref[\\detokenize{index:abbreviation-FSM}]", latex)
		self.assertIn("{\\sphinxstyleabbreviation{FSM}}", latex)
		self.assertEqual(1, latex.count("finite\\sphinxhyphen{}state machine"), "Only the list writes the long form.")

	@testcase("Alphabetical order")
	def Ordered(self) -> None:
		"""
		The list is shown in alphabetical order, ignoring case, unless ':ordered:' is 'no'.

		Builds a list written as 'HDL', 'fsm', 'ASIC' with the default and with ':ordered: no', and checks the order of the
		terms on the page.
		"""
		unordered = (
			"   HDL\n      :long: hardware description language\n\n"
			"   fsm\n      :long: finite-state machine\n\n"
			"   ASIC\n      :long: application-specific integrated circuit\n"
		)
		for option, order in (("", ("ASIC", "fsm", "HDL")), ("   :ordered: no\n", ("HDL", "fsm", "ASIC"))):
			with self.subTest(option=option):
				self._build(f"Index\n#####\n\n.. abbreviations::\n{option}\n{unordered}\n:acs:`fsm`\n")

				self.assertEqual([], self._warningLines())
				html = self._html("index")
				positions = [html.index(f'<dt id="abbreviation-{short}">') for short in order]
				self.assertListEqual(sorted(positions), positions)
				self.assertIn('href="#abbreviation-fsm"', html)

	@testcase("Option error")
	def OptionError(self) -> None:
		"""
		A value of ':ordered:' other than yes/true or no/false is reported at the directive's line.

		Builds a list with ':ordered: maybe' and checks the message.
		"""
		self._build("Index\n#####\n\n.. abbreviations::\n   :ordered: maybe\n\n   FSM\n      :long: m\n")

		self.assertEqual(
			[
				"src/index.rst:4: ERROR: abbreviations::ordered: 'maybe' not supported for a boolean value "
				"(yes/true, no/false). [docutils]"
			],
			self._warningLines()
		)

	@testcase("Unknown abbreviation")
	def Unknown(self) -> None:
		"""
		A reference to an abbreviation that isn't in a list is reported at its line.

		Builds a reference to 'XYZ' and checks the warning.
		"""
		self._build("Index\n#####\n\n:acs:`XYZ`\n")

		self.assertEqual(
			["src/index.rst:4: WARNING: abbreviation 'XYZ' isn't in a list of abbreviations [ref.acs]"],
			self._warningLines()
		)

	@testcase("Listed twice")
	def Duplicate(self) -> None:
		"""
		An abbreviation listed in two documents is reported at the second.

		Builds two documents listing 'HDL' and checks the warning names the first one.
		"""
		second = "Second\n######\n\n.. abbreviations::\n\n   HDL\n      :long: hardware description language\n"
		self._build(f"Index\n#####\n\n{self._list}", documents={"second": second})

		self.assertEqual(
			["src/second.rst:6: WARNING: abbreviation 'HDL' is in the list of document 'index' already"],
			self._warningLines()
		)

	@testcase("Content errors")
	def ContentErrors(self) -> None:
		"""
		A list that isn't a definition list of abbreviations with their fields is reported at the directive's line.

		Builds a paragraph instead of a list, an abbreviation without ':long:', one with an unknown field, and one
		without fields, and checks each message.
		"""
		for content, message in (
			("   FSM is a machine.\n", "The directive's content isn't a definition list of abbreviations."),
			("   FSM\n      :plural: FSMs\n", "Abbreviation 'FSM' has no field ':long:'."),
			("   FSM\n      :long: m\n      :short: F\n", "Abbreviation 'FSM' has an unknown field ':short:'."),
			("   FSM\n      finite-state machine\n", "Abbreviation 'FSM' doesn't start with a field list, e.g. ':long:'."),
		):
			with self.subTest(content=content):
				self._build(f"Index\n#####\n\n.. abbreviations::\n\n{content}")

				self.assertEqual([f"src/index.rst:4: ERROR: abbreviations: {message} [docutils]"], self._warningLines())


@testsuite("Schema graphs in a document")
class SchemaGraphRendering(Project):
	"""Where 'xmlschema-graph' finds the schema it draws."""

	@testcase("Schema of a package")
	def Package(self) -> None:
		"""
		With ':package:', the argument names a resource file of that package.

		Builds a document drawing 'TestReport-v0.1.xsd' of 'pyTooling.Resources' - with the 'dummy' builder, so Graphviz
		needn't be installed - and checks the document holds the schema's graph.
		"""
		app = self._build(
			"Index\n#####\n\n.. xmlschema-graph:: TestReport-v0.1.xsd\n   :package: pyTooling.Resources\n",
			builder="dummy"
		)

		self.assertEqual([], self._warningLines())
		graphs = list(app.env.get_doctree("index").findall(graphviz))
		self.assertEqual(1, len(graphs))
		self.assertEqual("Diagram of TestReport-v0.1.xsd", graphs[0]["alt"])
		self.assertIn("testsuite", graphs[0]["code"])

	@testcase("Schema missing in a package")
	def Package_Missing(self) -> None:
		"""
		A file the package doesn't hold is reported at the directive.

		Builds a document naming 'Missing.xsd' of 'pyTooling.Resources', and checks the error names file and package.
		"""
		self._build("Index\n#####\n\n.. xmlschema-graph:: Missing.xsd\n   :package: pyTooling.Resources\n", builder="dummy")

		self.assertIn(
			"xmlschema-graph: Couldn't find schema 'Missing.xsd' in package 'pyTooling.Resources'.",
			"\n".join(self._warningLines())
		)

	@testcase("Package missing")
	def Package_Unknown(self) -> None:
		"""
		A package that can't be imported is reported at the directive.

		Builds a document naming the package 'pyTooling.NoSuchPackage', and checks the error says it can't be imported.
		"""
		self._build(
			"Index\n#####\n\n.. xmlschema-graph:: TestReport-v0.1.xsd\n   :package: pyTooling.NoSuchPackage\n",
			builder="dummy"
		)

		self.assertIn(
			"xmlschema-graph: Couldn't import package 'pyTooling.NoSuchPackage'.",
			"\n".join(self._warningLines())
		)
