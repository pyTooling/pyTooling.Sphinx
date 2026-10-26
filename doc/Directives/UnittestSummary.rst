.. _DIR/UnittestSummary:

report:unittest-summary
#######################

.. grid:: 2

   .. grid-item::
      :columns: 6

      The ``report:unittest-summary`` directive renders a unit test report as a table: a row per testsuite and
      testcase, with the counts of testcases, skipped, errored, failed and passed ones, the assertions and the runtime.
      The hierarchy of testsuites is shown by indentation, a status by a symbol and a CSS class.

      The report is read by `pyEDAA.Reports <https://edaa-org.github.io/pyEDAA.Reports/>`__ in the *Any JUnit* XML
      format, so the reports of pytest, OSVVM and other JUnit dialects are accepted, or in
      :ref:`pyTooling's own XML format <DIR/UnittestSummary/Formats>`. Report files are declared in :file:`conf.py`,
      each with an identifier the directive names in its :rst:dir:`report:unittest-summary:reportid` option - so a
      documentation shows as many reports as it declares.

      A report can get a :ref:`page per testsuite and testcase <DIR/UnittestSummary/Pages>`, which the table links
      to and the roles :rst:role:`tc` and :rst:role:`ts` refer to.

      The directive is part of :mod:`pyTooling.Sphinx`; it needs the :ref:`extra reports <DIR/UnittestSummary/Setup>`.

   .. grid-item::
      :columns: 6

      .. code-block:: ReST

         .. report:unittest-summary::
            :reportid: example

This is how the example renders, from a report of five testcases. The report is declared with
:ref:`pages <DIR/UnittestSummary/Pages>`, so every testsuite and testcase links to its page:

.. report:unittest-summary::
   :reportid: example

The documentation's own :doc:`unit test report <../unittests/index>` is rendered by this directive too, with a page
per testsuite and testcase.


.. _DIR/UnittestSummary/Setup:

Installing the extra ``reports``
********************************

The directives of domain ``report`` are registered by the extension :mod:`pyTooling.Sphinx`, but read the reports -
and analyze the documentation coverage - with :gh:`pyEDAA.Reports <edaa-org/pyEDAA.Reports>`, an optional dependency.
A project using a report installs it with the extra ``reports``:

.. code-block:: bash

   pip install pyTooling.Sphinx[reports]

Without it, the extension and every other directive work; a report directive reports on the page and in the build's
log that it needs it:

.. code-block:: text

   Caught ReportsPackageMissingError when reading '../report/unit/unittest.xml'.
     ReportsPackageMissingError: Reading a unit test report needs 'pyEDAA.Reports', which isn't installed.
       Install it with: pip install pyTooling.Sphinx[reports]


.. _DIR/UnittestSummary/Configuration:

Configuration
*************

The report files are declared in :file:`conf.py` as a dictionary, keyed by the identifier a directive names in
:rst:dir:`report:unittest-summary:reportid`. A path is relative to the documentation's source directory.

``pyTooling_Unittest_Testsuites``
  |rarr| The unit test reports, by identifier. An entry has these fields:

  ``xml_report``
    |rarr| The report file, in Any JUnit XML format or :ref:`pyTooling's XML format <DIR/UnittestSummary/Formats>`.
    Required.

  ``pages``
    |rarr| The document name the :ref:`pages per testsuite and testcase <DIR/UnittestSummary/Pages>` are generated
    below, e.g. ``unittests/src``. Optional; without it, the report gets no pages.

.. code-block:: Python

   # doc/conf.py
   pyTooling_Unittest_Testsuites = {
     "src": {
       "xml_report": "../report/unit/unittest.xml",
       "pages":      "unittests/src",
     }
   }

The first entry is the default report of the roles :rst:role:`tc` and :rst:role:`ts`.

The configuration is checked when the build starts. A report file that doesn't exist is logged as an error, and the
entries after it aren't read: an entry whose file is written later - e.g. by a test run in CI - goes last.


.. _DIR/UnittestSummary/Formats:

Report formats
**************

The format of a report file is recognized by its root element:

``<testsuites>`` or ``<testsuite>``
  |rarr| A JUnit XML file, read by pyEDAA.Reports in the *Any JUnit* dialect - e.g. pytest's ``--junit-xml``. A
  testcase's failure, error or skip message, its traceback and its captured output are shown on its
  :ref:`page <DIR/UnittestSummary/Pages>`.

