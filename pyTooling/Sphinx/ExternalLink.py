# ==================================================================================================================== #
#             _____           _ _               ____        _     _                                                    #
#  _ __  _   |_   _|__   ___ | (_)_ __   __ _  / ___| _ __ | |__ (_)_ __ __  __                                        #
# | '_ \| | | || |/ _ \ / _ \| | | '_ \ / _` | \___ \| '_ \| '_ \| | '_ \\ \/ /                                        #
# | |_) | |_| || | (_) | (_) | | | | | | (_| |_ ___) | |_) | | | | | | | |>  <                                         #
# | .__/ \__, ||_|\___/ \___/|_|_|_| |_|\__, (_)____/| .__/|_| |_|_|_| |_/_/\_\                                        #
# |_|    |___/                          |___/        |_|                                                               #
# ==================================================================================================================== #
# Authors:                                                                                                             #
#   Patrick Lehmann                                                                                                    #
#                                                                                                                      #
# License:                                                                                                             #
# ==================================================================================================================== #
# Copyright 2026-2026 Patrick Lehmann - Bötzingen, Germany                                                             #
#                                                                                                                      #
# Licensed under the Apache License, Version 2.0 (the "License");                                                      #
# you may not use this file except in compliance with the License.                                                     #
# You may obtain a copy of the License at                                                                              #
#                                                                                                                      #
#   http://www.apache.org/licenses/LICENSE-2.0                                                                         #
#                                                                                                                      #
# Unless required by applicable law or agreed to in writing, software                                                  #
# distributed under the License is distributed on an "AS IS" BASIS,                                                    #
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.                                             #
# See the License for the specific language governing permissions and                                                  #
# limitations under the License.                                                                                       #
#                                                                                                                      #
# SPDX-License-Identifier: Apache-2.0                                                                                  #
# ==================================================================================================================== #
#
"""
Icons behind the external links of a document in HTML, each chosen by the link's target.

A link to GitHub gets GitHub's mark, an e-mail address an envelope, and a link to a host without an icon of its own a
square with an arrow pointing out of it.

Two post-transforms mark the links, for HTML only: :class:`MarkExternalLinks` before Sphinx resolves the references,
so it sees the links written with their URI - also those of a :mod:`sphinx.ext.extlinks` role -, and
:class:`MarkIntersphinxLinks` after, so it sees the links Sphinx resolved to another project's documentation - e.g. by
:mod:`sphinx.ext.intersphinx`. A marked link gets a CSS class naming its icon, which the stylesheet draws, and opens
in a new browser tab - unless configuration value ``pyTooling_ExternalLink_NewTab`` is ``False``, or the link is an
e-mail address.

A third post-transform, :class:`MarkDownloadLinks`, gives the links of Sphinx' ``:download:`` role a download icon.

.. code-block:: Python

   # doc/conf.py
   pyTooling_ExternalLink_Icons =  "all"
   pyTooling_ExternalLink_NewTab = True
   pyTooling_ExternalLink_Hosts =  {
     "gitlab.example.org": "gitlab",
   }

.. seealso::

   :ref:`LINK/External`
      |rarr| The icons, the configuration values and the stylesheet's custom properties, with rendered examples.
"""
from typing                            import Any, ClassVar, Literal, Mapping, Self
from urllib.parse                      import urlsplit

from docutils                          import nodes
from sphinx.addnodes                   import download_reference
from sphinx.application                import Sphinx
from sphinx.config                     import Config
from sphinx.transforms.post_transforms import SphinxPostTransform

from pyTooling.Common                  import StringEnum, getFullyQualifiedName
from pyTooling.Decorators              import export
from pyTooling.Sphinx                  import SphinxExtensionError


__all__ = ["CONFIG_PREFIX", "HOST_ICONS"]

#: Prefix of the configuration values, e.g. ``pyTooling_ExternalLink_Icons``.
CONFIG_PREFIX = "pyTooling_ExternalLink"


@export
class ExternalLinkIcons(StringEnum):
	"""
	Which external links get an icon, as configuration value ``pyTooling_ExternalLink_Icons`` states it.
	"""

	Disabled = "none"      #: No link.
	Explicit = "explicit"  #: Links written with their URI, also those of a :mod:`sphinx.ext.extlinks` role.
	All =      "all"       #: These, and links resolved to another project's documentation.

	DEFAULT =  Explicit    #: Without a configuration value, the links written with their URI get an icon.


