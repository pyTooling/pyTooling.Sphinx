.. _LINK/External:

External link icons
###################

.. grid:: 2

   .. grid-item::
      :columns: 6

      In HTML, the extension draws an **icon behind each external link**, so a reader sees that a link leaves the
      documentation, and where to, before following it.

      The icon is chosen by the link's **target**: GitHub's mark for a link to GitHub, an envelope for an e-mail
      address, and a square with an arrow pointing out of it for any host without an icon of its own - see
      :ref:`LINK/External/Icons`.

      A document needs no markup: every link written with its URI gets its icon, also a link of a
      :mod:`sphinx.ext.extlinks` role such as ``:gh:``. The configuration value ``pyTooling_ExternalLink_Icons`` adds
      the links to other projects' documentations, or disables the icons - see :ref:`LINK/External/Configuration`.

      A marked link **opens in a new browser tab**, unless ``pyTooling_ExternalLink_NewTab`` is ``False``; an e-mail
      address opens the mail program, as before.

      A **download** gets a download icon - an archive an archive icon - and its **file's size** behind it - see
      :ref:`LINK/External/Downloads`.

   .. grid-item::
      :columns: 6

      .. code-block:: ReST

         Built with `Sphinx <https://www.sphinx-doc.org/>`__,
         hosted at :gh:`pyTooling/pyTooling.Sphinx`, published
         on `PyPI <https://pypi.org/project/pyTooling.Sphinx/>`__.

      This is how the example renders:

      Built with `Sphinx <https://www.sphinx-doc.org/>`__, hosted at :gh:`pyTooling/pyTooling.Sphinx`, published on
      `PyPI <https://pypi.org/project/pyTooling.Sphinx/>`__.


.. _LINK/External/Icons:

Icons
*****

.. list-table::
   :header-rows: 1
   :widths: 30 15 55

   * - Example
     - Icon
     - Target
   * - `Docutils <https://docutils.sourceforge.io/>`__
     - ``external``
     - Any host without an icon of its own, e.g. a site on GitHub Pages, and an intersphinx link with a relative URI.
   * - `someone@example.org <mailto:someone@example.org>`__
     - ``mail``
     - An e-mail address: a URI of scheme ``mailto``.
   * - :download:`pyTooling.Sphinx' logo <../_static/logo.png>`
     - ``download``
     - A link of Sphinx' ``:download:`` role, to a file of the documentation or of another site.
   * - :download:`GHDL 6.0.0 for Windows
       <https://github.com/ghdl/ghdl/releases/download/v6.0.0/ghdl-mcode-6.0.0-ucrt64.zip>`
     - ``archive``
     - A link to an archive: a file name ending in an archive's extension, e.g. ``.zip`` or ``.tar.gz``, in any case -
       see :data:`~pyTooling.Sphinx.ExternalLink.ARCHIVE_FORMATS`. It replaces the download icon and the host's icon.
   * - :gh:`pyTooling/pyTooling.Sphinx`
     - ``github``
     - ``github.com``
   * - `GitLab <https://gitlab.com/>`__
     - ``gitlab``
     - ``gitlab.com``
   * - `Python <https://www.python.org/>`__, `PyPI <https://pypi.org/>`__
     - ``python``
     - ``python.org``, ``pypi.org``
   * - `NumPy <https://numpy.org/>`__
     - ``numpy``
     - ``numpy.org``
   * - `PyPy <https://pypy.org/>`__
     - ``pypy``
     - ``pypy.org``
   * - `pytest <https://docs.pytest.org/>`__
     - ``pytest``
     - ``pytest.org``
   * - `Pydantic <https://docs.pydantic.dev/>`__
     - ``pydantic``
     - ``pydantic.dev``
   * - `Sphinx <https://www.sphinx-doc.org/>`__
     - ``sphinx``
     - ``sphinx-doc.org``
   * - `Read the Docs <https://about.readthedocs.com/>`__,
       `its theme's documentation <https://sphinx-rtd-theme.rtfd.io/>`__
     - ``readthedocs``
     - ``readthedocs.io``, ``readthedocs.org``, ``rtfd.io``: the projects' documentation hosted there, too