``<TestReport>``
  |rarr| A test report in pyTooling's XML format, written by pyTooling's pytest plugin with ``--pytooling-xml``.
  Its testsuites nest, and a testsuite or testcase carries a title, a summary and a description - e.g. from the
  markers ``@testsuite`` and ``@testcase`` and the doc-strings. A page shows them below its name, a link shows the
  title on hover.

.. report:unittest-summary::
   :reportid: pytooling
   :no-assertions:


.. _DIR/UnittestSummary/Pages:

Pages per testsuite and testcase
********************************

A report declared with the key ``pages`` gets a page per testsuite and per testcase. They are generated when the
documentation is built - no source file is written - below the document name the key states:

* a testsuite's page: ``<pages>/<testsuite>/<testsuite>/...``, the names of the testsuites from the report's top
  down, e.g. ``unittests/example/pytest/tests/unit/Arithmetic``;
* a testcase's page: ``<pages>/<testsuite>/.../<testcase>``, e.g.
  ``unittests/example/pytest/tests/unit/Arithmetic/Division/test_ByZero``.

Characters of a name other than letters, digits, ``_``, ``-`` and ``.`` - e.g. the brackets of a parametrized pytest
testcase - are replaced by ``_``. A name colliding with a sibling's, also when differing in case only, gets the suffix
``-2``, ``-3``, and so on.

A **testcase's page** shows its status, duration, number of assertions (if the report has it) and its testsuite,
linked; then the message and details of a failure, error or skip, and the captured standard output and standard error.

A **testsuite's page** shows its status, the number of testcases per status, the duration, the number of assertions
(if the report has it) and its parent testsuite; then a table of its testsuites and a table of its testcases, each
linked to its page.

The title, summary and description of a :ref:`pyTooling report <DIR/UnittestSummary/Formats>` are shown below the
name, as plain text: they are doc-strings, which aren't necessarily ReST of this documentation.

The :rst:dir:`report:unittest-summary` table links every testsuite and testcase to its page; that is the entry point.
The directive lists the report's top-level testsuites in a hidden table of contents, and a testsuite's page lists its
testsuites and testcases, so the pages are below the summary's document in the navigation - in the section holding
the directive. A page's own sections - *Summary*, *Testcases*, ... - aren't listed there. A report is best shown on a
page of its own: a title, an introduction and the directive.

.. hint::

   A testcase is as many levels below the summary's document as the report nests testsuites - e.g. seven for
   ``pytest/tests/unit/Arithmetic/Division/test_ByZero``. A theme limits how deep its navigation goes, e.g. the
   option ``navigation_depth`` of the *Read the Docs* theme (default 4; ``-1`` = unlimited). ``pyedaa-reports``
   removes levels like ``pytest/tests/unit`` from a JUnit report with ``--pytest=reduce-depth:pytest.tests.unit``.

The pages are :ref:`orphans <sphinx:metadata>`, so a report with pages, but without a summary directive, causes no
warnings; its pages are reached by the roles only.

Sphinx regards the report file as the source of its pages, so a changed report regenerates its pages. As the pages
are in the table of contents, LaTeX writes them too - below the summary's section, the deepest levels as
paragraphs.

.. hint::

   A report can have thousands of testcases - pages are only generated for a report declaring ``pages``.


.. _DIR/UnittestSummary/Roles:

Roles
*****

The roles :rst:role:`tc` and :rst:role:`ts` refer to a testcase and a testsuite of a report with pages. They are
registered in domain ``report`` - as ``:report:tc:`` and ``:report:ts:`` - and without the domain's prefix.

.. rst:role:: tc

   Refers to a testcase's page, showing the testcase's name, or the role's title: ``:tc:`<target>``` or
   ``:tc:`title <<target>>```.

   The target is ``[<report ID>:]<qualified name>``. The qualified name is the path from the report's top down, the
   names joined by ``.``: e.g. ``pytest.tests.unit.Arithmetic.Division.test_ByZero``. A suffix of it starting at a
   name - ``Division.test_ByZero`` or ``test_ByZero`` - is accepted, if it's unique. Without a report ID, the first
   report of ``pyTooling_Unittest_Testsuites`` is meant.

   A target matching nothing or several testcases is warned about.

.. rst:role:: ts

   Refers to a testsuite's page, as :rst:role:`tc` refers to a testcase's.

.. grid:: 2

   .. grid-item::
      :columns: 6

      .. code-block:: ReST

         * :tc:`test_ByZero`
         * :tc:`example:Division.test_Fraction`
         * :ts:`Arithmetic`
         * :ts:`pytooling:Addition`
         * :tc:`the skipped one <test_Fraction>`

   .. grid-item::
      :columns: 6

      * :tc:`test_ByZero`
      * :tc:`example:Division.test_Fraction`
      * :ts:`Arithmetic`
      * :ts:`pytooling:Addition`
      * :tc:`the skipped one <test_Fraction>`

