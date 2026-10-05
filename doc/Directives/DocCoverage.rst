.. _DIR/DocCoverage:

report:doc-coverage
###################

.. grid:: 2

   .. grid-item::
      :columns: 6

      The ``report:doc-coverage`` directive renders the documentation coverage of a Python package as a table: a row
      per package and module, with the number of members expected to have a doc-string, the documented and the
      undocumented ones. The package hierarchy is shown by indentation and 📦, a module by ⚙️, and each row is
      coloured by its coverage level. ``report:doc-coverage-legend`` renders the coverage levels.

      There is no report file: the package's source directory is analyzed with
      `docstr_coverage <https://github.com/HunterMcGushion/docstr_coverage>`__ when the directive runs. Packages are
      declared in :file:`conf.py`, each with an identifier the directives name in their
      :rst:dir:`report:doc-coverage:reportid` option.

      The directives belong to the extension :ref:`pyTooling.Sphinx.Report <DIR/UnittestSummary/Setup>`.

   .. grid-item::
      :columns: 6

      .. code-block:: ReST

         .. grid:: 2

            .. grid-item::
               :columns: 8

               .. report:doc-coverage::
                  :reportid: src

            .. grid-item::
               :columns: 4

               .. report:doc-coverage-legend::
                  :reportid: src
                  :style:    vertical-table

This is how the example renders, for this documentation's own package:

.. grid:: 2

   .. grid-item::
      :columns: 8

      .. report:doc-coverage::
         :reportid: src

   .. grid-item::
      :columns: 4

      .. report:doc-coverage-legend::
         :reportid: src
         :style:    vertical-table


.. _DIR/DocCoverage/Configuration:

Configuration
*************

The packages are declared in :file:`conf.py` as a dictionary, keyed by the identifier a directive names in
:rst:dir:`report:doc-coverage:reportid`. A path is relative to the documentation's source directory.

``pyTooling_DocCoverage_Packages``
  |rarr| The analyzed packages, by identifier. An entry has four fields:

  ``name``
    |rarr| The name of the Python package, shown in the first row.
  ``directory``
    |rarr| The package's source directory.
  ``fail_below``
    |rarr| An integer in range 0..100: the coverage in percent below which the package fails.
  ``levels``
    |rarr| The name of a palette in ``pyTooling_DocCoverage_Levels``, e.g. ``"default"``.

``pyTooling_DocCoverage_Levels``
  |rarr| The palettes of coverage levels, by name. A palette maps an upper limit in percent to a CSS class and a
  description, and needs a level ``100`` and a level ``"error"``. Default: the palette ``default``, of 12 levels
  from ≤10 % to ≤100 %, coloured from blue via red, orange and yellow to green.

.. code-block:: Python

   # doc/conf.py
   pyTooling_DocCoverage_Packages = {
     "src": {
       "name":       "myPackage",
       "directory":  "../myPackage",
       "fail_below": 80,
       "levels":     "default"
     }
   }

The configuration is checked when the build starts. A directory that doesn't exist is logged as an error, and the
entries after it aren't read.


.. _DIR/DocCoverage/Options:

Options
*******

.. rst:directive:: .. report:doc-coverage::

   Renders the documentation coverage of a package as a table.

   .. rst:directive:option:: reportid: <identifier>

      The package, as declared in ``pyTooling_DocCoverage_Packages``. Required.

   .. rst:directive:option:: class: <CSS classes>

      Additional CSS classes on the table.

.. rst:directive:: .. report:doc-coverage-legend::

   Renders the coverage levels of a package as a table.

   .. rst:directive:option:: reportid: <identifier>

      The package, as declared in ``pyTooling_DocCoverage_Packages``, whose palette is shown. Required.

   .. rst:directive:option:: style: horizontal-table | vertical-table

      A column per level, or a row per level. Default: ``horizontal-table``.

   .. rst:directive:option:: class: <CSS classes>

      Additional CSS classes. Accepted, but not yet put on the table.


.. _DIR/DocCoverage/Styling:

Styling
*******

The table carries the classes ``report-doccov-table`` and ``report-doccov-<identifier>``, a legend
``report-doccov-legend``. A row carries its kind - ``report-package``, ``report-module`` or ``report-summary`` - and the
CSS class of its coverage level, e.g. ``report-cov-below80``. The rules of the stylesheet are those of the
:ref:`code coverage tables <DIR/CodeCoverage/Styling>`.