* A host's icon is also the icon of its subdomains: ``python.org`` gives ``docs.python.org`` the Python logo.
* A host is compared in lower case, so ``https://GitHub.com/...`` gets GitHub's mark too.
* A site on GitHub Pages - ``<user>.github.io`` - is the documentation hosted there, not GitHub: it gets the generic
  icon.

The hosts with an icon are :data:`~pyTooling.Sphinx.ExternalLink.HOST_ICONS`; ``pyTooling_ExternalLink_Hosts``
adds hosts or replaces an icon.


.. _LINK/External/Links:

Marked links
************

.. list-table::
   :header-rows: 1
   :widths: 50 50

   * - Link
     - Icon
   * - A link with an absolute URI of scheme ``http``, ``https``, ``ftp`` or ``mailto``: named or anonymous, a
       standalone URI or e-mail address, a link of a :mod:`sphinx.ext.extlinks` role.
     - Yes, unless ``pyTooling_ExternalLink_Icons`` is ``none``.
   * - A link resolved to another project's documentation, e.g. by :mod:`sphinx.ext.intersphinx`.
     - If ``pyTooling_ExternalLink_Icons`` is ``all``.
   * - A link within the documentation: a cross-reference, or a relative URI written by hand.
     - No.
   * - A link holding an image, e.g. a badge of the :ref:`shields <DIR/Shields>` directive, or an image with
       ``:target:``.
     - No.
   * - A toctree entry and the navigation.
     - No.
   * - A link of Sphinx' ``:download:`` role, to a file of the documentation or of another site.
     - The download icon, or the archive icon for an archive, unless ``pyTooling_ExternalLink_Icons`` is ``none``. It
       stays in the browser's tab, which saves the file.


.. _LINK/External/Downloads:

Downloads
*********

A file to download is linked with Sphinx' ``:download:`` role - a file of the documentation, and another site's file,
e.g. a release's asset on GitHub, alike:

.. code-block:: ReST

   Download the :download:`logo <_static/logo.png>`, or :download:`GHDL 6.0.0 for Windows
   <https://github.com/ghdl/ghdl/releases/download/v6.0.0/ghdl-mcode-6.0.0-ucrt64.zip>`.

This is how the example renders - this documentation asks no other site for a size, so the second link has none:

   Download the :download:`logo <../_static/logo.png>`, or :download:`GHDL 6.0.0 for Windows
   <https://github.com/ghdl/ghdl/releases/download/v6.0.0/ghdl-mcode-6.0.0-ucrt64.zip>`.

* The link gets the download icon, or the archive icon if the file is an archive. It stays in the browser's tab, which
  saves the file.
* The **file's size** follows the link, and for an archive its format: *logo (61.3 kiB)*, *GHDL 6.0.0 for Windows
  (ZIP, 22.6 MiB)*. The units are binary - 1 kiB is 1024 bytes -: ``B`` below 1 kiB, then ``kiB``, ``MiB`` and
  ``GiB`` with one decimal.

.. hint::

   Link every download with ``:download:``. A link written with its URI to an archive, e.g. to
   ``https://example.org/pkg-1.0.zip``, gets the archive icon and the size too, but only as a fallback for documents
   that don't follow this rule: a link to any other file, e.g. a PDF, isn't recognized as a download.


.. _LINK/External/Downloads/Local:

Files of the documentation
==========================

The size of a file of the documentation is its size on disk when the documentation is built. Every download gets it,
unless ``pyTooling_ExternalLink_DownloadSizes`` is ``False``. A file Sphinx doesn't find gets no size - an archive its
format only -; Sphinx warns about it.


.. _LINK/External/Downloads/Remote:

Other sites' files
==================