The testsuites and testcases are objects of domain ``report``, named ``<report ID>:<qualified name>`` in the
documentation's inventory (:file:`objects.inv`), so another documentation refers to them with ``intersphinx``.


.. _DIR/UnittestSummary/Options:

Options
*******

.. rst:directive:: .. report:unittest-summary::

   Renders a unit test report as a table, on landscape pages in LaTeX.

   .. rst:directive:option:: reportid: <identifier>

      The report, as declared in ``pyTooling_Unittest_Testsuites``. Required.

   .. rst:directive:option:: testsuite-summary-name: <name>

      The name of the row summarizing all testsuites, instead of the report's own.

   .. rst:directive:option:: show-testcases: all | not-passed

      Which testcases are listed per testsuite: all of them, or only those that didn't pass. Default: ``all``.

   .. rst:directive:option:: no-assertions

      Leaves out the column of assertions.

   .. rst:directive:option:: hide-testsuite-summary

      Leaves out the row summarizing all testsuites above the testsuites.

   .. rst:directive:option:: class: <CSS classes>

      Additional CSS classes on the table.


.. _DIR/UnittestSummary/Styling:

Styling
*******

The table carries the classes ``report-unittest-table`` and ``report-unittest-<identifier>``. A row carries its kind -
``report-testsuitesummary``, ``report-testsuite``, ``report-testcase`` or ``report-summary`` - and its status, e.g.
``testcase-failed``. The stylesheet of :mod:`pyTooling.Sphinx` colours the rows by status; a project overrides these
rules in a stylesheet of its own, listed in ``html_css_files``:

.. code-block:: CSS

   table.report-unittest-table > tbody > tr.testcase-skipped {
     background: #eee;
   }

A name is indented by its depth, two steps per level, as in the :ref:`code coverage tables <DIR/CodeCoverage/Styling>`.


.. _DIR/UnittestSummary/Deriving:

Deriving a table
****************

A project reading a test report of its own - e.g. a simulation framework's build summary with alert counts and
functional coverage - derives its directive from :class:`~pyTooling.Sphinx.Unittest.UnittestSummaryBase`, the base-class
of :rst:dir:`report:unittest-summary`. The base-class renders the rows - a testsuite summary, its testsuites and its
listed testcases, indented by depth, the first column linked to the pages -, the derived class names the other columns:

.. code-block:: Python

   from pyTooling.Sphinx.Unittest import Column, ColumnGroup, UnittestSummary

   class AssertionSummary(UnittestSummary):
     directiveName = "assertion-summary"

     def _Columns(self):
       return [
         Column("Testcases", 1, testsuite=lambda testsuite: f"{testsuite.TestcaseCount}"),
         ColumnGroup("Assertions", [
           Column("Passed", 1, testcase=lambda testcase: f"{testcase.PassedAssertionCount}"),
           Column("Total",  1, testcase=lambda testcase: f"{testcase.AssertionCount}")
         ])
       ]

A :class:`~pyTooling.Sphinx.Unittest.Column` names a function per kind of row - ``testsuite`` for a testsuite's and
the testsuite summary's rows, ``testcase`` for a testcase's row -, which returns the cell's content: a text, a node, or
the cell itself, e.g. to give it a CSS class. A :class:`~pyTooling.Sphinx.Unittest.ColumnGroup` puts columns under a
common title, in a second header row.

A directive reading another kind of report derives from :class:`~pyTooling.Sphinx.Unittest.UnittestSummaryBase` itself:
it reads its options in ``_CheckOptions``, its reports into its own class variables ``_reports`` and ``_readErrors``,
and returns its pages by ``_Pages``. Its pages derive from :class:`~pyTooling.Sphinx.UnittestPages.UnittestReportPages`,
which adds fields to a testcase's summary by ``_TestcaseFields``, and columns to the testcase table of a testsuite's
page by ``_TestcaseColumns`` and ``_TestcaseCells``. A domain of its own, with roles of its own, derives from
:class:`~pyTooling.Sphinx.ReportDomain` and names its roles in ``_ROLES``.


.. _DIR/UnittestSummary/Errors:

Errors
******

A mistake in the options, or a report that can't be read, is reported on the page where the table would be, and in
the build's log:

.. code-block:: text

   Caught ReportExtensionError when checking options for directive 'unittest-summary'.
     ReportExtensionError: No unit testing configuration item for 'src'.
