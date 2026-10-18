.. _DEP:

Dependencies
############

.. _DEP/package:

pyTooling.Sphinx Package (Mandatory)
************************************

.. rubric:: Manually Installing Package Requirements

Use the :file:`requirements.txt` file to install all dependencies via ``pip3`` or install the package directly from
PyPI (see :ref:`INSTALL`).

.. tab-set::

   .. tab-item:: Linux/macOS
      :sync: Linux

      .. code-block:: bash

         pip3 install -U -r requirements.txt

   .. tab-item:: Windows
      :sync: Windows

      .. code-block:: powershell

         pip install -U -r requirements.txt

.. rubric:: Dependency List

.. dependency-table:: package
   :caption: Mandatory dependencies of the pyTooling.Sphinx package.


.. _DEP/reports:

Report Domain (Optional)
************************

The directives of domain ``report`` read unit test reports and analyze the documentation coverage with these
packages. They are optional - only a project using a report needs them - and installed with the extra ``reports``:

.. tab-set::

   .. tab-item:: Linux/macOS
      :sync: Linux

      .. code-block:: bash

         pip3 install -U pyTooling.Sphinx[reports]

   .. tab-item:: Windows
      :sync: Windows

      .. code-block:: powershell

         pip install -U pyTooling.Sphinx[reports]

.. rubric:: Dependency List

:pypi:`pyEDAA.Reports` reads the unit test and code coverage reports and analyzes the documentation coverage.

.. dependency-table:: reports
   :caption: Dependencies added by the ``reports`` extra.



.. _DEP/markdown:

GitHub Markdown (Optional)
**************************

The converter of GitHub-flavoured Markdown into docutils nodes parses Markdown with these packages. They are
optional - only a project converting Markdown needs them - and installed with the extra ``markdown``:

.. tab-set::

   .. tab-item:: Linux/macOS
      :sync: Linux

      .. code-block:: bash

         pip3 install -U pyTooling.Sphinx[markdown]

   .. tab-item:: Windows
      :sync: Windows

      .. code-block:: powershell

         pip install -U pyTooling.Sphinx[markdown]

.. rubric:: Dependency List

:pypi:`markdown-it-py` parses CommonMark, tables, strikethrough, task lists and alerts; :pypi:`mdit-py-plugins`
parses GitHub's autolinks and footnotes.

.. dependency-table:: markdown
   :caption: Dependencies added by the ``markdown`` extra.

An SVG image in the Markdown - other than a shields.io badge, which is fetched as PNG - is converted to PNG for
LaTeX/PDF output, as LaTeX can't include SVG: by Sphinx' extension :mod:`sphinx.ext.imgconverter`, which
pyTooling.Sphinx loads, with `ImageMagick <https://imagemagick.org/>`__. Sphinx looks for ImageMagick only when a
document has an image the builder can't include, and warns once, if it's missing. ImageMagick must be able to read SVG,
e.g. with its delegate ``rsvg-convert``; if a conversion fails, Sphinx stops the build ("convert exited with error").
HTML includes SVG and needs no conversion for it. With only ImageMagick 7's ``magick`` command, set
``image_converter = "magick"`` and ``image_converter_args = ["convert"]`` in :file:`conf.py`.

.. rubric:: Bundled Data

The package contains data of another project for the converter. :ghsrc:`NOTICE.md <NOTICE.md>` lists all content of
other projects in the repository.

.. list-table::
   :header-rows: 1
   :widths: 25 25 25 25

   * - Content
     - File
     - Source
     - License
   * - GitHub's emoji: their characters and shortcodes
     - :file:`pyTooling/Sphinx/Resources/GitHubEmoji.txt`
     - :gh:`gemoji <github/gemoji>` ``db/emoji.json``, v4.1.0 (commit ``5476a66``)
     - MIT, Copyright (c) 2019 GitHub, Inc. - the file's header holds the license text

.. _DEP/testing:

Unit Testing / Coverage (Optional)
**********************************

Additional Python packages needed for testing and code coverage collection. These packages are only needed for
developers or on a CI server.

.. rubric:: Manually Installing Test Requirements

Use the :file:`tests/unit/requirements.txt` file to install all dependencies via ``pip3``. The file will recursively
install the mandatory dependencies too.

.. tab-set::

   .. tab-item:: Linux/macOS
      :sync: Linux

      .. code-block:: bash

         pip3 install -U -r tests/unit/requirements.txt

   .. tab-item:: Windows
      :sync: Windows

      .. code-block:: powershell

         pip install -U -r tests\unit\requirements.txt

.. rubric:: Dependency List

.. dependency-table:: unittest
   :caption: Dependencies for unit testing and code coverage.

.. rubric:: Test Data

The Markdown converter's tests use release notes from GitHub release pages as fixtures. They are in the repository only,
not in the package; :ghsrc:`NOTICE.md <NOTICE.md>` lists them too.

.. list-table::
   :header-rows: 1
   :widths: 25 30 25 20

   * - Content
     - Files
     - Source
     - License of the source project
   * - GHDL release notes v5.0.1
     - :file:`tests/data/GitHubMarkdown/GHDL-v5.0.1.md`
     - :gh:`ghdl/ghdl releases <ghdl/ghdl/releases/tag/v5.0.1>`
     - GPL-2.0
   * - OSVVM release notes 2024.07, 2026.05, 2026.09
     - :file:`tests/data/GitHubMarkdown/OSVVM-*.md`
     - :gh:`OSVVM/OsvvmLibraries releases <OSVVM/OsvvmLibraries/releases>`
     - Apache-2.0
   * - pyTooling release notes v8.0.0, v9.0.0
     - :file:`tests/data/GitHubMarkdown/pyTooling-*.md`
     - :gh:`pyTooling/pyTooling releases <pyTooling/pyTooling/releases>`
     - Apache-2.0


.. _DEP/documentation:

Sphinx Documentation (Optional)
*******************************

Additional Python packages needed for building the documentation. These packages are only needed for developers or on
a CI server.

.. rubric:: Manually Installing Documentation Requirements

Use the :file:`doc/requirements.txt` file to install all dependencies via ``pip3``. The file will recursively install
the mandatory dependencies too.

.. tab-set::

   .. tab-item:: Linux/macOS
      :sync: Linux

      .. code-block:: bash

         pip3 install -U -r doc/requirements.txt

   .. tab-item:: Windows
      :sync: Windows

      .. code-block:: powershell

         pip install -U -r doc\requirements.txt

.. rubric:: Dependency List

.. dependency-table:: documentation
   :caption: Dependencies for building the documentation.
