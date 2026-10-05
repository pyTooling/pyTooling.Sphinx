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
Unit tests for the Sphinx extension :mod:`pyTooling.Sphinx.Report`, each built in a small Sphinx project.
"""
from os                      import environ
from pathlib                 import Path
from subprocess              import run as subprocess_run
from sys                     import executable
from textwrap                import dedent
from unittest.mock           import MagicMock

from pyTooling.Sphinx        import __version__
from pyTooling.Sphinx.Report import ReportDomain, setup
from pyTooling.Testing       import testsuite, testcase

from tests.unit.Extension    import Project


if __name__ == "__main__":  # pragma: no cover
	print("ERROR: you called a testcase declaration file as an executable module.")
	print("Use: 'python -m unittest <testcase module>'")
	exit(1)


DATA = Path(__file__).parent.parent.parent / "data" / "Report"
"""Directory of the report files the testcases read."""

DIRECTIVES = {
	"code-coverage", "code-coverage-legend", "module-coverage", "doc-coverage", "doc-coverage-legend", "unittest-summary"
}
"""Names of the directives in domain ``report``."""

CONFIG_VALUES = {
	"pyTooling_CodeCoverage_Packages", "pyTooling_CodeCoverage_Levels", "pyTooling_DocCoverage_Packages",
	"pyTooling_DocCoverage_Levels", "pyTooling_Unittest_Testsuites"
}
"""Names of the configuration values the extension registers."""


class ReportProject(Project):
	"""Base-class of the testcases: a Sphinx project enabling the extension, with the report files of the testcases."""

	def _buildReport(self, index: str, builder: str = "html") -> None:
		"""
		Write the document and build the project, with a unit test report, a code coverage report and a package.

		:param index:   Content of the document ``index``.
		:param builder: Optional, name of the builder. Default: ``"html"``.
		"""
		package = self._path / "myPackage"
		package.mkdir()
		(package / "__init__.py").write_text('"""A documented package."""\n', encoding="utf-8")
		(package / "Module.py").write_text('def function() -> None:\n\tpass\n', encoding="utf-8")

		self._build(
			index, builder, "pyTooling.Sphinx.Report",
			pyTooling_Unittest_Testsuites={"ut": {"xml_report": str(DATA / "unittest.xml")}},
			pyTooling_CodeCoverage_Packages={
				"cov": {"name": "myPackage", "json_report": str(DATA / "coverage.json"), "fail_below": 80, "levels": "default"}
			},
			pyTooling_DocCoverage_Packages={
				"doc": {"name": "myPackage", "directory": str(package), "fail_below": 80, "levels": "default"}
			}
		)


@testsuite("Report extension registration")
class Registration(ReportProject):
	"""What the extension registers with Sphinx."""

	@testcase("Domain, directives and configuration values")
	def Domain(self) -> None:
		"""
		The extension registers domain 'report' with its directives, the configuration values under their new names, and
		sets up 'pyTooling.Sphinx'.

		Builds an empty project and checks the registry, the configuration and the extensions.
		"""
		app = self._build("Index\n#####\n", extension="pyTooling.Sphinx.Report")

		self.assertEqual([], self._warningLines())
		self.assertIn("report", app.registry.domains)
		self.assertEqual(DIRECTIVES, set(app.registry.domain_directives["report"]))
		for name in CONFIG_VALUES:
			with self.subTest(name=name):
				self.assertIn(name, app.config)
		self.assertNotIn("report_codecov_packages", app.config)
		self.assertIn("pyTooling.Sphinx", app.extensions)
		self.assertEqual(__version__, app.extensions["pyTooling.Sphinx.Report"].version)

	@testcase("Setup with a mock")
	def Setup(self) -> None:
		"""
		The extension's setup() sets up 'pyTooling.Sphinx', and registers the domain, the LaTeX package and the
		post-transform.

		Calls setup() with a mocked application and checks the calls.
		"""
		app = MagicMock()
		metadata = setup(app)

		app.setup_extension.assert_called_once_with("pyTooling.Sphinx")
		app.add_domain.assert_called_once_with(ReportDomain)
		self.assertEqual(
			DIRECTIVES, {call.args[1] for call in app.add_directive_to_domain.call_args_list if call.args[0] == "report"}
		)
		app.add_latex_package.assert_called_once_with("pdflscape")
		transformations = [call.args[0] for call in app.add_post_transform.call_args_list]
		self.assertEqual(list(ReportDomain.transformations), transformations)
		self.assertEqual(CONFIG_VALUES, {call.args[0] for call in app.add_config_value.call_args_list})
		self.assertEqual(__version__, metadata["version"])

	@testcase("Core extension without pyEDAA.Reports")
	def CoreWithoutReports(self) -> None:
		"""
		Setting up 'pyTooling.Sphinx' alone doesn't import pyEDAA.Reports.

		Runs a Python process that sets up the core extension with a mocked application, and checks 'sys.modules'.
		"""
		script = dedent("""\
			import sys
			from unittest.mock import MagicMock

			import pyTooling.Sphinx

			pyTooling.Sphinx.setup(MagicMock())
			assert not any(name.startswith("pyEDAA") for name in sys.modules), "pyEDAA.Reports was imported"
			assert "pyTooling.Sphinx.Report" not in sys.modules, "pyTooling.Sphinx.Report was imported"
		""")
		root = Path(__file__).parent.parent.parent.parent
		result = subprocess_run(
			[executable, "-c", script], cwd=root, env=environ.copy(), capture_output=True, text=True, check=False
		)

		self.assertEqual(0, result.returncode, result.stderr)

	@testcase("Missing report file")
	def MissingReport(self) -> None:
		"""
		A report file that doesn't exist is logged as an error when the configuration is checked.

		Builds a project declaring a missing unit test report and checks the error.
		"""
		self._build(
			"Index\n#####\n", extension="pyTooling.Sphinx.Report",
			pyTooling_Unittest_Testsuites={"ut": {"xml_report": "missing.xml"}}
		)

		self.assertEqual(
			[
				"ERROR: Caught ReportExtensionError when checking configuration variables.",
				"  conf.py: pyTooling_Unittest_Testsuites:[ut].xml_report: Unittest report file 'missing.xml' doesn't exist."
			],
			self._warningLines()
		)


@testsuite("Reports in a document")
class Rendering(ReportProject):
	"""What the directives put into a built page, in HTML and in LaTeX."""

	_document = dedent("""\
		Index
		#####

		.. report:unittest-summary::
		   :reportid: ut

		.. report:code-coverage::
		   :reportid: cov

		.. report:code-coverage-legend::
		   :reportid: cov
		   :style: vertical-table

		.. report:doc-coverage::
		   :reportid: doc

		.. report:doc-coverage-legend::
		   :reportid: doc
	""")

	@testcase("HTML")
	def HTML(self) -> None:
		"""
		Each directive renders its table, with the CSS classes of the stylesheet.

		Builds a document using five directives and checks the tables' and rows' classes and a testcase's name.
		"""
		self._buildReport(self._document)

		self.assertEqual([], self._warningLines())
		html = self._html("index")
		self.assertIn('class="report-unittest-table report-unittest-ut docutils', html)
		self.assertIn('class="report-testcase testcase-failed', html)
		self.assertIn("test_ByZero", html)
		self.assertIn('class="report-codecov-table report-codecov-cov docutils', html)
		self.assertIn('class="report-module report-cov-below50', html)
		self.assertIn('class="report-codecov-legend docutils', html)
		self.assertIn('class="report-doccov-table report-doccov-doc docutils', html)
		self.assertIn('class="report-doccov-legend docutils', html)

	@testcase("LaTeX")
	def LaTeX(self) -> None:
		"""
		LaTeX puts the unit test and code coverage tables on landscape pages, with the column widths stated.

		Builds the document as LaTeX and checks the landscape environments, the package and the column specification.
		"""
		self._buildReport(self._document, "latex")

		self.assertEqual([], self._warningLines())
		latex = next((self._path / "build" / "latex").glob("*.tex")).read_text(encoding="utf-8")
		self.assertEqual(2, latex.count("\\begin{landscape}"))
		self.assertEqual(2, latex.count("\\end{landscape}"))
		self.assertIn("\\usepackage{pdflscape}", latex)

	@testcase("Unknown report")
	def UnknownReport(self) -> None:
		"""
		A directive naming a report that isn't configured reports it on the page and in the log.

		Builds a unit test summary with an unknown report ID and checks the page's message.
		"""
		self._buildReport("Index\n#####\n\n.. report:unittest-summary::\n   :reportid: unknown\n")

		self.assertIn("<p>Caught ReportExtensionError when checking options for directive", self._html("index"))
		self.assertIn(
			"ERROR: Caught ReportExtensionError when checking options for directive 'unittest-summary'.",
			"\n".join(self._warningLines())
		)
