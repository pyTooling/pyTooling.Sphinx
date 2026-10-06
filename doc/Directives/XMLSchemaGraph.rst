.. _DIR/XMLSchemaGraph:

xmlschema-graph
###############

.. grid:: 2

   .. grid-item::
      :columns: 6

      The ``xmlschema-graph`` directive draws an XML schema as a Graphviz graph, from the schema file itself:

      * every complex type is a record of its name, its attributes, and its simple-typed child elements with their
        cardinality;
      * every complex-typed child element is an edge, labelled with its name and cardinality - so containment and
        recursion are edges rather than repeated type names;
      * an enumeration is a node of its own, listing its values;
      * a root element is a double circle.

      The schema is read with :mod:`xmlschema`, a requirement of this package, and drawn by
      :mod:`sphinx.ext.graphviz`, which the extension sets up itself. The schema file becomes a dependency of the
      page.

   .. grid-item::
      :columns: 6

      .. code-block:: ReST

         .. xmlschema-graph:: TestReport-v0.1.xsd
            :package: pyTooling.Resources
            :caption: The types of TestReport-v0.1.xsd.

This is how the example renders, drawing pyTooling's test report schema from the package pyTooling ships it in:

.. xmlschema-graph:: TestReport-v0.1.xsd
   :package: pyTooling.Resources
   :caption: The types of TestReport-v0.1.xsd.

.. rst:directive:: .. xmlschema-graph:: <path of an XML schema>

   Draws the schema the argument names: a file relative to the document, or with :rst:dir:`xmlschema-graph:package` a
   resource file of a package.

   .. rst:directive:option:: package: <package>

      A package whose resource file the argument names, e.g. ``pyTooling.Resources``. It is imported, and the file is
      found wherever the package is installed - so a documentation draws a schema another package ships, without a
      copy of it.

   .. rst:directive:option:: caption: <text>

      A caption under the graph.

`pyTooling's schema pages <https://pyTooling.github.io/pyTooling/Schemas/index.html>`__ show the graphs of the schemas
pyTooling ships.

.. rubric:: Another schema language

:class:`~pyTooling.Sphinx.SchemaGraph.SchemaGraph` is the directive's language-neutral base-class,
and :class:`~pyTooling.Sphinx.SchemaGraph.DotGraph` is the graph: a :class:`pyTooling.Graph.GraphViz.Graph` with the
look every schema graph shares, plus ``AddRecord()`` for a titled record of compartments and ``GetOrAddNode()`` for an
edge's target without a record of its own. A directive for another schema language derives from the base-class, names
itself, and overrides ``_RenderGraph()``:

.. code-block:: Python

   class JSONSchemaGraph(SchemaGraph):
     directiveName: str = "json-schema-graph"

     @classmethod
     def _RenderGraph(cls, schemaFile: Path) -> str:
       graph = DotGraph()
       person = graph.AddRecord("Person", "Person", [["name : string", "age : integer"]])
       graph.AddEdge(Edge(person, graph.GetOrAddNode("Address"), {"label": "address [0..1]"}))
       ...
       return str(graph)
