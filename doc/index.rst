.. raw:: latex

   \part{Introduction}

.. shields::
   :github:                pyTooling/pyTooling.Sphinx
   :pypi:                  pyTooling.Sphinx
   :codacy:                d80355705a634d59835eeb01e8536cce
   :source-license:        github:LICENSE.md
   :documentation-license: CC-BY-4.0 github:doc/Doc-License.rst
   :github-action:         Pipeline.yml@main
   :documentation:         github-pages

   github, src-license, ghp-doc, doc-license
   pypi-tag, pypi-status, pypi-python
   github-action, lib-status, codacy-quality, codacy-coverage, codecov-coverage

--------------------------------------------------------------------------------

The pyTooling.Sphinx Documentation
##################################

**pyTooling.Sphinx** adds roles and directives to `Sphinx <https://www.sphinx-doc.org/>`__: styled inline text and
line breaks working in HTML and LaTeX, condensed class interfaces, dependency tables generated from requirements files
and the package index, badges, and schema graphs.

Other packages build on it: `pyTooling.GitHub <https://GitHub.com/pyTooling/pyTooling.GitHub>`__ contributes the
domain ``gha`` for GitHub Actions workflows, enabled as the extension ``pyTooling.GitHub.Sphinx``.

.. attention::

   pyTooling.Sphinx requires **Python 3.12 or newer**, because it requires Sphinx 9.1 and Sphinx 9.1 does.

The extension is enabled in :file:`conf.py`:

.. code-block:: Python

   # doc/conf.py
   extensions = [
     ...,
     "pyTooling.Sphinx",
   ]

It links its stylesheet into every HTML page, appends its substitutions to ``rst_prolog``, and sets up
:mod:`sphinx.ext.graphviz` for the schema graphs.


.. _HIGHLIGHTS:

Roles and Directives
********************

.. rubric:: Roles

:ref:`Style roles <ROLE/Style>`
  |rarr| ``:red:``, ``:underline:``, ``:deletion:`` and more: CSS classes on inline text, with the stylesheet giving
  them their meaning.
:ref:`Inline Python code <ROLE/PythonCode>`
  |rarr| ``:pycode:``, syntax-highlighted inline code.
:ref:`Line break and horizontal rule <ROLE/Breaks>`
  |rarr| ``|br|`` and ``|hr|``, in HTML and LaTeX.

.. rubric:: Directives

:ref:`condensed-class <DIR/CondensedClass>`
  |rarr| A class' public interface as one code block, parsed from its source.
:ref:`dependency-table <DIR/DependencyTable>`
  |rarr| A project's dependencies with versions and licenses, from its requirements files and the package index.
:ref:`jsonschema-graph <DIR/JSONSchemaGraph>`
  |rarr| Planned: a JSON schema as a Graphviz graph.
:ref:`xmlschema-graph <DIR/XMLSchemaGraph>`
  |rarr| An XML schema as a Graphviz graph, drawn from the schema file.
:ref:`shields <DIR/Shields>`
  |rarr| A project's badges from shields.io, in rows.


.. _CONSUMERS:

Consumers
*********

This layer is used by:

* `pyTooling.GitHub <https://GitHub.com/pyTooling/pyTooling.GitHub>`__ - its Sphinx domain ``gha`` builds on this
  extension, and its documentation uses it.
* 🚧 `pyTooling <https://GitHub.com/pyTooling/pyTooling>`__ - its documentation, which still uses pyTooling's own copy
  of this extension.


.. _CONTRIBUTORS:

Contributors
************

* :gh:`Patrick Lehmann <Paebbels>` (Maintainer)
* `and more... <https://GitHub.com/pyTooling/pyTooling.Sphinx/graphs/contributors>`__


.. _LICENSE:

License
*******

.. only:: html

   This Python package (source code) is licensed under `Apache License 2.0 <License.html>`__. |br|
   The accompanying documentation is licensed under
   `Creative Commons - Attribution 4.0 (CC-BY 4.0) <Doc-License.html>`__.

.. only:: latex

   This Python package (source code) is licensed under **Apache License 2.0**. |br|
   The accompanying documentation is licensed under **Creative Commons - Attribution 4.0 (CC-BY 4.0)**.


.. toctree::
   :hidden:

   Subnamespace of pyTooling ➚ <https://pyTooling.github.io/pyTooling/>

.. toctree::
   :caption: Introduction
   :hidden:

   News
   Installation
   Dependency
   CompetingSolutions

.. raw:: latex

   \part{Main Documentation}

.. toctree::
   :caption: Roles
   :hidden:

   Roles/Style
   Roles/PythonCode
   Roles/Breaks

.. toctree::
   :caption: Directives
   :hidden:

   Directives/CondensedClass
   Directives/DependencyTable
   Directives/JSONSchemaGraph
   Directives/XMLSchemaGraph
   Directives/Shields

.. raw:: latex

   \part{References and Reports}

.. toctree::
   :caption: References and Reports
   :hidden:

   Python Class Reference <pyTooling.Sphinx/pyTooling.Sphinx>
   unittests/index
   coverage/index
   CodeCoverage
   Doc. Coverage Report <DocCoverage>
   Static Type Check Report ➚ <typing/index>

.. raw:: latex

   \part{Appendix}

.. toctree::
   :caption: Appendix
   :hidden:

   License
   Doc-License
   Glossary
   genindex
   Python Module Index <modindex>
   TODO
