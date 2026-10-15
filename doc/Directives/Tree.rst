.. _DIR/Tree:

tree
####

.. grid:: 2

   .. grid-item::
      :columns: 6

      The ``tree`` directive draws a hierarchy as a tree - a directory, a class hierarchy, the structure of a
      testsuite - instead of lines drawn by hand in a code block.

      The **content** is the hierarchy, written as an indented list in the style of a YAML block sequence. An entry's
      text is inline ReST, so a role such as ``:class:`` or ``:ref:`` links to what the entry names.

      The **options** choose an icon per kind of entry or per marker, and how many levels are expanded initially. In
      HTML, every entry with children folds and unfolds on a click.

      An entry may have a **description**, which HTML draws as a second column, as in a table - see
      :ref:`DIR/Tree/Descriptions`.

      An icon may have a **text** explaining it, which HTML draws in the tree's legend - see :ref:`DIR/Tree/Legend`.

   .. grid-item::
      :columns: 6

      .. code-block:: ReST

         .. tree::
            :root-icon: 📦
            :node-icon: 📁
            :leaf-icon: 📄
            :icons:     > 📁

            - pyTooling.Sphinx
              > :file:`doc`
              - :file:`pyTooling`
                - :file:`Sphinx`
                  - :mod:`~pyTooling.Sphinx.Tree`
                  - :mod:`~pyTooling.Sphinx.Shields`
              - :file:`README.md`

This is how the example renders:

.. tree::
   :root-icon: 📦
   :node-icon: 📁
   :leaf-icon: 📄
   :icons:     > 📁

   - pyTooling.Sphinx
     > :file:`doc`
     - :file:`pyTooling`
       - :file:`Sphinx`
         - :mod:`~pyTooling.Sphinx.Tree`
         - :mod:`~pyTooling.Sphinx.Shields`
     - :file:`README.md`

A class hierarchy, without icons and with only the first level expanded:

.. grid:: 2

   .. grid-item::
      :columns: 6

      .. code-block:: ReST

         .. tree::
            :expanded-levels: 1

            - :class:`~sphinx.directives.ObjectDescription`
              - :class:`~pyTooling.Sphinx.BaseDirective`
                - :class:`~pyTooling.Sphinx.DependencyTable.DependencyTable`
                - :class:`~pyTooling.Sphinx.SchemaGraph.SchemaGraph`
                  - :class:`~pyTooling.Sphinx.XMLSchemaGraph.XMLSchemaGraph`
                - :class:`~pyTooling.Sphinx.Shields.Shields`
                - :class:`~pyTooling.Sphinx.Tree.Tree`

   .. grid-item::
      :columns: 6

      .. tree::
         :expanded-levels: 1

         - :class:`~sphinx.directives.ObjectDescription`
           - :class:`~pyTooling.Sphinx.BaseDirective`
             - :class:`~pyTooling.Sphinx.DependencyTable.DependencyTable`
             - :class:`~pyTooling.Sphinx.SchemaGraph.SchemaGraph`
               - :class:`~pyTooling.Sphinx.XMLSchemaGraph.XMLSchemaGraph`
             - :class:`~pyTooling.Sphinx.Shields.Shields`
             - :class:`~pyTooling.Sphinx.Tree.Tree`


.. _DIR/Tree/Content:

Content
*******

* An entry is a line starting with a marker and a space. Blank lines are ignored.
* An entry indented deeper than the entry above it is that entry's child. Siblings are indented alike; how deep a
  child is indented doesn't matter.
* An entry without a parent is a **root**, an entry with children is a **node**, and every other entry is a
  **leaf**. A content may hold several roots.
* The marker ``-`` gives an entry the icon of its kind. Every other marker is declared by :rst:dir:`tree:icons`, with
  its own icon, whatever the entry's kind is - e.g. a folder for an empty directory, which is a leaf.
* An entry's text is inline ReST: roles, emphasis, literals and links.
* A ``|`` between spaces separates the entry's text from its **description** - see :ref:`DIR/Tree/Descriptions`.

.. code-block:: ReST

   .. tree::
      :icons: > 📁, * ⭐

      - root
        - node
          - leaf
        > empty directory
        * a leaf with a star


.. _DIR/Tree/Descriptions:

Descriptions
************

A ``|`` between spaces separates an entry's text from its description. HTML draws the descriptions as a second
column: all of them start at the same horizontal position, whatever the entry's level, as in a table.

* A description is inline ReST, as the entry's text is.
* An entry without a description stays valid; so does a ``|`` at the line's end, which leaves the description empty.
* Spaces around the ``|`` don't matter, so the separators may be aligned in the source.
* A ``|`` in an inline literal, e.g. ``int | None``, or in a role's text separates nothing, and neither does a
  substitution reference such as ``|br|``. Elsewhere, a ``|`` between spaces, which belongs to the text, is escaped as
  ``\|``.
* A line has at most one separator.

