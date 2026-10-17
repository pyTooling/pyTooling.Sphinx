.. _ROLE/Style:

Style roles
###########

The extension registers roles styling inline text, and a stylesheet giving them their meaning, linked into every
HTML page.

.. grid:: 2

   .. grid-item::
      :columns: 6

      .. list-table::
         :header-rows: 1
         :widths: 35 65

         * - Role
           - Renders
         * - ``:bolditalic:``
           - :bolditalic:`bold and italic`
         * - ``:underline:``
           - :underline:`underlined`
         * - ``:strike:``
           - :strike:`struck through`
         * - ``:xlarge:``
           - :xlarge:`extra large`
         * - ``:red:``
           - :red:`red`
         * - ``:green:``
           - :green:`green`
         * - ``:blue:``
           - :blue:`blue`
         * - ``:purple:``
           - :purple:`purple`
         * - ``:deletion:``
           - :deletion:`deleted`
         * - ``:addition:``
           - :addition:`added`

   .. grid-item::
      :columns: 6

      .. code-block:: ReST

         A :red:`warning` and a :deletion:`removed` word.

      A style role puts CSS classes on the text; the stylesheet gives them their meaning. ``:deletion:`` and
      ``:addition:`` are the two a diff needs.

      Every colour and size is a CSS custom property, so a project changes it without replacing the stylesheet - in
      a stylesheet of its own, listed in ``html_css_files``:

      .. code-block:: CSS

         :root {
           --pyTooling-color-red: #b00020;
         }

      The properties are ``--pyTooling-color-red``, ``-green``, ``-blue``, ``-purple`` and
      ``--pyTooling-xlarge-size``.

.. rubric:: LaTeX

LaTeX writes a style role's text as ``\DUrole{<class>}{<text>}``, which calls command ``\DUrole<class>``, if it is
defined. The extension brings the LaTeX package :file:`pyTooling.Sphinx.sty`, which defines two of them: ``:strike:``
and ``:underline:`` - and strikethrough in converted Markdown - draw their line with package ``ulem`` (option
``normalem``, so ``\emph`` stays italic). The extension writes the file into the LaTeX build directory and loads it
with ``\usepackage{pyTooling.Sphinx}``; a project needs no ``latex_elements`` for it. The other style roles write their
text unstyled in LaTeX.