@export
class LinkIcon(StringEnum):
	"""
	The icon drawn behind an external link; the link gets the CSS class ``pytooling-link-icon-<value>``.
	"""

	External =    "external"     #: A square with an arrow pointing out of it.
	Mail =        "mail"         #: An envelope.
	GitHub =      "github"       #: GitHub's mark.
	GitLab =      "gitlab"       #: GitLab's tanuki.
	Python =      "python"       #: Python's logo.
	NumPy =       "numpy"        #: NumPy's logo.
	PyPy =        "pypy"         #: PyPy's logo.
	Pytest =      "pytest"       #: pytest's logo.
	Pydantic =    "pydantic"     #: Pydantic's logo.
	ReadTheDocs = "readthedocs"  #: Read the Docs' logo.
	Sphinx =      "sphinx"       #: Sphinx' logo.
	Download =    "download"     #: An arrow pointing down into a tray; the icon of a download link.

	DEFAULT =     External       #: A host without an icon of its own gets the square with the arrow.

	@classmethod
	def FromURI(cls, uri: str, hosts: Mapping[str, Self]) -> Self:
		"""
		Choose the icon of a link by its target.

		A ``mailto:`` URI gets :attr:`Mail`. Any other URI gets the icon of its host, which is looked up in ``hosts``
		with its full domain name first, then without its first label, and so on: ``docs.python.org`` is found as
		``python.org``. A URI without a host, or with a host not found, gets :attr:`DEFAULT`.

		:param uri:   The link's target.
		:param hosts: The icons, keyed by domain name in lower case.
		:returns:     The link's icon.
		"""
		target = urlsplit(uri)
		if target.scheme == "mailto":
			return cls.Mail
		elif (host := target.hostname) is None:
			return cls.DEFAULT

		labels = host.split(".")
		for index in range(len(labels)):
			if (domainName := ".".join(labels[index:])) in hosts:
				return hosts[domainName]

		return cls.DEFAULT


#: The icon of a link to a host or to one of its subdomains, keyed by the host's domain name in lower case.
#:
#: A project adds hosts, or replaces an icon, with configuration value ``pyTooling_ExternalLink_Hosts``.
HOST_ICONS: dict[str, LinkIcon] = {
	"github.com":      LinkIcon.GitHub,
	"gitlab.com":      LinkIcon.GitLab,
	"python.org":      LinkIcon.Python,
	"pypi.org":        LinkIcon.Python,
	"numpy.org":       LinkIcon.NumPy,
	"pypy.org":        LinkIcon.PyPy,
	"pytest.org":      LinkIcon.Pytest,
	"pydantic.dev":    LinkIcon.Pydantic,
	"readthedocs.io":  LinkIcon.ReadTheDocs,
	"readthedocs.org": LinkIcon.ReadTheDocs,
	"rtfd.io":         LinkIcon.ReadTheDocs,
	"sphinx-doc.org":  LinkIcon.Sphinx,
}


