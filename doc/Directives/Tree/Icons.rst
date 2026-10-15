.. _DIR/Tree/CommonIcons:

Common Icons
############

Icons commonly used in a :ref:`tree <DIR/Tree>`, per topic: each with its Unicode name and its code points, in the
form an icon option takes them. In HTML, the button beside an icon copies the icon, and the button beside the code
points copies these.

An icon with a variation selector, e.g. ``U+2699 U+FE0F``, is drawn as a colourful emoji; without it, many fonts draw
the character as a black and white symbol. The tables are written with the :ref:`unicode-table <DIR/UnicodeTable>`
directive, which computes the names and code points.

.. only:: latex

   The PDF lists the names and code points only, as LaTeX draws no emoji.


.. _DIR/Tree/CommonIcons/Files:

Files and Directories
*********************

.. unicode-table::

   📁               | a directory
   📂               | an expanded directory
   U+1F5C2 U+FE0F   | a collection of directories, e.g. a namespace package
   📄               | a file
   📝               | a text document, e.g. :file:`README.md`
   📜               | a script, e.g. :file:`run.ps1`
   📋               | a list, e.g. :file:`requirements.txt`
   📊               | a report or data, e.g. a coverage report
   U+1F5BC U+FE0F   | an image
   U+1F5C3 U+FE0F   | an archive, e.g. a wheel
   🔒               | a lock file, or a file not to be edited
   U+1F5D1 U+FE0F   | an obsolete or deleted file


.. _DIR/Tree/CommonIcons/Code:

Code and Packages
*****************

.. unicode-table::

   📦               | a package
   🐍               | a Python module
   U+2699 U+FE0F    | a configuration file, e.g. :file:`pyproject.toml`
   🧩               | a plugin or an extension
   🧱               | a building block, e.g. a class
   🔌               | an interface or an adapter
   🔧               | a tool
   U+1F6E0 U+FE0F   | build tooling, e.g. :file:`setup.py`
   📚               | a library
   📖               | documentation
   🧪               | tests
   🐞               | a bug, or a debugging aid
   🔑               | a key or a secret
   💻               | a program, e.g. a command line interface


.. _DIR/Tree/CommonIcons/CI:

CI and Workflows
****************

.. unicode-table::

   🔄               | a workflow or a pipeline
   U+25B6 U+FE0F    | a job, or a run
   🔗               | an action, or a reusable workflow
   🐳               | a container
   U+1F3D7 U+FE0F   | a build
   🚀               | a release, or a deployment
   📤               | an artifact uploaded
   📥               | an artifact downloaded
   U+23F1 U+FE0F    | a schedule, or a timeout
   🔀               | a matrix, or a merge
   🌿               | a branch
   🔖               | a tag, e.g. ``v1.2.0``
   U+1F3F7 U+FE0F   | a label, e.g. of an issue


.. _DIR/Tree/CommonIcons/Status:

Status
******

.. unicode-table::

   ✅               | passed, done
   ❌               | failed
   U+26A0 U+FE0F    | a warning
   U+2139 U+FE0F    | information
   ❓               | unknown
   ⛔               | blocked, forbidden
   🚧               | work in progress
   ⏳               | pending, running
   U+23ED U+FE0F    | skipped
   🟢               | good
   🟡               | degraded, partial
   🔴               | bad


.. _DIR/Tree/CommonIcons/Text:

Text Symbols
************

Characters without an emoji presentation: they are drawn in the text's font and colour, so they suit a tree's
expanders and a plain style.

.. unicode-table::

   ▾                | expanded, the default of ``:expanded-icon:``
   ▸                | collapsed, the default of ``:collapsed-icon:``
   •                | an item
   →                | a reference, or a result
   ✓                | passed, done
   ✗                | failed
