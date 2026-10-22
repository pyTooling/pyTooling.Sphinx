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
Unit tests for :class:`pyTooling.Sphinx.Pages.GeneratedPages`: pages generated for a model of another domain, built as
nodes or written as reStructuredText, each in a small Sphinx project.
"""
from textwrap               import dedent

from pyTooling.Sphinx.Pages import GeneratedPages
from pyTooling.Testing      import testsuite, testcase

from tests.unit.Extension   import Project


if __name__ == "__main__":  # pragma: no cover
	print("ERROR: you called a testcase declaration file as an executable module.")
	print("Use: 'python -m unittest <testcase module>'")
	exit(1)


#: Code appended to :file:`conf.py`: pages for a tree of dictionaries, below document ``tree``, in domain ``py``.
CONF = dedent("""\
	from pathlib                import Path

	from docutils               import nodes

	from pyTooling.Sphinx.Pages import GeneratedPages

	MODEL = {"name": "root", "children": [{"name": "left"}, {"name": "right", "children": [{"name": "leaf"}]}]}


	class TreePages(GeneratedPages[dict]):
		_DOMAIN = "py"
		_pages = {}

		def _Name(self, entity):
			return entity["name"]

		def _Children(self, roleName, entity):
			return [("node", child) for child in entity.get("children", [])]

		def _Page(self, docName, roleName, entity):
			section = nodes.section("", nodes.title(entity["name"], entity["name"]), ids=[f"tree-{entity['name']}"])
			section += nodes.paragraph("Built as nodes.", "Built as nodes.")
			children = [self.DocName(child) for child in entity.get("children", [])]
			if len(children) > 0:
				section += self._TableOfContents(docName, children)
			return section


	class ReSTPages(TreePages):
		_pages = {}

		def _Fill(self, sphinxApplication, document, docName, roleName, entity):
			name = entity["name"]
			title = f"{name}\\n{'#' * len(name)}"
			text = f".. _tree-{name}:\\n\\n{title}\\n\\nWritten as *text*.\\n\\n.. py:function:: {name}()\\n"
			self._ParseReST(sphinxApplication, document, text)
			children = [self.DocName(child) for child in entity.get("children", [])]
			if len(children) > 0:
				document[-1] += self._TableOfContents(docName, children)


	PAGES = ReSTPages if KIND == "rest" else TreePages


	def createPages(app):
		pages = PAGES("tree", "tree", Path(app.confdir) / "conf.py", [("node", MODEL)])
		PAGES._pages = {"tree": pages}
		pages.Register(app.env)


	def setup(app):
		app.connect("builder-inited", createPages)
		app.connect("env-before-read-docs", PAGES.GenerateAll)
		app.connect("html-page-context", PAGES.HideSource)
""")


@testsuite("Generated pages of another domain")
class Generated(Project):
	"""Pages for a tree of dictionaries, listed below the document ``index`` by its table of contents."""

	def _buildTree(self, kind: str, index: str) -> None:
		"""
		Build the project with the tree's pages.

		:param kind:  ``nodes`` for pages built as nodes, ``rest`` for pages written as reStructuredText.
		:param index: Content of the document ``index``.
		"""
		conf = f"KIND = {kind!r}\n{CONF}"
		self._build(f"{index}\n\n.. toctree::\n\n   tree/root\n", conf=conf)

	@testcase("Built as nodes")
	def Nodes(self) -> None:
		"""
		The pages built as nodes have their document names below the prefix, and are written.

		Builds the project and reads the pages of the tree.
		"""
		self._buildTree("nodes", "Index\n#####\n")

		self.assertEqual([], self._warningLines())
		for docName in ("tree/root", "tree/root/left", "tree/root/right", "tree/root/right/leaf"):
			with self.subTest(document=docName):
				self.assertIn("Built as nodes.", self._html(docName))

	@testcase("Written as reStructuredText")
	def ReST(self) -> None:
		"""
		A page written as reStructuredText runs the directives and roles of every domain: its labels and the objects of
		domain 'py' are referenced from another document.

		Builds the project and resolves a label and a function of a generated page.
		"""
		self._buildTree("rest", "Index\n#####\n\nSee :ref:`tree-leaf` and :py:func:`right`.\n")

		self.assertEqual([], self._warningLines())
		self.assertIn("<em>text</em>", self._html("tree/root/right/leaf"))
		index = self._html("index")
		self.assertIn('href="tree/root/right/leaf.html#tree-leaf"', index)
		self.assertRegex(index, r'href="tree/root/right\.html#\w+" title="right"><code class="xref py py-func')

	@testcase("Registry")
	def Registry(self) -> None:
		"""
		The registry is per derived class: the base-class has no pages of a model of a derived class.

		Builds the project and checks the registry of the base-class.
		"""
		self._buildTree("nodes", "Index\n#####\n")

		self.assertEqual([], self._warningLines())
		self.assertFalse(GeneratedPages.HasPages("tree"))
