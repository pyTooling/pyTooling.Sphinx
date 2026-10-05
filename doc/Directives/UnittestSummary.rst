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
      format, so the reports of pytest, OSVVM and other JUnit dialects are accepted. Report files are declared in
      :file:`conf.py`, each with an identifier the directive names in its :rst:dir:`report:unittest-summary:reportid`
      option - so a documentation shows as many reports as it declares.

      The directive belongs to the extension :ref:`pyTooling.Sphinx.Report <DIR/UnittestSummary/Setup>`.

   .. grid-item::
      :columns: 6

      .. code-block:: ReST

         .. report:unittest-summary::
            :reportid: example

This is how the example renders, from a report of four testcases:

.. report:unittest-summary::
   :reportid: example

The documentation's own :doc:`unit test report <../unittests/index>` is rendered by this directive too.


.. _DIR/UnittestSummary/Setup:

Enabling the extension
**********************

The domain ``report`` is an extension of its own, ``pyTooling.Sphinx.Report``, because it reads the reports with
pyEDAA.Reports, which the extension :mod:`pyTooling.Sphinx` doesn't need. It sets up ``pyTooling.Sphinx`` itself.

.. grid:: 2

   .. grid-item::
      :columns: 6

      .. code-block:: bash

         pip install pyTooling.Sphinx[reports]

   .. grid-item::
      :columns: 6

      .. code-block:: Python

         # doc/conf.py
         extensions = [
           ...,
           "pyTooling.Sphinx.Report",
         ]


.. _DIR/UnittestSummary/Configuration:

Configuration
*************

The report files are declared in :file:`conf.py` as a dictionary, keyed by the identifier a directive names in
:rst:dir:`report:unittest-summary:reportid`. A path is relative to the documentation's source directory.

``pyTooling_Unittest_Testsuites``
  |rarr| The unit test reports, by identifier. An entry has one field:

  ``xml_report``
    |rarr| The report file, in Any JUnit XML format.

.. code-block:: Python

   # doc/conf.py
   pyTooling_Unittest_Testsuites = {
     "src": {
       "xml_report": "../report/unit/unittest.xml",
     }
   }

The configuration is checked when the build starts. A report file that doesn't exist is logged as an error, and the
entries after it aren't read: an entry whose file is written later - e.g. by a test run in CI - goes last.


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


.. _DIR/UnittestSummary/Errors:

Errors
******

A mistake in the options, or a report that can't be read, is reported on the page where the table would be, and in
the build's log:

.. code-block:: text

   Caught ReportExtensionError when checking options for directive 'unittest-summary'.
     ReportExtensionError: No unit testing configuration item for 'src'.
