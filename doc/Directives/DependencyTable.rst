.. _DIR/DependencyTable:

dependency-table
################

The ``dependency-table`` directive renders a project's dependencies as a table - per package the version
required, its license and what it requires in turn - from the requirements themselves rather than by hand. The data
is fetched from the package index while the documentation is built.

.. attention::

   The directive reads the package index with pyTooling's ``pypi`` extra, a requirement of this package.

.. rubric:: Configuration

A table names an **entrypoint**, which :file:`conf.py` declares:

.. code-block:: Python

   # doc/conf.py
   pyTooling_Dependency_Requirements = {
     "package":       {"file":    "../requirements.txt"},
     "documentation": {"file":    "requirements.txt"},
     "yaml":          {"package": "pyTooling[yaml]"},
   }

Each entrypoint states exactly one of:

``file`` / ``files``
  |rarr| a requirements file, or several, read relative to :file:`conf.py` with their ``-r`` includes followed.
  They are read while :file:`conf.py` is processed, so a path that doesn't exist ends the build with one message.
``package`` / ``packages``
  |rarr| a package, or several, as the package index publishes its **latest release**: ``pyTooling`` for its own
  requirements, ``pyTooling[yaml]`` for what the extra ``yaml`` adds.

.. list-table:: Configuration values in :file:`conf.py`
   :header-rows: 1
   :widths: 40 60

   * - Name
     - Value
   * - ``pyTooling_Dependency_Requirements``
     - The entrypoints, by identifier.
   * - ``pyTooling_Dependency_PackageOverrides``
     - Optional, a YAML file stating the license of a package the index can't answer for, relative to
       :file:`conf.py`.
   * - ``pyTooling_Dependency_IndexURL``
     - Optional, the package index. Default: ``https://pypi.org``.
   * - ``pyTooling_Dependency_APIURL``
     - Optional, the index's JSON API. Default: ``https://pypi.org/pypi/``.

The tables of a build share one view of the index, so a package several tables require is downloaded once. Each
table logs what it cost, and the build ends with the total and the packages whose license couldn't be resolved -
the list the override file answers.

.. rst:directive:: .. dependency-table:: <entrypoint>

   Renders the dependencies of the entrypoint the argument names.

   .. rst:directive:option:: depth: <levels>

      Levels of sub-dependencies to expand. Default: 0, which expands until the tree ends.

      A package whose own dependencies the limit cuts off says so below its line, e.g.
      *… 2 dependencies not expanded (depth limit)*.

   .. rst:directive:option:: simplified-versions: yes | no

      Whether a version constraint is reduced to its lower bound: ``≥9.1`` instead of ``≥9.1, <10``. Default: ``yes``.

   .. rst:directive:option:: version-format: Major | MajorMinor | MajorMinorPatch | All

      How many parts of a version number are printed. Default: ``MajorMinor``.

   .. rst:directive:option:: dependency-format: Package | PackageVersion | PackageLicense | PackageVersionLicense

      What a line of a dependency tree states. Default: ``PackageVersionLicense``.

   .. rst:directive:option:: caption: <text>

      A caption for the table.

.. code-block:: ReST

   .. dependency-table:: package
      :caption: Mandatory dependencies of the pyTooling package.
      :depth: 4

`pyTooling's dependency page <https://pyTooling.github.io/pyTooling/Dependency.html>`__ shows the tables its
documentation renders.