@export
def checkExternalLinkConfiguration(sphinx: Sphinx, config: Config) -> None:
	"""
	Call-back for Sphinx' ``config-inited`` event, reading the configuration values of the external links' icons.

	``pyTooling_ExternalLink_Icons`` is replaced by the member of :class:`ExternalLinkIcons` it names, and
	``pyTooling_ExternalLink_Hosts`` by a dictionary of the members of :class:`LinkIcon` its values name, keyed by its
	hosts in lower case.

	:param sphinx:                The Sphinx application.
	:param config:                The configuration, after :file:`conf.py` was read.
	:raises SphinxExtensionError: If ``pyTooling_ExternalLink_Icons`` is not a string.
	:raises SphinxExtensionError: If ``pyTooling_ExternalLink_Icons`` names no member of :class:`ExternalLinkIcons`.
	:raises SphinxExtensionError: If ``pyTooling_ExternalLink_NewTab`` is not a boolean.
	:raises SphinxExtensionError: If ``pyTooling_ExternalLink_Hosts`` is not a dictionary.
	:raises SphinxExtensionError: If a host of ``pyTooling_ExternalLink_Hosts`` is not a string.
	:raises SphinxExtensionError: If a host of ``pyTooling_ExternalLink_Hosts`` is empty.
	:raises SphinxExtensionError: If an icon of ``pyTooling_ExternalLink_Hosts`` is not a string.
	:raises SphinxExtensionError: If an icon of ``pyTooling_ExternalLink_Hosts`` names no member of :class:`LinkIcon`.
	"""
	icons = config[f"{CONFIG_PREFIX}_Icons"]
	if icons is not None and not isinstance(icons, str):
		ex = SphinxExtensionError(f"conf.py: {CONFIG_PREFIX}_Icons: Value is not of type 'str'.")
		ex.add_note(f"Got type '{getFullyQualifiedName(icons)}'.")
		raise ex

	try:
		config[f"{CONFIG_PREFIX}_Icons"] = ExternalLinkIcons.Parse(icons)
	except ValueError as cause:
		ex = SphinxExtensionError(f"conf.py: {CONFIG_PREFIX}_Icons: '{icons}' is not a selection of links.")
		ex.add_note(f"Allowed values: {', '.join(ExternalLinkIcons)}.")
		raise ex from cause

	if not isinstance(newTab := config[f"{CONFIG_PREFIX}_NewTab"], bool):
		ex = SphinxExtensionError(f"conf.py: {CONFIG_PREFIX}_NewTab: Value is not of type 'bool'.")
		ex.add_note(f"Got type '{getFullyQualifiedName(newTab)}'.")
		raise ex

	hosts = config[f"{CONFIG_PREFIX}_Hosts"]
	if not isinstance(hosts, Mapping):
		ex = SphinxExtensionError(f"conf.py: {CONFIG_PREFIX}_Hosts: Value is not a dictionary.")
		ex.add_note(f"Got type '{getFullyQualifiedName(hosts)}'.")
		raise ex

	hostIcons: dict[str, LinkIcon] = {}
	for host, icon in hosts.items():
		if not isinstance(host, str):
			ex = SphinxExtensionError(f"conf.py: {CONFIG_PREFIX}_Hosts: Host '{host}' is not of type 'str'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(host)}'.")
			raise ex
		elif host == "":
			raise SphinxExtensionError(f"conf.py: {CONFIG_PREFIX}_Hosts: A host is empty.")

		if icon is not None and not isinstance(icon, str):
			ex = SphinxExtensionError(f"conf.py: {CONFIG_PREFIX}_Hosts: Icon of host '{host}' is not of type 'str'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(icon)}'.")
			raise ex

		try:
			hostIcons[host.lower()] = LinkIcon.Parse(icon)
		except ValueError as cause:
			ex = SphinxExtensionError(f"conf.py: {CONFIG_PREFIX}_Hosts: Icon '{icon}' of host '{host}' is not an icon.")
			ex.add_note(f"Allowed values: {', '.join(LinkIcon)}.")
			raise ex from cause

	config[f"{CONFIG_PREFIX}_Hosts"] = hostIcons


@export
class BaseExternalLinkTransform(SphinxPostTransform):
	"""
	Base-class of the post-transforms marking external links in HTML, so the stylesheet draws an icon behind each.

	A marked link gets the CSS class :attr:`linkClass`, and the CSS class ``pytooling-link-icon-<icon>`` naming the icon
	:meth:`LinkIcon.FromURI` chooses for it. A link holding an image - e.g. a badge - isn't marked, nor is a download
	link: :class:`MarkDownloadLinks` marks those.

	If ``pyTooling_ExternalLink_NewTab`` is ``True``, a marked link opens in a new browser tab: it gets the attributes
	``target="_blank"`` and ``rel="noopener noreferrer"``, which Sphinx' HTML writer copies into the ``<a>`` element. An
	e-mail address doesn't, as a browser would open an empty tab beside the mail program.
	"""

	formats =   ("html", )                               #: Output formats the transform runs for.
	linkClass:  ClassVar[str]                            #: CSS class of a link the transform marks.
	selections: ClassVar[tuple[ExternalLinkIcons, ...]]  #: Values of ``pyTooling_ExternalLink_Icons`` it runs for.

	#: The configuration values of the external links' icons, as ``name: (default, rebuild, types)``. Each is
	#: registered with :data:`CONFIG_PREFIX` as prefix, e.g. ``pyTooling_ExternalLink_Icons``.
	#:
	#: ``Icons`` names a member of :class:`ExternalLinkIcons`; ``None`` is its ``DEFAULT``. ``NewTab`` states whether a
	#: marked link opens in a new browser tab. ``Hosts`` maps a host's domain name to the name of a member of
	#: :class:`LinkIcon`, adding to :data:`HOST_ICONS` or replacing its icon. All are ``"html"``-rebuilt: the marks are
	#: written into the pages, never into the environment.
	configValues: ClassVar[dict[str, tuple[Any, Literal["html"], Any]]] = {
		"Icons":  (None, "html", (str, ExternalLinkIcons)),
		"NewTab": (True, "html", bool),
		"Hosts":  ({},   "html", dict),
	}

	def run(self, **kwargs: Any) -> None:
		"""
		Mark every link :meth:`_Selects` selects, if ``pyTooling_ExternalLink_Icons`` is one of :attr:`selections`.

		:param kwargs: Keyword arguments Sphinx passes to a post-transform; none is used.
		"""
		if self.config[f"{CONFIG_PREFIX}_Icons"] not in self.selections:
			return

		hosts = HOST_ICONS.copy()
		hosts.update(self.config[f"{CONFIG_PREFIX}_Hosts"])
		newTab = self.config[f"{CONFIG_PREFIX}_NewTab"]
		for reference in self.document.findall(nodes.reference):
			if isinstance(reference, download_reference) or "refuri" not in reference or not self._Selects(reference):
				continue
			elif next(reference.findall(nodes.image), None) is not None:
				continue

			icon = LinkIcon.FromURI(reference["refuri"], hosts)
			reference["classes"] += [self.linkClass, f"pytooling-link-icon-{icon}"]
			if newTab and icon is not LinkIcon.Mail:
				reference["target"] = "_blank"
				reference["rel"] =    "noopener noreferrer"

	def _Selects(self, reference: nodes.reference) -> bool:
		"""
		Decide whether a link with a URI is marked.

		:param reference: The link.
		:returns:         ``True`` if the link is marked.
		"""
		raise NotImplementedError(f"Method '{self.__class__.__name__}._Selects' is abstract.")


