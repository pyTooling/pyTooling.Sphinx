.. _DIR/CodeCoverage:

report:code-coverage
####################

.. grid:: 2

   .. grid-item::
      :columns: 6

      The ``report:code-coverage`` directive renders a code coverage report as a table: a row per directory and source
      file, with the line and branch coverage. The hierarchy is shown by indentation, a directory by 📁 and a file by
      📄, and each row is coloured by its coverage level. ``report:code-coverage-legend`` renders the coverage levels.

      A report is a :ref:`Cobertura XML file <DIR/CodeCoverage/Formats>` - written for any language, e.g. by
      coverage.py or gcovr - or coverage.py's JSON report. Report files are declared in :file:`conf.py`, each with an
      identifier the directives name in their :rst:dir:`report:code-coverage:reportid` option - so a documentation
      shows as many reports as it declares.

      A report can get a :ref:`page per directory and source file <DIR/CodeCoverage/Pages>`: a file's page shows its
      source, syntax highlighted, each line marked by its coverage state. The table links to the pages, and the role
      :rst:role:`cov` refers to them.

      The directives are part of :mod:`pyTooling.Sphinx`; they need the
      :ref:`extra reports <DIR/UnittestSummary/Setup>`.

   .. grid-item::
      :columns: 6

      .. code-block:: ReST

         .. grid:: 2

            .. grid-item::
               :columns: 8

               .. report:code-coverage::
                  :reportid: example

            .. grid-item::
               :columns: 4

               .. report:code-coverage-legend::
                  :reportid: example
                  :style:    vertical-table

This is how the example renders, from coverage.py's report of a Python package with one sub-package. The report is
declared with :ref:`pages <DIR/CodeCoverage/Pages>`, so every directory and file links to its page:

.. grid:: 2

   .. grid-item::
      :columns: 8

      .. report:code-coverage::
         :reportid: example

   .. grid-item::
      :columns: 4

      .. report:code-coverage-legend::
         :reportid: example
         :style:    vertical-table

The same directive renders a Cobertura report of a VHDL design:

.. report:code-coverage::
   :reportid: vhdl

The documentation's own :doc:`code coverage report <../CodeCoverage>` is rendered by these directives too.


.. _DIR/CodeCoverage/Configuration:

Configuration
*************

The report files are declared in :file:`conf.py` as a dictionary, keyed by the identifier a directive names in
:rst:dir:`report:code-coverage:reportid`. A path is relative to the documentation's source directory.

``pyTooling_CodeCoverage_Packages``
  |rarr| The code coverage reports, by identifier. An entry has these fields:

  ``name``
    |rarr| The name of the measured project, shown in the first row.
  ``xml_report`` or ``json_report``
    |rarr| The report file: a :ref:`Cobertura XML file <DIR/CodeCoverage/Formats>`, or coverage.py's JSON report.
    Exactly one of both.
  ``sources``
    |rarr| The directory the report's file paths are relative to, from which a file's source is read. Optional;
    required with ``pages``.
  ``pages``
    |rarr| The document name the :ref:`pages per directory and source file <DIR/CodeCoverage/Pages>` are generated
    below, e.g. ``coverage/src``. Optional; without it, the report gets no pages.
  ``fail_below``
    |rarr| An integer in range 0..100: the coverage in percent below which the package fails.
  ``levels``
    |rarr| The name of a palette in ``pyTooling_CodeCoverage_Levels``, e.g. ``"default"``.

``pyTooling_CodeCoverage_Levels``
  |rarr| The palettes of coverage levels, by name. A palette maps an upper limit in percent to a CSS class and a
  description, and needs a level ``100`` and a level ``"error"``. Default: the palette ``default``, of 12 levels
  from ≤10 % to ≤100 %, coloured from blue via red, orange and yellow to green.

.. code-block:: Python

   # doc/conf.py
   pyTooling_CodeCoverage_Packages = {
     "src": {
       "name":        "myPackage",
       "json_report": "../report/coverage/coverage.json",
       "sources":     "..",
       "pages":       "coverage/src",
       "fail_below":  80,
       "levels":      "default"
     },
     "vhdl": {
       "name":        "myDesign",
       "xml_report":  "../report/coverage/cobertura.xml",
       "sources":     "../src",
       "pages":       "coverage/vhdl",
       "fail_below":  80,
       "levels":      "default"
     }
   }

The first entry is the default report of the role :rst:role:`cov`.

A palette of its own:

.. code-block:: Python

   # doc/conf.py
   pyTooling_CodeCoverage_Levels = {
     "coarse": {
       50:      {"class": "report-cov-below50",  "desc": "poorly used"},
       80:      {"class": "report-cov-below80",  "desc": "somehow used"},
       100:     {"class": "report-cov-below100", "desc": "well used"},
       "error": {"class": "report-cov-error",    "desc": "internal error"},
     }
   }