.. code-block:: ReST

   .. tree::

      - CoverageSummary         | the report
        - physical hierarchy    | built from the file paths the report names
          - Directory           | e.g. ``myPackage/``
            - File              | e.g. ``myPackage/Shapes.py``
              - Line            | line number, ``LineCoverageStatus``, coverage count
                - Branch        | ``LineCoverageStatus``, coverage count, target
          - File
        - logical hierarchy     | the language units the report names - each: file, first and last line
          - Package             | e.g. ``myPackage``
            - Module            | e.g. ``myPackage.Shapes``
              - Class           | e.g. ``myPackage.Shapes.Circle``
                - Method        | e.g. ``myPackage.Shapes.Circle.Area``
              - Function        | e.g. ``myPackage.Shapes.Distance``
            - SourceFile        | e.g. ``main.c`` - for languages, where the file is the unit
              - Function        | e.g. ``main``

This is how the example renders:

.. tree::

   - CoverageSummary         | the report
     - physical hierarchy    | built from the file paths the report names
       - Directory           | e.g. ``myPackage/``
         - File              | e.g. ``myPackage/Shapes.py``
           - Line            | line number, ``LineCoverageStatus``, coverage count
             - Branch        | ``LineCoverageStatus``, coverage count, target
       - File
     - logical hierarchy     | the language units the report names - each: file, first and last line
       - Package             | e.g. ``myPackage``
         - Module            | e.g. ``myPackage.Shapes``
           - Class           | e.g. ``myPackage.Shapes.Circle``
             - Method        | e.g. ``myPackage.Shapes.Circle.Area``
           - Function        | e.g. ``myPackage.Shapes.Distance``
         - SourceFile        | e.g. ``main.c`` - for languages, where the file is the unit
           - Function        | e.g. ``main``

.. rubric:: How the column is laid out

The directive estimates how wide the column of the entries' texts is, from the tree's left edge: per level, the
indentation and the longest text with its icon, counted in characters. The browser computes the widest of these,
using the indentation the stylesheet states. Each entry's text is then as wide as the column, less its own
indentation, so every description starts at the same position.

* A text is rendered in a font the theme chooses, e.g. a role's literal in a monospace font, so the estimate - in the
  CSS unit ``ch``, the width of a digit - may be off. A text wider than estimated pushes its own description to the
  right; it never overlaps it.
* A text whose rendering differs from its source, e.g. a ``:ref:`` showing a section's title, is estimated by
  what the role is given.
* A description too narrow beside its text - on a narrow screen - wraps below the text.

.. _DIR/Tree/Legend:

Legend
******

An icon option may explain its icon: a ``|`` between spaces separates the icon from its **text**. The texts form the
tree's **legend**, which HTML draws as one line below the tree - or above it, as :rst:dir:`tree:legend` chooses.

* A text is inline ReST, as an entry's description is.
* :rst:dir:`tree:icons` declares a marker with a text on a line of its own, so a text may contain commas. A line
  without a ``|`` is still a list of markers separated by commas.
* The legend lists the icons with a text in the order declared: root, node and leaf first, then the markers. An icon
  without a text isn't listed.
* An icon declared twice with the same text - e.g. a folder for the nodes and for a marker of empty directories - is
  listed once. The same icon with two different texts is an error, as the legend would contradict itself.
* ``:legend: none`` keeps the texts in the source, but draws no legend, e.g. when the page explains the icons once for
  several trees.

.. code-block:: ReST

   .. tree::
      :legend:    top
      :root-icon: 📦 | package
      :node-icon: 📁 | directory
      :leaf-icon: 📄 | file
      :icons:     > 📁 | directory
                  * 🐍 | Python module, linked to its :ref:`API reference <DIR/Tree/Options>`

      - pyTooling.Sphinx
        > :file:`doc`
        - :file:`pyTooling`
          - :file:`Sphinx`
            * :mod:`~pyTooling.Sphinx.Tree`
            * :mod:`~pyTooling.Sphinx.Shields`
        - :file:`README.md`

This is how the example renders:

.. tree::
   :legend:    top
   :root-icon: 📦 | package
   :node-icon: 📁 | directory
   :leaf-icon: 📄 | file
   :icons:     > 📁 | directory
               * 🐍 | Python module, linked to its :ref:`API reference <DIR/Tree/Options>`

   - pyTooling.Sphinx
     > :file:`doc`
     - :file:`pyTooling`
       - :file:`Sphinx`
         * :mod:`~pyTooling.Sphinx.Tree`
         * :mod:`~pyTooling.Sphinx.Shields`
     - :file:`README.md`


.. _DIR/Tree/Options:

Options
*******

