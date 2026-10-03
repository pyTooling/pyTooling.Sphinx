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

Other packages extend it with plugins: `pyTooling.GitHub <https://GitHub.com/pyTooling/pyTooling.GitHub>`__
contributes the domain ``gha`` for GitHub Actions workflows, which is registered automatically when that package is
installed.

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


.. _COMPETITORS:

Competing Solutions
*******************

The roles and each directive have competitors solving a part of their task; none of them is one extension covering
all of them.

Outside Python, XML editors generate the documentation of an XML schema - e.g. `Oxygen XML Editor
<https://www.oxygenxml.com/doc/ug-editor/topics/documentation-XML-Schema.html>`__ writes HTML or PDF pages listing
every component, with diagrams - but outside the Sphinx build.

.. _COMPETITORS/Roles:

docutils Roles
==============

Source: the `role <https://docutils.sourceforge.io/docs/ref/rst/directives.html#custom-interpreted-text-roles>`__
and `raw <https://docutils.sourceforge.io/docs/ref/rst/directives.html#raw-data-pass-through>`__ directives of
docutils, compared to the roles.

.. rubric:: Disadvantages

* A role created by ``.. role::`` only sets a CSS class, so every project writes the stylesheet itself, and declares the
  role in every document or in ``rst_prolog``.
* A line break written with ``raw`` is written once per output format - ``html`` and ``latex``.

.. rubric:: Advantages

* No extension is needed.

.. _COMPETITORS/autodoc:

autodoc and AutoAPI
===================

Source: :mod:`sphinx.ext.autodoc` and :mod:`sphinx.ext.autosummary` of Sphinx, and
:gh:`Sphinx AutoAPI <readthedocs/sphinx-autoapi>`, on PyPI as
`sphinx-autoapi <https://pypi.org/project/sphinx-autoapi/>`__, compared to ``condensed-class``.

.. rubric:: Disadvantages

* They document every member with its doc-string, or list members in a table, rather than showing a class' interface
  as one code block.
* :mod:`~sphinx.ext.autodoc` imports the module, so an annotation is rendered as it resolves, not as it is written.

.. rubric:: Standoff

* AutoAPI parses the source instead of importing it, as ``condensed-class`` does.

.. rubric:: Advantages

* Complete API documentation of modules, classes and functions, cross-referenced, not just one class' interface.

.. _COMPETITORS/Dependencies:

Dependency Lists
================

Source: :gh:`sphinxcontrib-requirements-txt <sphinx-contrib/requirements-txt>`, on PyPI as
`sphinxcontrib-requirements-txt <https://pypi.org/project/sphinxcontrib-requirements-txt/>`__ (last release 2023),
and `pip-licenses <https://pypi.org/project/pip-licenses/>`__, compared to ``dependency-table``.

.. rubric:: Disadvantages

* sphinxcontrib-requirements-txt renders the lines of requirements files through a Jinja2 template. It asks no
  package index, so it shows neither licenses nor the dependencies of a dependency.
* pip-licenses is a command line tool, not a directive. It reports the packages **installed** in the environment it
  runs in, as a flat list, so its table is generated and committed, or included by another extension.

.. rubric:: Advantages

* pip-licenses writes many formats - among them a reST grid table - and can fail on licenses that aren't allowed.

.. _COMPETITORS/Schemas:

Schema Documentation
====================

Source: :gh:`sphinx-jsonschema <lnoor/sphinx-jsonschema>`, on PyPI as
`sphinx-jsonschema <https://pypi.org/project/sphinx-jsonschema/>`__, compared to ``xmlschema-graph``.

.. rubric:: Disadvantages

* sphinx-jsonschema renders a JSON schema, not an XML schema, and as tables rather than as a graph.

.. rubric:: Advantages

* sphinx-jsonschema shows every property with its description.

.. _COMPETITORS/Shields:

sphinx-toolbox Shields
======================

Source: :gh:`sphinx-toolbox <sphinx-toolbox/sphinx-toolbox>`, on PyPI as
`sphinx-toolbox <https://pypi.org/project/sphinx-toolbox/>`__, its extension ``sphinx_toolbox.shields``, compared
to ``shields``.

.. rubric:: Disadvantages

* Every badge is a directive of its own - ``pypi-shield``, ``github-shield``, ``actions-shield`` and others - so the
  project's coordinates are repeated per badge, and the rows are laid out by hand.

.. rubric:: Advantages

* Badges of services ``shields`` doesn't know, e.g. Read the Docs, Coveralls, CodeFactor and pre-commit.
* It is one extension of a larger collection.


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

   Used as a layer of pyTooling ➚ <https://pyTooling.github.io/pyTooling/>

.. toctree::
   :caption: Introduction
   :hidden:

   News
   Installation
   Dependency

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