The configuration is checked when the build starts. A report file that doesn't exist is logged as an error, and the
entries after it aren't read: an entry whose file is written later - e.g. by a test run in CI - goes last.


.. _DIR/CodeCoverage/Formats:

Report formats
**************

A report is read with the code coverage data model of :gh:`pyEDAA.Reports <edaa-org/pyEDAA.Reports>`: directories
and source files, built from the file paths the report names, and per file the coverage of its executable lines.

``xml_report``: Cobertura XML
  |rarr| Written by many tools for any language, e.g. coverage.py (``coverage xml``) for Python or gcovr
  (``--cobertura``) for C, C++ and other languages compiled by GCC. A file's path is relative to one of the report's
  ``<source>`` directories, so ``sources`` names that directory. A line has hits - how often it ran -, and a branching
  line the number of its taken branches. The format has no excluded lines.

``json_report``: coverage.py's JSON report
  |rarr| Written by ``coverage json``. A file's path is relative to the directory coverage.py ran in. A line has no
  hits; excluded lines - e.g. marked ``# pragma: no cover`` - are listed.

.. hint::

   coverage.py writes both formats from one measurement, naming the files differently: Cobertura relative to the
   measured source directory - e.g. ``Shapes.py`` -, JSON relative to the directory coverage.py ran in - e.g.
   ``myPackage/Shapes.py``.

The table shows a directory's and a file's lines - executable, excluded, covered, missing - and branches - all,
covered, partially covered lines, missing -, each with its coverage. A chain of directories holding no file and one
directory each - e.g. ``pyTooling/Sphinx`` - is one row.


.. _DIR/CodeCoverage/Pages:

Pages per directory and source file
***********************************

A report declared with the key ``pages`` gets a page per directory and per source file. They are generated when the
documentation is built - no source file is written - below the document name the key states, named by the path in
the report, e.g. ``coverage/vhdl/src/Counter.vhdl``. A chain of directories holding no file and one directory each is
one page, e.g. ``coverage/src/pyTooling_Sphinx``.

A **directory's page** shows its line and branch coverage and its parent directory; then a table of its directories
and a table of its files, each linked to its page.

A **source file's page** shows its line and branch coverage, its parent directory and its missed lines, e.g.
``8, 14-17``; then its **listing**. The source is read from the report's ``sources`` directory, and syntax highlighted
with the Pygments lexer of the file's name - every language Pygments knows, e.g. Python, VHDL, Verilog, C, C++,
Java, Rust, Go, Tcl or Bash; a file without a lexer is shown as plain text. The colors are those of Sphinx'
Pygments style, as of every code block. Each line is marked by its coverage state:

.. list-table::
   :header-rows: 1
   :widths: 20 80

   * - State
     - Line
   * - ``covered``
     - The line ran, and all of its branches - if it has any - were taken.
   * - ``partial``
     - The line ran, but not all of its branches were taken; on hover, it says how many were.
   * - ``uncovered``
     - The line never ran.
   * - ``excluded``
     - The line is excluded from the measurement.
   * - (none)
     - The line isn't executable: a comment, a declaration, an empty line.

A line's number and - if the report has them - its hits are written in front of it. A line has the ID
``L<number>``, so the role :rst:role:`cov` links to it.

The report must have been measured on the source as it is: a report naming a line beyond a file's end is warned about.

The :rst:dir:`report:code-coverage` directive lists the top-level directories and files in a hidden table of contents,
and a directory's page lists its directories and files, so the pages are in the navigation below the table's
document. LaTeX writes the pages too, below the table's section; a listing's line numbers are colored by the coverage
state, followed by a marker: ``+`` covered, ``~`` partial, ``-`` uncovered, ``x`` excluded.

Sphinx regards the report file as the source of its pages, so a changed report regenerates its pages.

.. hint::

   A file is as many levels below the table's document as its path has directories. A theme limits how deep its
   navigation goes, e.g. the option ``navigation_depth`` of the *Read the Docs* theme (default 4; ``-1`` =
   unlimited).


.. _DIR/CodeCoverage/Role:

Role
****

