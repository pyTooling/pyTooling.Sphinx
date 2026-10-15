.. _DIR/UnicodeTable:

unicode-table
#############

.. grid:: 2

   .. grid-item::
      :columns: 6

      The ``unicode-table`` directive lists icons - Unicode characters, e.g. emoji - with their Unicode names and code
      points, e.g. the icons a :ref:`tree <DIR/Tree>` uses.

      The **content** is the icons, one per line, written as characters or as code points. An icon may have a
      **description**, behind a ``|``.

      The **names** and **code points** are computed from the icon, so a row can't contradict its icon.

      In HTML, a **button** beside the icon copies the icon into the clipboard, and a button beside the code points
      copies these - in the form a tree's icon options take them.

   .. grid-item::
      :columns: 6

      .. code-block:: ReST

         .. unicode-table::

            📦             | a package
            U+1F4C1        | a directory
            U+2699 U+FE0F  | a configuration file
            👨‍💻

This is how the example renders:

.. unicode-table::

   📦             | a package
   U+1F4C1        | a directory
   U+2699 U+FE0F  | a configuration file
   👨‍💻

:ref:`DIR/Tree/CommonIcons` lists icons commonly used in a tree, by this directive.


.. _DIR/UnicodeTable/Content:

Content
*******

* An entry is a line holding an icon. Blank lines are ignored.
* An icon is written as characters, e.g. ``📁``, or as Unicode code points, e.g. ``U+1F4C1``. Several words form one
  icon, and characters and code points may be mixed: ``U+2699 U+FE0F`` and ``⚙ U+FE0F`` are the same icon. A code
  point keeps the source readable in an editor whose font lacks the icon's glyph, and shows a variation selector,
  which is invisible as a character.
* A ``|`` between spaces separates the icon from its **description**, which is inline ReST. A table without any
  description has no column for them.
* Spaces around the ``|`` don't matter, so the separators may be aligned in the source. A ``|`` in an inline literal
  or in a role's text separates nothing; elsewhere, a ``|`` belonging to the description is escaped as ``\|``.


.. _DIR/UnicodeTable/Names:

Names and code points
*********************

The names are the ones Python's :mod:`unicodedata` knows, so a name is always the icon's.

* A single character is named by its Unicode name: ``📦`` is ``PACKAGE``.
* A **sequence** is named by its characters, joined by ``+``: ``👨‍💻`` is ``MAN + PERSONAL COMPUTER``. A variation
  selector and the zero width joiner select how the characters are drawn and aren't named: ``⚙️`` - ``U+2699 U+FE0F``
  - is ``GEAR``.
* A character without a name - a control character, a private-use character or a noncharacter - is named by the
  label the Unicode standard gives it, e.g. ``<private-use-E000>``. An icon font such as a Nerd Font maps its icons to
  private-use characters.
* A code point not assigned in the Unicode version of :mod:`unicodedata` is named ``<reserved-XXXX>`` and warned about:
  either it is a typo, or the icon is newer than the Python running the build. Python 3.12 knows Unicode 15.0, 3.13
  Unicode 15.1 and 3.14 Unicode 16.0.

The code points are written as the icon options of the :ref:`tree <DIR/Tree/Options>` take them: ``U+`` and at least
four hexadecimal digits per character, separated by spaces.


.. _DIR/UnicodeTable/Options:

Options
*******

.. rst:directive:: .. unicode-table::

   Lists the icons written in the content, with their names and code points.

   .. rst:directive:option:: class: <CSS classes>

      Additional CSS classes on the table.


.. _DIR/UnicodeTable/Copy:

Copy buttons
************

In HTML, the icon and the code points are each followed by a ``<button>``, labelled for a screen reader - e.g. *Copy
the icon PACKAGE* -, which copies them into the clipboard. After a click, the button shows a check mark for a moment,
and a status message tells a screen reader what was copied.

The buttons work by the script :file:`pyTooling.js`, which the extension links into every HTML page, as it does its
stylesheet. The browser grants a page the clipboard, if it is served by HTTPS or from ``localhost``; elsewhere, a
button turns red.


.. _DIR/UnicodeTable/Styling:

Styling
*******

The stylesheet takes its values from CSS custom properties, so a project changes them without replacing the
stylesheet - in a stylesheet of its own, listed in ``html_css_files``:

.. list-table::
   :header-rows: 1
   :widths: 35 15 50

   * - Property
     - Default
     - Sets
   * - ``--pyTooling-unicode-glyph-size``
     - ``1.5em``
     - the size of the icons
   * - ``--pyTooling-copy-color``
     - ``#666``
     - the colour of a copy button
   * - ``--pyTooling-copy-hover-color``
     - ``#06f``
     - the colour of a copy button under the mouse or with the keyboard focus
   * - ``--pyTooling-copy-success-color``
     - ``#093``
     - the colour of a copy button, which copied its text
   * - ``--pyTooling-copy-failure-color``
     - ``#c00``
     - the colour of a copy button, which couldn't copy its text


.. _DIR/UnicodeTable/Output:

HTML and other formats
**********************

HTML writes the table with its copy buttons. Every other format writes the table without buttons.

LaTeX writes no icons: pdfLaTeX stops at a character it has no definition for - which an emoji is -, and LuaLaTeX
and XeLaTeX need an emoji font to draw one. So a table in LaTeX has no column of icons; the names and the code points
identify them.


.. _DIR/UnicodeTable/Errors:

Errors
******

A mistake in the content is reported on the page, where the table would be, and in the build's log:

.. code-block:: text

   unicode-table: The directive's content holds no entry.
   unicode-table: '| a package' has a description, but no icon.
   unicode-table: '📦 | a | b' has more than one separator ' | '; a '|' in a text is escaped as '\|'.
   unicode-table: 'U+110000' has an invalid icon: 'U+110000' is beyond the last code point U+10FFFF.
   unicode-table: 'U+D800' has an invalid icon: 'U+D800' is a surrogate code point, which is no character.

A code point not assigned in the Unicode version of :mod:`unicodedata` is a warning, at the icon's line; the icon
still gets its row:

.. code-block:: text

   unicode-table: U+0378 isn't assigned in Unicode 16.0.0, which Python's 'unicodedata' knows; its name is unknown.
