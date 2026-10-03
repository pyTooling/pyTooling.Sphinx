.. _NEWS:

News
####

See `pyTooling.Sphinx Release Pages <https://github.com/pyTooling/pyTooling.Sphinx/releases>`__ for detail release
notes on every release.


Version 0.x (2026)
******************

.. topic:: `v0.1.0 - unreleased <https://github.com/pyTooling/pyTooling.Sphinx/releases/v0.1.0>`__

   .. rubric:: New Features

   * First release: pyTooling's Sphinx extension ``pyTooling.Documentation.Sphinx`` becomes a package of its own,
     :mod:`pyTooling.Sphinx`.
   * Roles: :ref:`style roles <DOC/Sphinx/Roles/Style>`, :ref:`inline Python code <DOC/Sphinx/Roles/pycode>`, and
     :ref:`line break and horizontal rule <DOC/Sphinx/Roles/Breaks>` in HTML and LaTeX.
   * Directives: :ref:`condensed-class <DOC/Sphinx/CondensedClass>`,
     :ref:`dependency-table <DOC/Sphinx/DependencyTable>`, :ref:`xmlschema-graph <DOC/Sphinx/XMLSchemaGraph>` and
     :ref:`shields <DOC/Sphinx/Shields>`.
   * :class:`~pyTooling.Sphinx.SchemaGraph.DotGraph` is built on :mod:`pyTooling.Graph.GraphViz`.

   .. rubric:: Changes

   * The directive ``xsd-graph`` is named ``xmlschema-graph``, and its class ``XSDSchemaGraph`` is
     :class:`~pyTooling.Sphinx.XMLSchemaGraph.XMLSchemaGraph`.
