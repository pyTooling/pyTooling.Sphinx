.. _DIR/Abbreviations:

abbreviations
#############

.. grid:: 2

   .. grid-item::
      :columns: 6

      The ``abbreviations`` directive holds a list of abbreviations: each with its long form, optionally its plurals,
      and a description like a glossary's. The roles ``:acs:``, ``:acl:``, ``:acf:`` and their plurals refer to an
      abbreviation from any document, in the form they name - as LaTeX' ``acro`` package does.

      Every reference links to the abbreviation in the list. In HTML, a short form shows its long form in a box when
      the mouse is over it - and, if configured, the summary of its description.

   .. grid-item::
      :columns: 6

      .. code-block:: ReST

         .. abbreviations::

            FSM
               :long:        finite-state machine
               :long-plural: finite-state machines

               A machine in exactly one of a finite number of
               states at a time.

            HDL
               :long: hardware description language

         An :acs:`FSM` is described in an :acs:`HDL`; a
         design holds several :aclp:`FSM`.

This is how the example renders:

.. abbreviations::

   FSM
      :long:        finite-state machine
      :long-plural: finite-state machines

      A machine in exactly one of a finite number of states at a time.

   HDL
      :long: hardware description language

An :acs:`FSM` is described in an :acs:`HDL`; a design holds several :aclp:`FSM`.


.. _DIR/Abbreviations/Content:

Content
*******

* The content is a definition list. A term is an abbreviation, written as it is shown.
* An abbreviation's definition starts with a field list stating its forms. A description may follow, as in a
  glossary; it may refer to other abbreviations.
* Each abbreviation is listed once in the whole documentation; the list may be on a page of its own. An abbreviation
  gets no entry in the general index.
* The list is shown in alphabetical order, ignoring case, whatever order the source has. With ``:ordered: no``, it is
  shown in the source's order.

.. list-table::
   :header-rows: 1
   :widths: 20 15 65

   * - Field
     - Required
     - States
   * - ``:long:``
     - yes
     - the long form, e.g. ``finite-state machine``
   * - ``:plural:``
     - no
     - the plural of the abbreviation; default: the abbreviation followed by ``s``
   * - ``:long-plural:``
     - no
     - the plural of the long form; default: the long form followed by ``s``

A form is shown as plain text wherever a role refers to it; in the list, the long form keeps its inline markup.


.. _DIR/Abbreviations/Roles:

Roles
*****

.. list-table::
   :header-rows: 1
   :widths: 20 40 40

   * - Role
     - Writes
     - Example
   * - ``:acs:`` (``:ac:``)
     - the abbreviation
     - :acs:`FSM`
   * - ``:acl:``
     - the long form
     - :acl:`FSM`
   * - ``:acf:``
     - the full form: the long form, then the abbreviation in parentheses
     - :acf:`FSM`
   * - ``:acsp:`` (``:acp:``)
     - the plural of the abbreviation
     - :acsp:`FSM`
   * - ``:aclp:``
     - the plural of the long form
     - :aclp:`FSM`
   * - ``:acfp:``
     - the plural of the full form
     - :acfp:`FSM`

* A role always writes the form it names. A reader doesn't read a page from top to bottom, so there is no first use
  that spells an abbreviation out: ``:ac:`` and ``:acp:`` are ``:acs:`` and ``:acsp:``.
* A text written as the role's title replaces the form: ``:acs:`FSM-based <FSM>``` writes
  :acs:`FSM-based <FSM>`. A form the fields don't state, e.g. a genitive, is written this way.
* The roles also exist in their domain ``abbreviation``, e.g. ``:abbreviation:acs:``.


.. _DIR/Abbreviations/Options:

Options
*******

.. rst:directive:: .. abbreviations::

   Lists abbreviations, each with its forms and an optional description.

   .. rst:directive:option:: ordered: yes | no

      Whether the list is shown in alphabetical order. Default: ``yes``.

   .. rst:directive:option:: class: <CSS classes>

      Additional CSS classes on the list.


.. _DIR/Abbreviations/Configuration:

Configuration
*************

.. list-table:: Configuration values in :file:`conf.py`
   :header-rows: 1
   :widths: 40 15 45

   * - Name
     - Default
     - Effect
   * - ``pyTooling_Abbreviation_ShowSummary``
     - ``False``
     - If ``True``, the box in HTML also shows the **summary** of an abbreviation's description: its first paragraph,
       as plain text. An abbreviation without a description shows its long form only.

The summary is the description's text up to the first blank line - the same split pyTooling applies to a doc-string
(:func:`pyTooling.Documentation.splitDocString`).

.. code-block:: Python

   # doc/conf.py
   pyTooling_Abbreviation_ShowSummary = True


.. _DIR/Abbreviations/Styling:

Styling
*******

The stylesheet draws the box from CSS custom properties, so a project changes them without replacing the stylesheet -
in a stylesheet of its own, listed in ``html_css_files``:

.. list-table::
   :header-rows: 1
   :widths: 40 25 35

   * - Property
     - Default
     - Sets
   * - ``--pyTooling-abbreviation-underline``
     - ``1px dotted``
     - the underline of a short form
   * - ``--pyTooling-abbreviation-background``
     - ``#fff``
     - the box' background
   * - ``--pyTooling-abbreviation-border``
     - ``1px solid #999``
     - the box' border, as a CSS ``border``
   * - ``--pyTooling-abbreviation-shadow``
     - ``0 2px 6px rgba(0, 0, 0, 0.2)``
     - the box' shadow
   * - ``--pyTooling-abbreviation-max-width``
     - ``30em``
     - how wide the box gets before its text wraps


.. _DIR/Abbreviations/Output:

HTML and other formats
**********************

HTML writes a short form as an ``<abbr>`` element holding the box, which the stylesheet shows while the mouse is over
the abbreviation or its link has the keyboard focus - without JavaScript. Every other format, e.g. LaTeX, writes the
form with a hyperlink to the list.

The box shows the long form, below it the summary if configured. The abbreviation itself is shown in front of the
long form only if a title replaced it in the text, e.g. ``:acs:`FSM-based <FSM>```: otherwise it is the hovered text.

The box is part of the link: clicking anywhere in it opens the abbreviation's entry in the list. The summary is plain
text, so a reference in a description - e.g. to another abbreviation - is shown as its text, not as a link.


.. _DIR/Abbreviations/Errors:

Errors
******

A mistake in the list is reported on the page, where the list would be, and in the build's log:

.. code-block:: text

   abbreviations: The directive's content isn't a definition list of abbreviations.
   abbreviations: Abbreviation 'FSM' doesn't start with a field list, e.g. ':long:'.
   abbreviations: Abbreviation 'FSM' has no field ':long:'.
   abbreviations: Abbreviation 'FSM' has an unknown field ':short:'.
   abbreviations: Abbreviation 'FSM' states field ':long:' twice.
   abbreviations: Field ':long:' of abbreviation 'FSM' isn't a single paragraph.
   abbreviations::ordered: 'maybe' not supported for a boolean value (yes/true, no/false).

A reference to an abbreviation that isn't listed, or an abbreviation listed twice, is reported as a warning:

.. code-block:: text

   WARNING: abbreviation 'XYZ' isn't in a list of abbreviations [ref.acs]
   WARNING: abbreviation 'HDL' is in the list of document 'index' already