.. rst:role:: cov

   Refers to a directory's or source file's page, showing its name, or the role's title: ``:cov:`<target>``` or
   ``:cov:`title <<target>>```. It is registered in domain ``report`` - as ``:report:cov:`` - and without the domain's
   prefix.

   The target is ``[<report ID>:]<path>[#<line>]``. The path is the one in the report, e.g. ``src/Counter.vhdl``. A
   suffix of it starting at a name - ``Counter.vhdl`` - is accepted, if it's unique. Without a report ID, the first
   report of ``pyTooling_CodeCoverage_Packages`` is meant. A line number links to the line of a file's listing, and
   is shown behind the file's name.

   A target matching nothing or several directories and files is warned about.

.. grid:: 2

   .. grid-item::
      :columns: 6

      .. code-block:: ReST

         * :cov:`Shapes.py`
         * :cov:`myPackage/Units`
         * :cov:`vhdl:Counter.vhdl`
         * :cov:`vhdl:Counter.vhdl#27`
         * :cov:`the reset branch <vhdl:src/Counter.vhdl#26>`

   .. grid-item::
      :columns: 6

      * :cov:`Shapes.py`
      * :cov:`myPackage/Units`
      * :cov:`vhdl:Counter.vhdl`
      * :cov:`vhdl:Counter.vhdl#27`
      * :cov:`the reset branch <vhdl:src/Counter.vhdl#26>`

The directories and files are objects of domain ``report`` of type ``source``, named ``<report ID>:<path>`` in the
documentation's inventory (:file:`objects.inv`), so another documentation refers to them with ``intersphinx``.


.. _DIR/CodeCoverage/FileCoverage:

report:file-coverage
********************

The ``report:file-coverage`` directive writes a source file's listing where it is, as a file's page does - also for a
report without pages. Its argument is the file's path in the report:

.. grid:: 2

   .. grid-item::
      :columns: 6

      .. code-block:: ReST

         .. report:file-coverage:: myPackage/Units/Length.py
            :reportid: example

   .. grid-item::
      :columns: 6

      .. report:file-coverage:: myPackage/Units/Length.py
         :reportid: example


.. _DIR/CodeCoverage/Options:

Options
*******

.. rst:directive:: .. report:code-coverage::

   Renders a code coverage report as a table, on landscape pages in LaTeX.

   .. rst:directive:option:: reportid: <identifier>

      The report, as declared in ``pyTooling_CodeCoverage_Packages``. Required.

   .. rst:directive:option:: no-branch-coverage

      Leaves out the branch coverage columns.

   .. rst:directive:option:: class: <CSS classes>

      Additional CSS classes on the table.

.. rst:directive:: .. report:code-coverage-legend::

   Renders the coverage levels of a report as a table.

   .. rst:directive:option:: reportid: <identifier>

      The report, as declared in ``pyTooling_CodeCoverage_Packages``, whose palette is shown. Required.

   .. rst:directive:option:: style: horizontal-table | vertical-table

      A column per level, or a row per level. Default: ``horizontal-table``.

   .. rst:directive:option:: class: <CSS classes>

      Additional CSS classes. Accepted, but not yet put on the table.

.. rst:directive:: .. report:file-coverage:: <path>

   Renders a source file's listing. The report needs ``sources``.

   .. rst:directive:option:: reportid: <identifier>

      The report, as declared in ``pyTooling_CodeCoverage_Packages``. Required.

   .. rst:directive:option:: class: <CSS classes>

      Accepted, but not yet put on the listing.


.. _DIR/CodeCoverage/Styling:

Styling
*******

The table carries the classes ``report-codecov-table`` and ``report-codecov-<identifier>``, a legend
``report-codecov-legend``. A row carries its kind - ``report-package`` for the root, ``report-directory``,
``report-file`` or ``report-summary`` - and the CSS class of its coverage level, e.g. ``report-cov-below80``. The
stylesheet of :mod:`pyTooling.Sphinx` colours the rows of the ``default`` palette; a project overrides these rules, or
adds rules for a palette of its own, in a stylesheet listed in ``html_css_files``:

.. code-block:: CSS

   table.report-codecov-table > tbody > tr.report-cov-below80,
   table.report-codecov-legend > tbody > tr.report-cov-below80 {
     background: hsl(45 75% 80%);
   }

A listing is a ``<div>`` with class ``report-coverage-listing``, a line a ``<span>`` with class ``report-line`` and
``report-line-<state>``. Its colors and widths are custom properties:

.. code-block:: CSS

   :root {
     --pyTooling-coverage-covered:          rgba(46, 160, 88, 0.14);  /* line background */
     --pyTooling-coverage-covered-marker:   #2e9e58;                  /* left border */
     --pyTooling-coverage-partial:          rgba(218, 160, 24, 0.24);
     --pyTooling-coverage-partial-marker:   #b88910;
     --pyTooling-coverage-uncovered:        rgba(212, 58, 58, 0.16);
     --pyTooling-coverage-uncovered-marker: #c63c3c;
     --pyTooling-coverage-excluded:         rgba(110, 120, 130, 0.10);
     --pyTooling-coverage-excluded-marker:  #8a949c;
     --pyTooling-coverage-marker-width:     4px;
     --pyTooling-coverage-tab-size:         4;
   }


.. _DIR/CodeCoverage/Errors:

Errors
******

A mistake in the options, or a report that isn't configured, is reported on the page where the table would be, and in
the build's log:

.. code-block:: text

   Caught ReportExtensionError when checking options for directive 'code-coverage'.
     ReportExtensionError: No configuration for 'src'

A report that can't be read - e.g. without pyEDAA.Reports installed - is reported where its table would be:

.. code-block:: text

   Caught ReportsPackageMissingError when reading code coverage report 'src'.