@export
class MarkExternalLinks(BaseExternalLinkTransform):
	"""
	A post-transform marking the links written with an absolute URI, before Sphinx resolves the references.

	A link of a :mod:`sphinx.ext.extlinks` role, e.g. ``:gh:``, is one of them.
	"""

	default_priority = 5                                                    #: Before Sphinx' ``ReferencesResolver`` (10).
	linkClass =        "pytooling-external-link"                            #: CSS class of a marked link.
	selections =       (ExternalLinkIcons.Explicit, ExternalLinkIcons.All)  #: Values it runs for.

	def _Selects(self, reference: nodes.reference) -> bool:
		"""
		Select a link to an absolute URI of scheme ``http``, ``https``, ``ftp`` or ``mailto``.

		:param reference: The link.
		:returns:         ``True`` if the link isn't internal and its URI has one of these schemes.
		"""
		return not reference.get("internal", False) and urlsplit(reference["refuri"]).scheme in (
			"http", "https", "ftp", "mailto"
		)


@export
class MarkIntersphinxLinks(BaseExternalLinkTransform):
	"""
	A post-transform marking the links Sphinx resolved to another project's documentation.

	Such a link - e.g. one of :mod:`sphinx.ext.intersphinx` - is one :class:`MarkExternalLinks` didn't mark, which its
	resolver declared not ``internal``. Its URI may be relative, for a project whose inventory is a local file; then it
	gets the icon :attr:`LinkIcon.External`.
	"""

	default_priority = 20                            #: After Sphinx' ``ReferencesResolver`` (10).
	linkClass =        "pytooling-intersphinx-link"  #: CSS class of a marked link.
	selections =       (ExternalLinkIcons.All, )     #: Values it runs for.

	def _Selects(self, reference: nodes.reference) -> bool:
		"""
		Select a link declared not ``internal`` by its resolver, which :class:`MarkExternalLinks` didn't mark.

		:param reference: The link.
		:returns:         ``True`` if the link's attribute ``internal`` is ``False`` and the link isn't marked yet.
		"""
		return reference.get("internal", None) is False and MarkExternalLinks.linkClass not in reference["classes"]


@export
class MarkDownloadLinks(SphinxPostTransform):
	"""
	A post-transform marking the links of Sphinx' ``:download:`` role in HTML, so the stylesheet draws a download icon
	behind each.

	A marked link gets the CSS classes ``pytooling-download-link`` and ``pytooling-link-icon-download``, whether the file
	is part of the documentation or another site's. It stays in the browser's tab, as the browser saves the file. A link
	holding an image isn't marked.
	"""

	default_priority = 5                                                    #: Before Sphinx' ``ReferencesResolver`` (10).
	formats =          ("html", )                                           #: Output formats the transform runs for.
	linkClass =        "pytooling-download-link"                            #: CSS class of a marked link.
	selections =       (ExternalLinkIcons.Explicit, ExternalLinkIcons.All)  #: Values it runs for.

	def run(self, **kwargs: Any) -> None:
		"""
		Mark every download link, if ``pyTooling_ExternalLink_Icons`` is one of :attr:`selections`.

		:param kwargs: Keyword arguments Sphinx passes to a post-transform; none is used.
		"""
		if self.config[f"{CONFIG_PREFIX}_Icons"] not in self.selections:
			return

		for reference in self.document.findall(download_reference):
			if next(reference.findall(nodes.image), None) is None:
				reference["classes"] += [self.linkClass, f"pytooling-link-icon-{LinkIcon.Download}"]
