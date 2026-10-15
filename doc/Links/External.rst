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
   * - :gh:`pyTooling/pyTooling.Sphinx`
     - ``github``
     - ``github.com``
   * - `GitLab <https://gitlab.com/>`__
     - ``gitlab``
     - ``gitlab.com``
   * - `Python <https://www.python.org/>`__
     - ``python``
     - ``python.org``
   * - `PyPI <https://pypi.org/>`__
     - ``pypi``
     - ``pypi.org``
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
     - The download icon, unless ``pyTooling_ExternalLink_Icons`` is ``none``. It stays in the browser's tab, which
       saves the file.


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

.. code-block:: Python

   # doc/conf.py
   pyTooling_ExternalLink_Icons =  "all"
   pyTooling_ExternalLink_NewTab = False                # links open in the same tab
   pyTooling_ExternalLink_Hosts =  {
     "gitlab.example.org": "gitlab",     # a GitLab instance of one's own
     "pypi.org":           "python",     # Python's logo for the package index
   }

A malformed value stops the build:

.. code-block:: text

   conf.py: pyTooling_ExternalLink_Icons: 'some' is not a selection of links.
   Allowed values: none, explicit, all.
   conf.py: pyTooling_ExternalLink_Hosts: Icon 'hg' of host 'example.org' is not an icon.
   Allowed values: external, mail, github, gitlab, python, pypi, numpy, pypy, pytest, pydantic, readthedocs, sphinx,
   download.


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
   * - ``--pyTooling-link-icon-<icon>``
     - an SVG image
     - the icon's shape, e.g. ``--pyTooling-link-icon-github``

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

* The icon is drawn by the link's ``::after`` pseudo-element, so it stays on the line of the link's last word.
* A screen reader reads the icon's alternative text instead, e.g. *(external link, opens in a new tab)* or
  *(e-mail address)*.
* In a forced-colours mode, e.g. Windows' high contrast themes, the icon keeps the link's colour.

Every other format - e.g. LaTeX - writes the links as before, without a mark.

The brands' icons - ``github`` to ``readthedocs`` - are their marks from `Simple Icons <https://simpleicons.org/>`__
16.35.0, published under CC0 1.0 Universal; the marks are trademarks of their owners. ``external`` and ``mail`` are
drawn for pyTooling.Sphinx.
