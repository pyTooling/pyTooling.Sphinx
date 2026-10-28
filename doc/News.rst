.. _NEWS:

News
####

See :gh:`pyTooling.Sphinx Release Pages <pyTooling/pyTooling.Sphinx/releases>` for detail release
notes on every release.


Version 0.x (2026)
******************

.. topic:: :gh:`v0.1.0 - unreleased <pyTooling/pyTooling.Sphinx/releases/v0.1.0>`

   .. rubric:: New Features

   * First release: pyTooling's Sphinx extension :mod:`pyTooling.Sphinx` becomes a package of its own. It was
     developed in the ``dev`` branch of :doc:`pyTooling <pyTool:index>` and moved here before any pyTooling release
     contained it.
   * Python 3.12 to 3.15 (Sphinx 9.1 requires Python 3.12); the extras :ref:`reports <DEP/reports>` and
     :ref:`markdown <DEP/markdown>` install the optional requirements.
   * Roles: :ref:`style roles <ROLE/Style>`, :ref:`inline Python code <ROLE/PythonCode>`, and
     :ref:`line break and horizontal rule <ROLE/Breaks>` in HTML and LaTeX.
   * Directives: :ref:`condensed-class <DIR/CondensedClass>`,
     :ref:`dependency-table <DIR/DependencyTable>`, :ref:`xmlschema-graph <DIR/XMLSchemaGraph>`,
     :ref:`shields <DIR/Shields>`, :ref:`tree <DIR/Tree>` and :ref:`abbreviations <DIR/Abbreviations>` with the
     abbreviation roles ``:acs:``, ``:acl:``, ``:acf:`` and their plurals.
   * A :ref:`dependency-table <DIR/DependencyTable>` limited by ``:depth:`` marks each package whose dependencies
     weren't expanded.
   * A :ref:`dependency-table <DIR/DependencyTable>` reports a broken requirement line, also one in a file included
     with ``-r``, a warning of a release's details and a warning from loading a project as a Sphinx warning. A package
     whose license needs an override is reported once, by its canonical name - the key the override file is looked up
     by.
   * A :ref:`dependency-table <DIR/DependencyTable>` resolves the requirements with pyTooling's
     :class:`~pyTooling.Dependency.Resolver.Resolver`, which downloads the packages of one level in parallel; a
     requirement naming extras lists their requirements too.
   * A :ref:`dependency-table <DIR/DependencyTable>` lists the build requirements of a :file:`pyproject.toml` file,
     declared with the entrypoint field ``pyproject``.
   * A :ref:`tree <DIR/Tree>` explains its icons in a :ref:`legend <DIR/Tree/Legend>`: an icon option takes a text
     behind a ``|``, and ``:legend:`` draws the legend above or below the tree.
   * A :ref:`tree <DIR/Tree>` entry may have a :ref:`description <DIR/Tree/Descriptions>` behind a ``|``, drawn as a
     second, aligned column.
   * Directive :ref:`unicode-table <DIR/UnicodeTable>`: icons with their Unicode names and code points, computed with
     :mod:`unicodedata`; in HTML, a button copies an icon or its code points into the clipboard. It lists the
     :ref:`icons commonly used in a tree <DIR/Tree/CommonIcons>`. A tree's icon option rejects a surrogate code point.
   * :class:`~pyTooling.Sphinx.SchemaGraph.DotGraph` is built on :mod:`pyTooling.Graph.GraphViz`.
   * :ref:`xmlschema-graph <DIR/XMLSchemaGraph>` draws a schema shipped in a package with the option ``:package:``.
   * Domain ``report`` from :gh:`sphinx-reports <pyTooling/sphinx-reports>` (v0.11.2), with the directives
     :ref:`report:unittest-summary <DIR/UnittestSummary>`, :ref:`report:code-coverage <DIR/CodeCoverage>` and
     :ref:`report:doc-coverage <DIR/DocCoverage>`. Reading a report needs the extra ``reports``.
   * The domain ``report`` takes part in a parallel build (``sphinx-build -j N``).
   * A package's ``levels`` may be a palette of its own, a dictionary checked like the palettes in
     ``pyTooling_CodeCoverage_Levels`` or ``pyTooling_DocCoverage_Levels``.
   * A unit test report declared with ``pages`` gets a
     :ref:`page per testsuite and testcase <DIR/UnittestSummary/Pages>`, generated without source files, linked
     from the summary table and listed in the navigation below the summary's page, and the roles
     :ref:`:tc: and :ts: <DIR/UnittestSummary/Roles>` refer to them. A report may be in
     :ref:`pyTooling's XML format <DIR/UnittestSummary/Formats>` too.
   * A project :ref:`derives its own unit test table <DIR/UnittestSummary/Deriving>` from
     :class:`~pyTooling.Sphinx.Unittest.UnittestSummaryBase`, its columns declared as
     :class:`~pyTooling.Sphinx.Unittest.Column` and :class:`~pyTooling.Sphinx.Unittest.ColumnGroup`; its pages
     extend :class:`~pyTooling.Sphinx.UnittestPages.UnittestReportPages`, and a domain of its own with roles of its
     own derives from :class:`~pyTooling.Sphinx.ReportDomain`.
   * A unit test summary explains its status symbols in a :ref:`legend <DIR/UnittestSummary/Legend>` below the
     table; ``:legend:`` draws it above the table or leaves it out.
   * A code coverage report is read with pyEDAA.Reports' language-neutral model, from
     :ref:`Cobertura XML or coverage.py's JSON report <DIR/CodeCoverage/Formats>`, and shown per directory and source
     file. Declared with ``pages`` and ``sources``, it gets a
     :ref:`page per directory and source file <DIR/CodeCoverage/Pages>`; a file's page shows its source, syntax
     highlighted with Pygments, each line marked by its coverage state. The role
     :ref:`:cov: <DIR/CodeCoverage/Role>` refers to a page, optionally to a line, and the directive
     :ref:`report:file-coverage <DIR/CodeCoverage/FileCoverage>` shows a file's listing anywhere.
   * A package's documentation coverage is :ref:`analyzed <DIR/DocCoverage/Analysis>` by pyEDAA.Reports'
     language-neutral model and its Python reader, which counts fields and variables too; ``docstr_coverage`` isn't
     needed anymore. A package declared with ``pages`` gets a
     :ref:`page per package and module <DIR/DocCoverage/Pages>`; a module's page shows its source condensed to the
     decorators, signatures and doc-strings of its classes and functions - bodies elided to ``...`` - and its fields
     and variables, each marked by its documentation state. The role :ref:`:doccov: <DIR/DocCoverage/Role>` refers to
     a page.
   * :ref:`External link icons <LINK/External>`: in HTML, an icon behind each external link, chosen by its target -
     GitHub's mark, GitLab's tanuki, the logos of Python, NumPy, PyPy, pytest, Pydantic, Read the Docs and
     Sphinx, an envelope for an e-mail address, or a square with an arrow; a link of the ``:download:`` role gets a
     download icon, a link to an archive an archive icon. The configuration value ``pyTooling_ExternalLink_Icons``
     adds the intersphinx links or disables the icons, and ``pyTooling_ExternalLink_Hosts`` adds hosts. A link with an
     icon opens in a new browser tab, unless ``pyTooling_ExternalLink_NewTab`` is ``False``.
   * :ref:`Download sizes <LINK/External/Downloads>`: a download's file size follows its link, for an archive with its
     format, e.g. *(ZIP, 1.2 MiB)*; another site's file is asked for with an HTTP ``HEAD`` request, if its URI matches
     a pattern of ``pyTooling_ExternalLink_RemoteSizes``. ``pyTooling_ExternalLink_DownloadSizes`` switches the sizes
     off, ``pyTooling_ExternalLink_RemoteSizeTimeout`` sets the time to wait for an answer.
   * :mod:`pyTooling.Sphinx.GitHubMarkdown` converts GitHub-flavoured Markdown into docutils nodes - GitHub alerts as
     admonitions, task lists, tables, footnotes, linked GitHub references and emoji -, installed with the extra
     :ref:`markdown <DEP/markdown>`.
   * For LaTeX, ``latex_table_style`` defaults to ``["booktabs"]`` and ``latex_elements["maxlistdepth"]`` to ``"10"``,
     unless :file:`conf.py` or ``-D`` sets them.

   .. rubric:: Breaking Changes

   .. attention::

      **Migrating from** :gh:`sphinx-reports <pyTooling/sphinx-reports>` **v0.11.2:** pyTooling.Sphinx takes over its
      domain ``report``. These items break a documentation set up for sphinx-reports; a project new to
      pyTooling.Sphinx isn't affected.

      * ⚠️ Package and extension: ``pip install sphinx-reports`` |rarr| ``pip install pyTooling.Sphinx[reports]``;
        ``extensions = ["sphinx_reports"]`` |rarr| ``extensions = ["pyTooling.Sphinx"]``.
      * ⚠️ Configuration values in :file:`conf.py`: ``report_unittest_testsuites`` |rarr|
        ``pyTooling_Unittest_Testsuites``, ``report_codecov_packages`` |rarr| ``pyTooling_CodeCoverage_Packages``,
        ``report_codecov_levels`` |rarr| ``pyTooling_CodeCoverage_Levels``, ``report_doccov_packages`` |rarr|
        ``pyTooling_DocCoverage_Packages``, ``report_doccov_levels`` |rarr| ``pyTooling_DocCoverage_Levels``.
      * ⚠️ Directive ``report:module-coverage`` |rarr| :ref:`report:file-coverage <DIR/CodeCoverage/FileCoverage>`.
      * ⚠️ Directive ``report:dependency-table`` is removed; the directive
        :ref:`dependency-table <DIR/DependencyTable>` renders an entrypoint's requirements, configured in
        :file:`conf.py`.

   .. rubric:: Changes compared to sphinx-reports

   * ⚠️ The domain is registered by the extension ``pyTooling.Sphinx`` instead of ``sphinx_reports``; it is still
     ``report``.
   * ⚠️ The configuration values are renamed: ``report_unittest_testsuites`` |rarr| ``pyTooling_Unittest_Testsuites``,
     ``report_codecov_packages``/``report_codecov_levels`` |rarr|
     ``pyTooling_CodeCoverage_Packages``/``pyTooling_CodeCoverage_Levels``, and
     ``report_doccov_packages``/``report_doccov_levels`` |rarr|
     ``pyTooling_DocCoverage_Packages``/``pyTooling_DocCoverage_Levels``.
   * ⚠️ ``report:dependency-table`` is dropped in favour of :ref:`dependency-table <DIR/DependencyTable>`.
   * ⚠️ ``report:code-coverage`` shows directories and files instead of Python packages and modules, and reads
     Cobertura XML too; the prototype ``report:module-coverage`` is replaced by
     :ref:`report:file-coverage <DIR/CodeCoverage/FileCoverage>`.
   * The report styles are part of the stylesheet of :mod:`pyTooling.Sphinx`, and a theme's row stripes are reset for
     the report tables only, no longer for every table.
   * A report table indents a name by markup instead of em quads, so a wrapped name stays at its indentation and a
     copied name has no leading spaces; ``--pyTooling-report-indentation`` (HTML) and
     ``\pyToolingReportIndentationStep`` (LaTeX) set the step.
   * A legend in style ``horizontal-table`` renders.
   * An invalid ``levels`` is reported with a message; it was empty.
