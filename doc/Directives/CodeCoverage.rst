.. _DIR/CodeCoverage:

report:code-coverage
####################

.. grid:: 2

   .. grid-item::
      :columns: 6

      The ``report:code-coverage`` directive renders a code coverage report as a table: a row per package and module,
      with the statement and branch coverage. The package hierarchy is shown by indentation and 📦, a module by ⚙️,
      and each row is coloured by its coverage level. ``report:code-coverage-legend`` renders the coverage levels.

      The report is the JSON file of `Coverage.py <https://github.com/nedbat/coveragepy>`__ (``coverage json``).
      Report files are declared in :file:`conf.py`, each with an identifier the directives name in their
      :rst:dir:`report:code-coverage:reportid` option - so a documentation shows as many reports as it declares.

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

This is how the example renders, from a report of a package with one sub-package and one module:

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

The documentation's own :doc:`code coverage report <../CodeCoverage>` is rendered by these directives too.


.. _DIR/CodeCoverage/Configuration:

Configuration
*************

The report files are declared in :file:`conf.py` as a dictionary, keyed by the identifier a directive names in
:rst:dir:`report:code-coverage:reportid`. A path is relative to the documentation's source directory.

``pyTooling_CodeCoverage_Packages``
  |rarr| The code coverage reports, by identifier. An entry has four fields:

  ``name``
    |rarr| The name of the Python package, shown in the first row.
  ``json_report``
    |rarr| The report file, as written by ``coverage json``.
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
       "fail_below":  80,
       "levels":      "default"
     }
   }

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

``report:module-coverage`` is a prototype of a module's source code, highlighted by its coverage. It isn't usable yet.


.. _DIR/CodeCoverage/Styling:

Styling
*******

The table carries the classes ``report-codecov-table`` and ``report-codecov-<identifier>``, a legend
``report-codecov-legend``. A row carries its kind - ``report-package``, ``report-module`` or ``report-summary`` - and
the CSS class of its coverage level, e.g. ``report-cov-below80``. The stylesheet of :mod:`pyTooling.Sphinx` colours the
rows of the ``default`` palette; a project overrides these rules, or adds rules for a palette of its own, in a
stylesheet listed in ``html_css_files``:

.. code-block:: CSS

   table.report-codecov-table > tbody > tr.report-cov-below80,
   table.report-codecov-legend > tbody > tr.report-cov-below80 {
     background: hsl(45 75% 80%);
   }


.. _DIR/CodeCoverage/Errors:

Errors
******

A mistake in the options, or a report that isn't configured, is reported on the page where the table would be, and in
the build's log:

.. code-block:: text

   Caught ReportExtensionError when checking options for directive 'code-coverage'.
     ReportExtensionError: No configuration for 'src'
