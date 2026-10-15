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
      `docstr_coverage <https://github.com/HunterMcGushion/docstr_coverage>`__ once per build. Packages are declared in
      :file:`conf.py`, each with an identifier the directives name in their :rst:dir:`report:doc-coverage:reportid`
      option.

      A package can get a :ref:`page per package and module <DIR/DocCoverage/Pages>`: a module's page shows its source
      condensed to signatures and doc-strings, each marked by its documentation state. The table links to the pages,
      and the role :rst:role:`doccov` refers to them.

      The directives are part of :mod:`pyTooling.Sphinx`; they need the
      :ref:`extra reports <DIR/UnittestSummary/Setup>`.

   .. grid-item::
      :columns: 6

      .. code-block:: ReST

         .. grid:: 2

            .. grid-item::
               :columns: 8

               .. report:doc-coverage::
                  :reportid: example

            .. grid-item::
               :columns: 4

               .. report:doc-coverage-legend::
                  :reportid: example
                  :style:    vertical-table

This is how the example renders, for a package with one sub-package. The package is declared with
:ref:`pages <DIR/DocCoverage/Pages>`, so every package and module links to its page:

.. grid:: 2

   .. grid-item::
      :columns: 8

      .. report:doc-coverage::
         :reportid: example

   .. grid-item::
      :columns: 4

      .. report:doc-coverage-legend::
         :reportid: example
         :style:    vertical-table

The documentation's own :doc:`documentation coverage report <../DocCoverage>` is rendered by these directives too.


.. _DIR/DocCoverage/Configuration:

Configuration
*************

The packages are declared in :file:`conf.py` as a dictionary, keyed by the identifier a directive names in
:rst:dir:`report:doc-coverage:reportid`. A path is relative to the documentation's source directory.

``pyTooling_DocCoverage_Packages``
  |rarr| The analyzed packages, by identifier. An entry has these fields:

  ``name``
    |rarr| The name of the Python package, shown in the first row.
  ``directory``
    |rarr| The package's source directory.
  ``pages``
    |rarr| The document name the :ref:`pages per package and module <DIR/DocCoverage/Pages>` are generated below,
    e.g. ``doccoverage/src``. Optional; without it, the package gets no pages.
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
       "pages":      "doccoverage/src",
       "fail_below": 80,
       "levels":     "default"
     }
   }

The first entry is the default package of the role :rst:role:`doccov`.

The configuration is checked when the build starts. A directory that doesn't exist is logged as an error, and the
entries after it aren't read. The packages are analyzed once per build, before any document is read.


.. _DIR/DocCoverage/Pages:

Pages per package and module
****************************

A package declared with the key ``pages`` gets a page per package and per module. They are generated when the
documentation is built - no source file is written - below the document name the key states, named by the package's
and module's names, e.g. ``doccoverage/src/myPackage/Units/Length``.

A **package's page** shows its parent package, the state of its ``__init__.py``'s doc-string, and its counters: those
of its ``__init__.py``, and overall - with all its packages and modules -, each colored by its coverage level. Then a
table of its packages and a table of its modules, each linked to its page and colored by its coverage level; a
package's row counts it with all its packages and modules. Last, the **condensed listing** of its ``__init__.py``.

A **module's page** shows its parent package, the state of its doc-string, its counters, and its condensed listing.

The condensed listing shows a module's source as far as documentation coverage is about it: the code of a function is
of no interest, its signature and its doc-string are. The source is syntax highlighted with Pygments, in the colors
of Sphinx' Pygments style, as every code block. A line is shown as written, with its line number, or elided:

* The module's doc-string is shown. Imports and other statements are elided.
* A class or function is shown with its decorators, its header - a signature spanning several lines too - and its
  doc-string. Its body follows: a class' fields and methods, a function's nested functions and classes. Anything else
  is elided.
* A module's variables and a class' fields are shown with their ``#:`` comments - behind them or in the lines above -
  and a doc-string literal following them.