The extension asks another site for a file's size only if the file's URI matches a pattern of
``pyTooling_ExternalLink_RemoteSizes`` - by default, it asks no site; an archive gets its format only. It sends an HTTP
``HEAD`` request with Sphinx' :mod:`sphinx.util.requests`, so Sphinx' configuration values ``user_agent``,
``tls_verify`` and ``tls_cacerts`` apply. It follows redirections - e.g. of a GitHub release's asset to its storage -,
and reads the answer's ``Content-Length``. Each URI is asked once per build, however often it is linked.

* A pattern is a glob pattern, compared case-sensitively with the whole URI: ``*`` matches any characters - also
  ``/`` -, ``?`` one character, and ``[...]`` one of the characters listed.
* Only a URI of scheme ``http`` or ``https`` is asked for.
* The extension waits ``pyTooling_ExternalLink_RemoteSizeTimeout`` seconds for an answer, 5 by default.

.. code-block:: Python

   # doc/conf.py
   pyTooling_ExternalLink_RemoteSizes = [
     "https://github.com/pyTooling/*/releases/download/*",   # the releases' assets of an organization's projects
     "https://example.org/files/*.zip",
   ]
   pyTooling_ExternalLink_RemoteSizeTimeout = 2.5

If the size stays unknown - no answer within the time, an HTTP error, or an answer without ``Content-Length`` - the
link gets no size, an archive its format only, e.g. ``(ZIP)``, and Sphinx warns at the link, with the warning type
``pyTooling.download_size`` appended in brackets:

.. code-block:: text

   a.rst:2: WARNING: size of download 'https://example.org/a.zip' unknown: no answer within 2.5 seconds
   a.rst:4: WARNING: size of download 'https://example.org/b.zip' unknown: the server answered 404 Not Found

A project that accepts a missing size suppresses the warning by its type:

.. code-block:: Python

   # doc/conf.py
   suppress_warnings = [
     "pyTooling.download_size",
   ]


.. _LINK/External/Configuration:

Configuration
*************

.. list-table:: Configuration values in :file:`conf.py`
   :header-rows: 1
   :widths: 35 15 50

   * - Name
     - Default
     - Effect
   * - ``pyTooling_ExternalLink_Icons``
     - ``"explicit"``
     - Which external links get an icon:

       ``none``
          No link.
       ``explicit``
          The links written with their URI, also those of an extlinks role.
       ``all``
          These, and the links resolved to another project's documentation, e.g. by intersphinx.
   * - ``pyTooling_ExternalLink_NewTab``
     - ``True``
     - Whether a link with an icon opens in a new browser tab: it gets ``target="_blank"`` and
       ``rel="noopener noreferrer"``. An e-mail address never does; a browser would open an empty tab beside the mail
       program. A screen reader announces the new tab with the icon, e.g. "external link, opens in a new tab".
   * - ``pyTooling_ExternalLink_Hosts``
     - ``{}``
     - More hosts, each with the name of its icon - see :ref:`LINK/External/Icons`. A host given here wins over a
       host of :data:`~pyTooling.Sphinx.ExternalLink.HOST_ICONS`; ``None`` is ``external``.
   * - ``pyTooling_ExternalLink_DownloadSizes``
     - ``True``
     - Whether a download gets its file's size behind its link - see :ref:`LINK/External/Downloads`.
   * - ``pyTooling_ExternalLink_RemoteSizes``
     - ``[]``
     - The glob patterns of the URIs of other sites' files whose size is asked for - see
       :ref:`LINK/External/Downloads/Remote`. Without a pattern, no site is asked.
   * - ``pyTooling_ExternalLink_RemoteSizeTimeout``
     - ``5.0``
     - The seconds to wait for a site's answer to the request for a size; a positive number.

.. code-block:: Python

   # doc/conf.py
   pyTooling_ExternalLink_Icons =             "all"
   pyTooling_ExternalLink_NewTab =            False     # links open in the same tab
   pyTooling_ExternalLink_Hosts =             {
     "gitlab.example.org": "gitlab",     # a GitLab instance of one's own
     "pypi.org":           "external",   # no Python logo for the package index
   }
   pyTooling_ExternalLink_DownloadSizes =     True
   pyTooling_ExternalLink_RemoteSizes =       [
     "https://gitlab.example.org/*/-/releases/*",
   ]
   pyTooling_ExternalLink_RemoteSizeTimeout = 5.0

