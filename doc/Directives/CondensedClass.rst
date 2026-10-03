.. _DOC/Sphinx/CondensedClass:

condensed-class
###############

.. grid:: 2

   .. grid-item::
      :columns: 6

      The ``condensed-class`` directive renders a class' **public interface** as a code block: the class line, its
      class variables, its methods and its properties, each with the signature it is declared with, and ``...`` for
      a body.

      **The source is parsed, not imported.** Annotations appear as they are written - ``Nullable[str]``, not the
      ``Optional[str]`` an import resolves it to - members appear in the order of the file, and the file becomes a
      dependency of the page, so editing the class rebuilds the page.

      Left out is what the surrounding text is for: bodies, doc-strings, private members (one leading underscore),
      and the annotated fields of a slotted class.

   .. grid-item::
      :columns: 6

      .. code-block:: ReST

         .. condensed-class:: pyTooling.GenericPath.URL.Host

This is how the example renders - a class derived from a mixin, with its initializer, two read-only properties, a
method and ``__str__()``:

.. condensed-class:: pyTooling.GenericPath.URL.Host

.. rst:directive:: .. condensed-class:: <dotted name of a class>

   Renders the interface of the class the argument names. The longest prefix of the name that is a module is
   the module; the rest is the class, and may name a class nested in a class.

   .. rst:directive:option:: members: <kinds>

      The kinds of member to render, separated by commas, in any case: ``ClassVariables``, ``Dunders``,
      ``Methods``, ``Properties`` or ``All``. Default: ``All``.

      A property is a method decorated with ``@property``, ``@readonly``, ``@cached_property`` or as a setter or
      deleter; a dunder is a method named ``__<name>__``.

   .. rst:directive:option:: exclude-members: <names>

      Names of methods not to render, separated by commas.

   .. rst:directive:option:: indent: <columns>

      Width of one indentation level. Default: 2.

   .. rst:directive:option:: width: <columns>

      Column a signature is wrapped at, one parameter per line. Default: 100.

   .. rst:directive:option:: caption: <text>

      A caption for the code block.