* A statement holding classes or functions - e.g. an ``if`` choosing between two definitions - is shown as written,
  its classes and functions condensed.
* A definition written in one line - ``def f(): pass`` - is shown as written.
* Comments between statements are left out; consecutive blank lines become one.

Consecutive elided statements become a single ``...`` line without a line number, at the statements' indentation, so
a function's body becomes ``...``. Each line of a class or function - its decorators, header and doc-string - is
marked by the documentation state docstr_coverage found for it:

.. list-table::
   :header-rows: 1
   :widths: 20 80

   * - State
     - Line
   * - ``documented``
     - The class or function has a doc-string - or an excuse comment, e.g. ``# docstr-coverage:inherited``.
   * - ``undocumented``
     - The class or function has no doc-string.
   * - ``ignored``
     - The class or function isn't counted, e.g. matching an ignore pattern.
   * - ``excluded``
     - The item is excluded from the analysis.
   * - (none)
     - The line isn't counted: a variable, a field, a blank line, a statement holding definitions.

The module's doc-string is marked too; a missing one is stated in the page's summary. docstr_coverage doesn't count
variables and fields, so they aren't marked - unless pyEDAA.Reports' model holds a state for one.

A header above the listing shows the module's path and a legend of these states.

The :rst:dir:`report:doc-coverage` directive lists the package's page in a hidden table of contents, and a package's
page lists its packages and modules, so the pages are in the navigation below the table's document. LaTeX writes the
pages too, below the table's section; a listing's line numbers are colored by the documentation state, followed by a
marker: ``+`` documented, ``-`` undocumented, ``o`` ignored, ``x`` excluded; a line above the listing shows the
module's path and the markers' legend.

Sphinx regards a module's file - a package's ``__init__.py`` - as the source of its page.

.. hint::

   A module is as many levels below the table's document as it is nested in packages. A theme limits how deep its
   navigation goes, e.g. the option ``navigation_depth`` of the *Read the Docs* theme (default 4; ``-1`` =
   unlimited).


.. _DIR/DocCoverage/Role:

Role
****

.. rst:role:: doccov

   Refers to a package's or module's page, showing its name, or the role's title: ``:doccov:`<target>``` or
   ``:doccov:`title <<target>>```. It is registered in domain ``report`` - as ``:report:doccov:`` - and without the
   domain's prefix.

   The target is ``[<report ID>:]<dotted name>``, e.g. ``myPackage.Units.Length``. A suffix of it starting at a name
   - ``Units.Length`` or ``Length`` - is accepted, if it's unique. The configured name of the analyzed package is one
   name, also if it's dotted, e.g. ``pyTooling.Sphinx``. Without a report ID, the first package of
   ``pyTooling_DocCoverage_Packages`` is meant.

   A target matching nothing or several packages and modules is warned about.

.. grid:: 2

   .. grid-item::
      :columns: 6

      .. code-block:: ReST

         * :doccov:`example:Shapes`
         * :doccov:`example:myPackage.Units`
         * :doccov:`the length module <example:Length>`

   .. grid-item::
      :columns: 6

      * :doccov:`example:Shapes`
      * :doccov:`example:myPackage.Units`
      * :doccov:`the length module <example:Length>`

The packages and modules are objects of domain ``report`` of type ``module``, named ``<report ID>:<dotted name>`` in
the documentation's inventory (:file:`objects.inv`), so another documentation refers to them with ``intersphinx``.


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
:ref:`code coverage tables <DIR/CodeCoverage/Styling>`. A page's tables carry ``report-doccov-table`` too, and
``report-doccov-summary`` or ``report-doccov-children``.

A condensed listing is styled like a :ref:`code coverage listing <DIR/CodeCoverage/Styling>`: a line carries
``report-line-documented``, ``report-line-undocumented``, ``report-line-ignored`` or ``report-line-excluded``, which
share the colors of ``covered``, ``uncovered`` and ``excluded``; an elided ``...`` carries ``report-line-elided``.
