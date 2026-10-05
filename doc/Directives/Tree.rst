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

      The **options** choose an icon per kind of entry, and how many levels are expanded initially. In HTML, every
      entry with children folds and unfolds on a click.

   .. grid-item::
      :columns: 6

      .. code-block:: ReST

         .. tree::
            :root-icon: U+1F4E6
            :node-icon: U+1F4C1
            :leaf-icon: U+1F4C4

            - pyTooling.Sphinx
              - :file:`doc`:
              - :file:`pyTooling`
                - :file:`Sphinx`
                  - :mod:`~pyTooling.Sphinx.Tree`
                  - :mod:`~pyTooling.Sphinx.Shields`
              - :file:`README.md`

This is how the example renders:

.. tree::
   :root-icon: U+1F4E6
   :node-icon: U+1F4C1
   :leaf-icon: U+1F4C4

   - pyTooling.Sphinx
     - :file:`doc`:
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

* An entry is a line starting with ``-`` and a space. Blank lines are ignored.
* An entry indented deeper than the entry above it is that entry's child. Siblings are indented alike; how deep a
  child is indented doesn't matter.
* An entry without a parent is a **root**, an entry with children is a **node**, and every other entry is a
  **leaf**. A content may hold several roots.
* A trailing colon makes an entry a node without children, e.g. an empty directory. It isn't shown. A text that
  really ends in a colon escapes it: ``\:``.
* An entry's text is inline ReST: roles, emphasis, literals and links.

.. code-block:: ReST

   .. tree::

      - root
        - node
          - leaf
        - empty node:
        - Note\:


.. _DIR/Tree/Options:

Options
*******

.. rst:directive:: .. tree::

   Draws the hierarchy written in the content as a tree.

   .. rst:directive:option:: root-icon: <icon>

      The icon of a root. Default: none.

   .. rst:directive:option:: node-icon: <icon>

      The icon of a node. Default: none.

   .. rst:directive:option:: leaf-icon: <icon>

      The icon of a leaf. Default: none.

   .. rst:directive:option:: expanded-icon: <icon>

      The icon in front of an expanded entry with children. Default: ``▾``.

   .. rst:directive:option:: collapsed-icon: <icon>

      The icon in front of a collapsed entry with children. Default: ``▸``.

   .. rst:directive:option:: expanded-levels: <levels>

      How many levels are expanded initially: ``0`` collapses every entry, ``1`` expands the roots only. Default:
      all.

   .. rst:directive:option:: class: <CSS classes>

      Additional CSS classes on the tree.

.. rubric:: Icons

An icon is written as characters, e.g. ``📁``, or as a Unicode code point, e.g. ``U+1F4C1`` - which keeps a
document readable in an editor whose font lacks the glyph. Several words form one icon. An option without a value
draws no icon.


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


.. _DIR/Tree/Output:

HTML and other formats
**********************

HTML draws an entry with children as a ``<details>`` element, so a reader folds and unfolds it without JavaScript.
Both expander icons are written, and the stylesheet shows the one matching the entry's state. Icons are hidden from a
screen reader.

Every other format, e.g. LaTeX, renders the tree as nested bullet lists, without icons: a PDF can't fold, and
pdfLaTeX stops at a character it has no definition for - which an emoji is.


.. _DIR/Tree/Errors:

Errors
******

A mistake in the content is reported on the page, where the tree would be, and in the build's log:

.. code-block:: text

   tree: The directive's content holds no entry.
   tree: 'pyTooling' is not an entry, which starts with '- '.
   tree: '-' is an entry without text.
   tree: '- c' is indented less than the entry above, but not as deep as one of its ancestors.

A mistake in an entry's text, e.g. an unknown role, is reported at the entry's line.