A malformed value stops the build:

.. code-block:: text

   conf.py: pyTooling_ExternalLink_Icons: 'some' is not a selection of links.
   Allowed values: none, explicit, all.
   conf.py: pyTooling_ExternalLink_RemoteSizeTimeout: Value is not a positive, finite number.
   Got value '0'.


.. _LINK/External/Styling:

Styling
*******

The stylesheet draws an icon from CSS custom properties, so a project changes them without replacing the stylesheet -
in a stylesheet of its own, listed in ``html_css_files``:

.. list-table::
   :header-rows: 1
   :widths: 40 25 35

   * - Property
     - Default
     - Sets
   * - ``--pyTooling-link-icon-size``
     - ``0.8em``
     - the icon's width and height
   * - ``--pyTooling-link-icon-gap``
     - ``0.2em``
     - the gap between the link's text and the icon
   * - ``--pyTooling-link-icon-scale``
     - ``1``; ``1.15`` for ``download``
     - a factor of an icon's size, set on the link's class, e.g. ``a.pytooling-link-icon-download``
   * - ``--pyTooling-link-icon-<icon>``
     - an SVG image
     - the icon's shape, e.g. ``--pyTooling-link-icon-github``

The size behind a download is a ``<span class="pytooling-download-size">``, which a project's stylesheet may style, e.g.
in a smaller font.

An icon is a mask filled with the link's colour, so only the shape of its image counts:

.. code-block:: CSS

   :root {
     --pyTooling-link-icon-size: 0.7em;
     --pyTooling-link-icon-external: url("data:image/svg+xml,...");
   }


.. _LINK/External/Output:

HTML and other formats
**********************

Two post-transforms mark the links in HTML, for every builder of the HTML family:
:class:`~pyTooling.Sphinx.ExternalLink.MarkExternalLinks` before Sphinx resolves the references, and
:class:`~pyTooling.Sphinx.ExternalLink.MarkIntersphinxLinks` after. A marked link gets the CSS classes
``pytooling-external-link`` or ``pytooling-intersphinx-link``, and ``pytooling-link-icon-<icon>`` naming its icon:

.. code-block:: HTML

   <a class="extlink-gh pytooling-external-link pytooling-link-icon-github reference external"
      href="https://GitHub.com/pyTooling/pyTooling.Sphinx">pyTooling/pyTooling.Sphinx</a>

Two more post-transforms work on the downloads, in HTML too: :class:`~pyTooling.Sphinx.ExternalLink.MarkDownloadLinks`
marks them with the CSS class ``pytooling-download-link`` and the download or archive icon, and
:class:`~pyTooling.Sphinx.ExternalLink.AddDownloadSizes` writes their sizes.

* The icon is drawn by the link's ``::after`` pseudo-element, so it stays on the line of the link's last word.
* A screen reader reads the icon's alternative text instead, e.g. *(external link, opens in a new tab)* or
  *(e-mail address)*.
* In a forced-colours mode, e.g. Windows' high contrast themes, the icon keeps the link's colour.
* A link to an archive also gets the CSS class ``pytooling-archive-<extension>``, e.g. ``pytooling-archive-tar-gz``;
  its alternative text names the format, e.g. *(download, ZIP archive)*.
* sphinx_rtd_theme draws a download glyph of its own before a download link's text. A marked download link shows its
  icon behind the text only, like any other link; with ``pyTooling_ExternalLink_Icons`` set to ``none``, the theme's
  glyph stays.

Every other format - e.g. LaTeX - writes the links as before, without a mark and without a size: LaTeX writes a
``:download:`` link as its text, without the file, so a PDF offers no file whose size would help.

The brands' icons - ``github`` to ``readthedocs`` - are their marks from `Simple Icons <https://simpleicons.org/>`__
16.35.0, published under CC0 1.0 Universal; the marks are trademarks of their owners. ``external``, ``mail``,
``download`` and ``archive`` are drawn for pyTooling.Sphinx.