.. rst:directive:: .. tree::

   Draws the hierarchy written in the content as a tree.

   .. rst:directive:option:: root-icon: <icon> [| <text>]

      The icon of a root, and the text explaining it in the legend. Default: none.

   .. rst:directive:option:: node-icon: <icon> [| <text>]

      The icon of a node, and the text explaining it in the legend. Default: none.

   .. rst:directive:option:: leaf-icon: <icon> [| <text>]

      The icon of a leaf, and the text explaining it in the legend. Default: none.

   .. rst:directive:option:: expanded-icon: <icon>

      The icon in front of an expanded entry with children. Default: ``▾``.

   .. rst:directive:option:: collapsed-icon: <icon>

      The icon in front of a collapsed entry with children. Default: ``▸``.

   .. rst:directive:option:: icons: <marker> <icon>[, <marker> <icon> ...]

      More markers an entry may start with, each with the icon an entry marked so gets. A marker is one character,
      neither a letter nor a digit. Declaring ``-`` replaces the icon of every kind. The list may continue on the
      next lines. A marker with a text for the legend, ``<marker> <icon> | <text>``, is declared on a line of its own.

   .. rst:directive:option:: legend: top | bottom | none

      Where the legend of the icons with a text is drawn: above the tree, below it, or not at all. Default:
      ``bottom``. Without an icon having a text, the tree has no legend.

   .. rst:directive:option:: expanded-levels: <levels>

      How many levels are expanded initially: ``0`` collapses every entry, ``1`` expands the roots only. Default:
      all.

   .. rst:directive:option:: class: <CSS classes>

      Additional CSS classes on the tree.

.. rubric:: Icons

An icon is written as characters, e.g. ``📁``, or as a Unicode code point, e.g. ``U+1F4C1``. Several words form one
icon. An option without a value draws no icon.


.. _DIR/Tree/Styling:

Styling
*******

The stylesheet draws the lines and the indentation from CSS custom properties, so a project changes them without
replacing the stylesheet - in a stylesheet of its own, listed in ``html_css_files``:

.. code-block:: CSS

   :root {
     --pyTooling-tree-line: 1px dotted #666;
   }

.. list-table::
   :header-rows: 1
   :widths: 35 15 50

   * - Property
     - Default
     - Sets
   * - ``--pyTooling-tree-row-height``
     - ``1.6em``
     - the height of an entry's row
   * - ``--pyTooling-tree-indentation``
     - ``1.4em``
     - how far a child is indented from its parent's expander
   * - ``--pyTooling-tree-expander-width``
     - ``1em``
     - the width of the expander icons
   * - ``--pyTooling-tree-icon-gap``
     - ``0.3em``
     - the gap between an icon and the text
   * - ``--pyTooling-tree-line``
     - ``1px solid #999``
     - the lines, as a CSS ``border``
   * - ``--pyTooling-tree-margin-bottom``
     - ``24px``
     - the space below the tree
   * - ``--pyTooling-tree-column-gap``
     - ``1.5em``
     - the gap between the column of the texts and the descriptions
   * - ``--pyTooling-tree-description-min-width``
     - ``15em``
     - how narrow a description gets beside its text, before it wraps below the text
   * - ``--pyTooling-tree-legend-gap``
     - ``1.5em``
     - the gap between two items of the legend
   * - ``--pyTooling-tree-legend-margin``
     - ``0.5em``
     - the space between the tree and its legend


.. _DIR/Tree/Output:

HTML and other formats
**********************

HTML draws an entry with children as a ``<details>`` element, so a reader folds and unfolds it without JavaScript.
Both expander icons are written, and the stylesheet shows the one matching the entry's state. Icons are hidden from a
screen reader, and so is the legend explaining them.

Every other format, e.g. LaTeX, renders the tree as nested bullet lists, without icons: a PDF can't fold, and
pdfLaTeX stops at a character it has no definition for - which an emoji is. A description follows its entry's text
behind an en dash: ``Directory – e.g. myPackage/``. LaTeX, text, manual pages and Texinfo have no legend, as their
trees show no icons.


.. _DIR/Tree/Errors:

Errors
******

A mistake in the content is reported on the page, where the tree would be, and in the build's log:

.. code-block:: text

   tree: The directive's content holds no entry.
   tree: 'pyTooling' is not an entry, which starts with '- '.
   tree: '+ pyTooling' is not an entry, which starts with '- ', '> '.
   tree: '-' is an entry without text.
   tree: '- a | b | c' has more than one separator ' | '; a '|' in a text is escaped as '\|'.
   tree: '- c' is indented less than the entry above, but not as deep as one of its ancestors.

A mistake in an entry's text, e.g. an unknown role, is reported at the entry's line.

A mistake in the legend's texts is reported likewise, at the directive's line; ``:legend:`` without an icon having a
text is a warning:

.. code-block:: text

   tree: Icon '📁' has two texts: 'directory' and 'folder'.
   tree: ':legend: top' without an icon having a text draws no legend.

A mistake in an icon option is reported by docutils as an invalid option value, followed by its reason:

.. code-block:: text

   '📦 | a | b' has more than one separator ' | '; a '|' in a text is escaped as '\|'.
   '| package' has a text, but no icon.
