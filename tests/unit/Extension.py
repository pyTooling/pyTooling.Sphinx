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
from io                     import StringIO
from os                     import sep
from pathlib                import Path
from tempfile               import TemporaryDirectory
from typing                 import Any
from unittest.mock          import MagicMock

from sphinx.testing.util    import SphinxTestApp
from sphinx.util.console    import strip_colors

from pyTooling.Testing      import Testcase, testsuite, testcase

from pyTooling.Sphinx       import __version__, SUBSTITUTIONS, setup
from pyTooling.Sphinx.Roles import BREAK_ROLES, PYTHON_CODE_ROLE, STYLE_ROLES


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

	def _build(self, index: str, **config: Any) -> "SphinxTestApp":
		"""
		Write the document and build the project as HTML.

		:param index:  Content of the document ``index``.
		:param config: Configuration values overriding the defaults.
		:returns:      The Sphinx application after the build.
		"""
		source = self._path / "src"
		(source / "conf.py").write_text('extensions = ["pyTooling.Sphinx"]\n', encoding="utf-8")
		(source / "index.rst").write_text(index, encoding="utf-8")

		self._warnings = StringIO()
		app = SphinxTestApp(
			"html", source, self._path / "build", freshenv=True, confoverrides=config, status=StringIO(),
			warning=self._warnings
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
		Return the warnings of the last build, without the temporary directory's path - as given and as resolved, e.g.
		below ``/private/var`` on macOS -, and with ``/`` as the separator of the remaining paths.

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
		style, break and code roles and the four directives.
		"""
		app = MagicMock()
		metadata = setup(app)

		roles = {call.args[0] for call in app.add_role.call_args_list}
		directives = {call.args[0] for call in app.add_directive.call_args_list}
		self.assertEqual(set(STYLE_ROLES) | set(BREAK_ROLES) | {PYTHON_CODE_ROLE}, roles)
		self.assertEqual({"condensed-class", "dependency-table", "xsd-graph", "shields"}, directives)
		self.assertEqual(__version__, metadata["version"])

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
