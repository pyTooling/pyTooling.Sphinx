.. _DIR/DependencyTable:

dependency-table
################

The ``dependency-table`` directive renders a project's dependencies as a table - per package the version
required, its license and what it requires in turn - from the requirements themselves rather than by hand. The data
is fetched from the package index while the documentation is built.

.. attention::

   The directive reads the package index with pyTooling's ``dependencies`` extra, a requirement of this package.

.. rubric:: Configuration

A table names an **entrypoint**, which :file:`conf.py` declares:

.. code-block:: Python

   # doc/conf.py
   pyTooling_Dependency_Requirements = {
     "package":       {"file":      "../requirements.txt"},
     "documentation": {"file":      "requirements.txt"},
     "yaml":          {"package":   "pyTooling[yaml]"},
     "packaging":     {"pyproject": True},
   }

Each entrypoint states exactly one of:

``file`` / ``files``
  |rarr| a requirements file, or several, read relative to :file:`conf.py` with their ``-r`` includes followed.
  They are read while :file:`conf.py` is processed, so a path that doesn't exist ends the build with one message.
``package`` / ``packages``
  |rarr| a package, or several, as the package index publishes its **latest release**: ``pyTooling`` for its own
  requirements, ``pyTooling[yaml]`` for what the extra ``yaml`` adds.
``pyproject``
  |rarr| the project's :file:`pyproject.toml` file: the build requirements of its ``[build-system]`` table
  (:pep:`518`), which ``pip`` and ``build`` install into an isolated build environment. ``True`` reads
  :file:`pyproject.toml` in the project's root directory, a string is a path relative to that directory
  (``"package/pyproject.toml"``), and ``None`` declares a project without such a file - its table is empty. A file
  without a ``[build-system]`` table has no build requirements. Like a requirements file, it is read while
  :file:`conf.py` is processed. A project has one such file, so there is no plural form.

.. list-table:: Configuration values in :file:`conf.py`
   :header-rows: 1
   :widths: 40 60

   * - Name
     - Value
   * - ``pyTooling_Dependency_Requirements``
     - The entrypoints, by identifier.
   * - ``pyTooling_ProjectRoot``
     - Optional, the project's root directory, relative to :file:`conf.py`; a ``pyproject`` path is relative to it.
       Default: the parent of the directory :file:`conf.py` is in, e.g. ``"../.."`` for :file:`docs/sphinx/conf.py`.
   * - ``pyTooling_Dependency_PackageOverrides``
     - Optional, a YAML file stating the license of a package the index can't answer for, relative to
       :file:`conf.py`. Reading it needs pyTooling's ``yaml`` extra.
   * - ``pyTooling_Dependency_IndexURL``
     - Optional, the package index. Default: ``https://pypi.org``.
   * - ``pyTooling_Dependency_APIURL``
     - Optional, the index's JSON API. Default: ``https://pypi.org/pypi/``.

The requirements are resolved by pyTooling's :class:`~pyTooling.Dependency.Resolver.Resolver`: per requirement the
newest release matching it - a pre-release only if the requirement names one or nothing else matches -, its
unconditional requirements and those of the extras the requirement names (``pyTooling[yaml]``), as deep as
``:depth:`` allows. A package already on the path isn't listed again, so a dependency cycle ends. The packages of one
level are downloaded in parallel.

The tables of a build share one view of the index, so a package several tables require is downloaded once. Each
table logs what it cost, and the build ends with the total and the packages whose license couldn't be resolved -
the list the override file answers.

A package is shown with the extras its requirement names, sorted: ``pyTooling[dependencies]``, as its dependencies
differ from those of ``pyTooling``. When several statements of an entrypoint require a package - e.g. a file and the
file it includes with ``-r`` -, the last statement's constraint is used with the extras of all of them, as ``pip``
installs every extra any statement names.

.. rst:directive:: .. dependency-table:: <entrypoint>

   Renders the dependencies of the entrypoint the argument names.

   .. rst:directive:option:: depth: <levels>

      Levels of sub-dependencies to expand. Default: 0, which expands until the tree ends.

      A package whose own dependencies the limit cuts off says so below its line, e.g.
      *… 2 more dependencies not expanded*.

   .. rst:directive:option:: simplified-versions: yes | no

      Whether a version constraint is reduced to its lower bound: ``≥9.1`` instead of ``≥9.1, <10``. Default: ``yes``.

   .. rst:directive:option:: version-format: major | major-minor | major-minor-patch | all

      How many parts of a version number are printed. Default: ``major-minor``.

   .. rst:directive:option:: dependency-format: package | package-version | package-license | package-version-license

      What a line of a dependency tree states. Default: ``package-version-license``.

   .. rst:directive:option:: duplicates: expanded | collapsed | reference

      How a tree shows the dependencies of a **duplicate**, a package whose dependencies an earlier line of the table
      already shows. Default: ``collapsed``.

      ``expanded``
         |rarr| shown again, as at the earlier line.
      ``collapsed``
         |rarr| folded below a marker, e.g. *… same 12 dependencies as listed at sphinx*, which links to the earlier
         line. In HTML, a click on the marker unfolds them; LaTeX, text, manual pages and Texinfo show the marker alone.
      ``reference``
         |rarr| replaced by the marker.

      Every package of the table's first column is an original, so a dependency the table lists in a row of its own
      links to that row. Any other package's first line in reading order is the original - also a package two trees
      share, several levels down. The duplicate's own line keeps its version constraint and license, as these differ
      by what requires the package. A line whose dependencies the ``:depth:`` limit cut off is no original.

      The marker links to the original's row or line by a readable ID, ``#dependency-<entrypoint>-<package>``, e.g.
      ``#dependency-documentation-requests``. In HTML, the row or line with its dependencies is highlighted after the
      jump, the color fading out in 2.5 seconds - or staying, if the reader's system asks for reduced motion. The
      stylesheet's custom property ``--pyTooling-table-target-color`` sets the color, by default Sphinx' highlight
      yellow.

   .. rst:directive:option:: duplicate-match: exact | subset | name

      When a line is a duplicate of an earlier line of the same package. Default: ``subset``.

      ``exact``
         |rarr| the same release with the same extras.
      ``subset``
         |rarr| the same release with the earlier line's extras or fewer: ``pyTooling`` is a duplicate of
         ``pyTooling[dependencies]``, as everything it requires is shown there; ``pyTooling[yaml]`` is not.
      ``name``
         |rarr| any release with any extras.

   .. rst:directive:option:: caption: <text>

      A caption for the table.

.. code-block:: ReST

   .. dependency-table:: package
      :caption: Mandatory dependencies of the pyTooling package.
      :depth: 4

`pyTooling's dependency page <https://pyTooling.github.io/pyTooling/Dependency.html>`__ shows the tables its
documentation renders.
