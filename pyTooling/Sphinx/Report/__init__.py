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
# Copyright 2023-2026 Patrick Lehmann - Bötzingen, Germany                                                             #
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
A Sphinx extension adding the domain ``report``: unit test results, code coverage and documentation coverage as
tables in the documentation.

The reports are read by :mod:`pyEDAA.Reports`, so this extension needs the extra ``reports`` -
``pip install pyTooling.Sphinx[reports]`` - and is enabled separately from :mod:`pyTooling.Sphinx`, which it sets up
itself:

.. code-block:: Python

   # doc/conf.py
   extensions = [
     ...,
     "pyTooling.Sphinx.Report",
   ]

.. rubric:: What it registers

* the **directives** of domain ``report``:

  * :rst:dir:`report:unittest-summary` - a unit test report, per testsuite and testcase;
  * :rst:dir:`report:code-coverage` and :rst:dir:`report:code-coverage-legend` - a code coverage report, per package
    and module, and its coverage levels;
  * :rst:dir:`report:doc-coverage` and :rst:dir:`report:doc-coverage-legend` - a package's documentation coverage,
    per package and module, and its coverage levels;
  * ``report:module-coverage`` - a prototype of a module's source code with its coverage.

* the **configuration values** in :file:`conf.py`, which declare the reports a directive names by its ``:reportid:``:

  * ``pyTooling_Unittest_Testsuites``
  * ``pyTooling_CodeCoverage_Packages`` and ``pyTooling_CodeCoverage_Levels``
  * ``pyTooling_DocCoverage_Packages`` and ``pyTooling_DocCoverage_Levels``

* the LaTeX package ``pdflscape``, for the :class:`~pyTooling.Sphinx.Node.Landscape` node the wide tables are put in,
  and the post-transform :class:`~pyTooling.Sphinx.Report.Workaround.FixLatexTableWidths`.

The domain has no roles and no indices. Its stylesheet is part of :mod:`pyTooling.Sphinx`'s.

.. seealso::

   :ref:`DIR/UnittestSummary`
      |rarr| The unit test summary's options and configuration.
   :ref:`DIR/CodeCoverage`
      |rarr| The code coverage directives' options and configuration.
   :ref:`DIR/DocCoverage`
      |rarr| The documentation coverage directives' options and configuration.
