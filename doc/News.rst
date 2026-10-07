.. _NEWS:

News
####

See :gh:`pyTooling.Sphinx Release Pages <pyTooling/pyTooling.Sphinx/releases>` for detail release
notes on every release.


Version 0.x (2026)
******************

.. topic:: :gh:`v0.1.0 - unreleased <pyTooling/pyTooling.Sphinx/releases/v0.1.0>`

   .. rubric:: New Features

   * First release: pyTooling's Sphinx extension :mod:`pyTooling.Sphinx` becomes a package of its own (formerly
     developed as part of :doc:`pyTooling <pyTool:index>` v10.0.0).
   * Roles: :ref:`style roles <ROLE/Style>`, :ref:`inline Python code <ROLE/PythonCode>`, and
     :ref:`line break and horizontal rule <ROLE/Breaks>` in HTML and LaTeX.
   * Directives: :ref:`condensed-class <DIR/CondensedClass>`,
     :ref:`dependency-table <DIR/DependencyTable>`, :ref:`xmlschema-graph <DIR/XMLSchemaGraph>`,
     :ref:`shields <DIR/Shields>`, :ref:`tree <DIR/Tree>` and :ref:`abbreviations <DIR/Abbreviations>` with the
     abbreviation roles ``:acs:``, ``:acl:``, ``:acf:`` and their plurals.
   * :class:`~pyTooling.Sphinx.SchemaGraph.DotGraph` is built on :mod:`pyTooling.Graph.GraphViz`.
   * Domain ``report`` from :gh:`sphinx-reports <pyTooling/sphinx-reports>` (v0.11.2), with the directives
     :ref:`report:unittest-summary <DIR/UnittestSummary>`, :ref:`report:code-coverage <DIR/CodeCoverage>` and
     :ref:`report:doc-coverage <DIR/DocCoverage>`. Reading a report needs the extra ``reports``.
   * A unit test report declared with ``pages`` gets a
     :ref:`page per testsuite and testcase <DIR/UnittestSummary/Pages>`, generated without source files, linked
     from the summary table and listed in the navigation below the summary's page, and the roles
     :ref:`:tc: and :ts: <DIR/UnittestSummary/Roles>` refer to them. A report may be in
     :ref:`pyTooling's XML format <DIR/UnittestSummary/Formats>` too.
   * A code coverage report is read with pyEDAA.Reports' language-neutral model, from
     :ref:`Cobertura XML or coverage.py's JSON report <DIR/CodeCoverage/Formats>`, and shown per directory and source
     file. Declared with ``pages`` and ``sources``, it gets a
     :ref:`page per directory and source file <DIR/CodeCoverage/Pages>`; a file's page shows its source, syntax
     highlighted with Pygments, each line marked by its coverage state. The role
     :ref:`:cov: <DIR/CodeCoverage/Role>` refers to a page, optionally to a line, and the directive
     :ref:`report:file-coverage <DIR/CodeCoverage/FileCoverage>` shows a file's listing anywhere.

   .. rubric:: Changes compared to sphinx-reports

   * The domain is registered by the extension ``pyTooling.Sphinx`` instead of ``sphinx_reports``; it is still
     ``report``.
   * The configuration values are renamed: ``report_unittest_testsuites`` |rarr| ``pyTooling_Unittest_Testsuites``,
     ``report_codecov_packages``/``report_codecov_levels`` |rarr|
     ``pyTooling_CodeCoverage_Packages``/``pyTooling_CodeCoverage_Levels``, and
     ``report_doccov_packages``/``report_doccov_levels`` |rarr|
     ``pyTooling_DocCoverage_Packages``/``pyTooling_DocCoverage_Levels``.
   * ``report:dependency-table`` is dropped in favour of :ref:`dependency-table <DIR/DependencyTable>`.
   * ``report:code-coverage`` shows directories and files instead of Python packages and modules, and reads
     Cobertura XML too; the prototype ``report:module-coverage`` is replaced by
     :ref:`report:file-coverage <DIR/CodeCoverage/FileCoverage>`.
   * The report styles are part of the stylesheet of :mod:`pyTooling.Sphinx`, and a theme's row stripes are reset for
     the report tables only, no longer for every table.
   * A legend in style ``horizontal-table`` renders.