"""
from enum                               import Flag
from typing                             import Any, ClassVar, Optional as Nullable

from docutils.nodes                     import Element
from sphinx.addnodes                    import pending_xref
from sphinx.application                 import Sphinx
from sphinx.builders                    import Builder
from sphinx.config                      import Config
from sphinx.domains                     import Domain
from sphinx.environment                 import BuildEnvironment
from sphinx.transforms.post_transforms  import SphinxPostTransform
from sphinx.util.logging                import getLogger

from pyTooling.Decorators               import export

from pyTooling.Sphinx                   import __version__, SphinxExtensionError
from pyTooling.Sphinx.Report.Workaround import FixLatexTableWidths


__all__ = ["INDENTATION"]

#: The character a report table indents an entry by, per level of the hierarchy: an em quad, which HTML keeps.
INDENTATION = "\u2001"


@export
class ReportExtensionError(SphinxExtensionError):
	"""
	The exception raised by the ``report`` domain, e.g. for a mistake in its configuration values or options.
	"""


@export
class ReportsPackageMissingError(ReportExtensionError):
	"""
	The exception raised when a report is read, but the optional packages of the extra ``reports`` aren't installed.

	The message names what was attempted and the packages it needs; a note says how to install them.
	"""

	def __init__(self, task: str, packages: str = "'pyEDAA.Reports'") -> None:
		"""
		Initialize the exception with what was attempted and the packages it needs.

		:param task:     What needs the packages, e.g. ``Reading a unit test report``.
		:param packages: Optional, the packages needed, quoted. Default: ``'pyEDAA.Reports'``.
		"""
		super().__init__(f"{task} needs {packages}, which isn't installed.")
		self.add_note("Install it with: pip install pyTooling.Sphinx[reports]")


@export
class LegendStyle(Flag):
	"""
	How a legend directive lays out the coverage levels; a document writes the members' names with dashes.
	"""

	Default =    0     #: No style.
	Table =      1     #: A table.

	Horizontal = 1024  #: A column per level.
	Vertical =   2048  #: A row per level.

	horizontal_table = Table | Horizontal  #: A table with a column per level, written ``horizontal-table``.
	vertical_table =   Table | Vertical    #: A table with a row per level, written ``vertical-table``.


@export
class ReportDomain(Domain):
	"""
	The Sphinx domain ``report``, integrating reports and summaries into a Sphinx documentation.

	Its directives are registered by :func:`setup`, and read their reports from the files declared in :file:`conf.py`.
	"""

	name =  "report"  #: Name of the domain, the prefix of its directives.
	label = "rpt"     #: Name of the domain, as displayed.

	latexPackages:   ClassVar[tuple[str, ...]] = ("pdflscape", )  #: LaTeX packages the domain's output needs.
	transformations: ClassVar[tuple[type[SphinxPostTransform], ...]] = (FixLatexTableWidths, )  #: Post-transforms.

	def resolve_xref(
		self,
		env: BuildEnvironment,
		fromdocname: str,
		builder: Builder,
		typ: str,
		target: str,
		node: pending_xref,
		contnode: Element
	) -> Nullable[Element]:
		"""
		Resolve a cross-reference of this domain, which has none: the domain has no roles and no objects.

		Raises :exc:`NotImplementedError` always. Sphinx doesn't call it, as no role creates a reference of this domain.

		:param env:         The build environment.
		:param fromdocname: Name of the document the reference is in.
		:param builder:     The builder.
		:param typ:         Type of the reference.
		:param target:      Target of the reference.
		:param node:        The pending cross-reference.
		:param contnode:    The node holding the reference's text.
		:returns:           Never.
		"""
		raise NotImplementedError()


@export
def checkConfiguration(sphinx: Sphinx, config: Config) -> None:
	"""
	Call-back for Sphinx' ``config-inited`` event, checking the configuration values and loading the reports' settings.

	A mistake is logged as an error rather than stopping the build; a directive naming that report fails on its own.

	:param sphinx: The Sphinx application.
	:param config: The configuration, after :file:`conf.py` was read.
	"""
	from pyTooling.Sphinx.Report.CodeCoverage import CodeCoverageBase
	from pyTooling.Sphinx.Report.DocCoverage  import DocCoverageBase
	from pyTooling.Sphinx.Report.Unittest     import UnittestSummary

	checkConfigurations = (
		CodeCoverageBase.CheckConfiguration,
		DocCoverageBase.CheckConfiguration,
		UnittestSummary.CheckConfiguration,
	)

	for check in checkConfigurations:
		try:
			check(sphinx, config)
		except ReportExtensionError as ex:
			getLogger(__name__).error(f"Caught {ex.__class__.__name__} when checking configuration variables.\n  {ex}")


@export
def readReports(sphinx: Sphinx) -> None:
	"""
	Call-back for Sphinx' ``builder-inited`` event, reading the report files.

	:param sphinx: The Sphinx application.
	"""
	from pyTooling.Sphinx.Report.CodeCoverage import CodeCoverageBase
	from pyTooling.Sphinx.Report.Unittest     import UnittestSummary

	CodeCoverageBase.ReadReports(sphinx)
	UnittestSummary.ReadReports(sphinx)


@export
def setup(sphinx: Sphinx) -> dict[str, Any]:
	"""
	Register the domain ``report``, its directives, configuration values, LaTeX packages and post-transforms with Sphinx.

	The directives derive from :class:`~pyTooling.Sphinx.BaseDirective` and put their tables into
	:class:`~pyTooling.Sphinx.Node.Landscape` nodes, and the stylesheet is :mod:`pyTooling.Sphinx`'s, so the extension
	:mod:`pyTooling.Sphinx` is set up first.

	:param sphinx: The Sphinx application to register with.
	:returns:      The extension's metadata.
	"""
	from pyTooling.Sphinx.Report.CodeCoverage import CONFIG_PREFIX as CODE_COVERAGE_PREFIX
	from pyTooling.Sphinx.Report.CodeCoverage import CodeCoverage, CodeCoverageBase, CodeCoverageLegend, ModuleCoverage
	from pyTooling.Sphinx.Report.DocCoverage  import CONFIG_PREFIX as DOC_COVERAGE_PREFIX
	from pyTooling.Sphinx.Report.DocCoverage  import DocCoverageBase, DocCoverageLegend, DocStrCoverage
	from pyTooling.Sphinx.Report.Unittest     import CONFIG_PREFIX as UNITTEST_PREFIX
	from pyTooling.Sphinx.Report.Unittest     import UnittestSummary

	sphinx.setup_extension("pyTooling.Sphinx")

	sphinx.add_domain(ReportDomain)

	directives = {
		"code-coverage":        CodeCoverage,
		"code-coverage-legend": CodeCoverageLegend,
		"module-coverage":      ModuleCoverage,
		"doc-coverage":         DocStrCoverage,
		"doc-coverage-legend":  DocCoverageLegend,
		"unittest-summary":     UnittestSummary,
	}
	for directiveName, directive in directives.items():
		sphinx.add_directive_to_domain(ReportDomain.name, directiveName, directive)

	for latexPackage in ReportDomain.latexPackages:
		sphinx.add_latex_package(latexPackage)

	for transformation in ReportDomain.transformations:
		sphinx.add_post_transform(transformation)

	for prefix, configValues in (
		(CODE_COVERAGE_PREFIX, CodeCoverageBase.configValues),
		(DOC_COVERAGE_PREFIX,  DocCoverageBase.configValues),
		(UNITTEST_PREFIX,      UnittestSummary.configValues),
	):
		for configName, (default, rebuild, types) in configValues.items():
			sphinx.add_config_value(f"{prefix}_{configName}", default, rebuild, types)

	sphinx.connect("config-inited", checkConfiguration)
	sphinx.connect("builder-inited", readReports)

	return {"version": __version__, "parallel_read_safe": True, "parallel_write_safe": True}
