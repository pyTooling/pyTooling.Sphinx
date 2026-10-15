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
Unit tests for :mod:`pyTooling.Sphinx.ExternalLink`: which links are marked, which icon each gets, and the configuration
values.
"""
from unittest.mock                 import MagicMock
from zlib                          import compress

from pyTooling.Sphinx              import SphinxExtensionError, setup
from pyTooling.Sphinx.ExternalLink import HOST_ICONS, ExternalLinkIcons, LinkIcon, MarkExternalLinks
from pyTooling.Sphinx.ExternalLink import MarkIntersphinxLinks, checkExternalLinkConfiguration
from pyTooling.Testing             import Testcase, testsuite, testcase

from tests.unit.Extension          import Project


if __name__ == "__main__":  # pragma: no cover
	print("ERROR: you called a testcase declaration file as an executable module.")
	print("Use: 'python -m unittest <testcase module>'")
	exit(1)


@testsuite("External link registration")
class Registration(Testcase):
	"""What the extension registers with Sphinx for the external links."""

	@testcase("Setup with a mock")
	def Setup(self) -> None:
		"""
		The extension's setup() registers both post-transforms, both configuration values and their check.

		Calls setup() with a mocked application and checks the calls.
		"""
		app = MagicMock()
		setup(app)

		transforms = [call.args[0] for call in app.add_post_transform.call_args_list]
		self.assertIn(MarkExternalLinks, transforms)
		self.assertIn(MarkIntersphinxLinks, transforms)
		app.add_config_value.assert_any_call("pyTooling_ExternalLink_Icons", None, "html", (str, ExternalLinkIcons))
		app.add_config_value.assert_any_call("pyTooling_ExternalLink_Hosts", {}, "html", dict)
		self.assertIn(("config-inited", checkExternalLinkConfiguration), [call.args for call in app.connect.call_args_list])

	@testcase("Priorities")
	def Priorities(self) -> None:
		"""
		Links written with their URI are marked before Sphinx resolves the references (priority 10), the others after.

		Checks the post-transforms' priorities and output formats.
		"""
		self.assertLess(MarkExternalLinks.default_priority, 10)
		self.assertGreater(MarkIntersphinxLinks.default_priority, 10)
		self.assertEqual(("html", ), MarkExternalLinks.formats)
		self.assertEqual(("html", ), MarkIntersphinxLinks.formats)


@testsuite("External link selection")
class Selection(Testcase):
	"""Configuration value 'pyTooling_ExternalLink_Icons': which external links get an icon."""

	@testcase("Selections")
	def Selections(self) -> None:
		"""
		No link, the links written with their URI, or all external links; without a value, the links written with their
		URI.

		Parses each value and no value, and checks the members.
		"""
		for value, selection in (
			("none",     ExternalLinkIcons.Disabled),
			("explicit", ExternalLinkIcons.Explicit),
			("all",      ExternalLinkIcons.All),
			(None,       ExternalLinkIcons.Explicit),
		):
			with self.subTest(value=value):
				self.assertIs(selection, ExternalLinkIcons.Parse(value))

	@testcase("Unknown selection")
	def Unknown(self) -> None:
		"""
		Any other value is rejected, and the note lists the values.

		Parses 'some' and checks the ValueError and its note.
		"""
		with self.assertRaises(ValueError) as context:
			ExternalLinkIcons.Parse("some")

		self.assertEqual("'some' is not a valid ExternalLinkIcons.", str(context.exception))
		self.assertEqual(["Allowed values: none, explicit, all."], context.exception.__notes__)


@testsuite("Icon per target")
class IconPerTarget(Testcase):
	"""The icon of a link, chosen by its URI's scheme and host."""

	@testcase("Hosts with an icon")
	def Hosts(self) -> None:
		"""
		A host of HOST_ICONS gets its icon, written in any case.

		Chooses the icon for a URI per host, one written in mixed case, and checks the icons.
		"""
		for uri, icon in (
			("https://github.com/pyTooling/pyTooling", LinkIcon.GitHub),
			("https://GitHub.com/pyTooling/pyTooling", LinkIcon.GitHub),
			("https://gitlab.com/group/project",       LinkIcon.GitLab),
			("https://www.python.org/",                LinkIcon.Python),
			("https://PyPI.org/project/pyTooling",     LinkIcon.Python),
		):
			with self.subTest(uri=uri):
				self.assertIs(icon, LinkIcon.FromURI(uri, HOST_ICONS))

	@testcase("Subdomains")
	def Subdomains(self) -> None:
		"""
		A subdomain of a host gets the host's icon, but a host merely ending in the same characters doesn't.

		Chooses the icon for 'docs.python.org', 'gist.github.com' and 'notgithub.com', and checks the icons.
		"""
		self.assertIs(LinkIcon.Python, LinkIcon.FromURI("https://docs.python.org/3/library/enum.html", HOST_ICONS))
		self.assertIs(LinkIcon.GitHub, LinkIcon.FromURI("https://gist.github.com/Paebbels", HOST_ICONS))
		self.assertIs(LinkIcon.External, LinkIcon.FromURI("https://notgithub.com/", HOST_ICONS))

	@testcase("GitHub Pages")
	def GitHubPages(self) -> None:
		"""
		A site on GitHub Pages is the documentation hosted there, not GitHub: it gets the generic icon.

		Chooses the icon for 'pyTooling.github.io' and checks it.
		"""
		self.assertIs(LinkIcon.External, LinkIcon.FromURI("https://pyTooling.github.io/pyTooling/", HOST_ICONS))

	@testcase("Other targets")
	def OtherTargets(self) -> None:
		"""
		An e-mail address gets the envelope; any other host, a URI without host and a relative URI the generic icon.

		Chooses the icon for 'mailto:', another host, 'file:///', a host with a port and a relative URI, and checks the
		icons.
		"""
		for uri, icon in (
			("mailto:Paebbels@gmail.com",       LinkIcon.Mail),
			("https://www.sphinx-doc.org/",     LinkIcon.External),
			("ftp://ftp.example.org/file",      LinkIcon.External),
			("https://github.com:443/pyTooling", LinkIcon.GitHub),
			("file:///tmp/index.html",          LinkIcon.External),
			("../other/index.html",             LinkIcon.External),
		):
			with self.subTest(uri=uri):
				self.assertIs(icon, LinkIcon.FromURI(uri, HOST_ICONS))

	@testcase("Own hosts")
	def OwnHosts(self) -> None:
		"""
		A mapping of the caller adds hosts and replaces icons; the more specific domain name wins.

		Chooses icons with a mapping adding a GitLab instance and replacing the icon of 'pypi.org', and checks them.
		"""
		hosts = HOST_ICONS.copy()
		hosts.update({"gitlab.example.org": LinkIcon.GitLab, "pypi.org": LinkIcon.External, "example.org": LinkIcon.Mail})

		self.assertIs(LinkIcon.GitLab, LinkIcon.FromURI("https://gitlab.example.org/group/project", hosts))
		self.assertIs(LinkIcon.Mail, LinkIcon.FromURI("https://www.example.org/", hosts))
		self.assertIs(LinkIcon.External, LinkIcon.FromURI("https://pypi.org/project/pyTooling", hosts))


@testsuite("External link configuration")
class Configuration(Testcase):
	"""Reading the configuration values 'pyTooling_ExternalLink_Icons' and 'pyTooling_ExternalLink_Hosts'."""

	@testcase("Values read")
	def Values(self) -> None:
		"""
		The selection becomes a member of ExternalLinkIcons, a host's icon a member of LinkIcon, keyed in lower case.

		Checks a configuration with a selection and two hosts, one without an icon, which gets the generic one.
		"""
		config = {
			"pyTooling_ExternalLink_Icons": "all",
			"pyTooling_ExternalLink_Hosts": {"GitLab.example.org": "gitlab", "pypi.org": None},
		}
		checkExternalLinkConfiguration(None, config)

		self.assertIs(ExternalLinkIcons.All, config["pyTooling_ExternalLink_Icons"])
		self.assertEqual(
			{"gitlab.example.org": LinkIcon.GitLab, "pypi.org": LinkIcon.External}, config["pyTooling_ExternalLink_Hosts"]
		)

	@testcase("Defaults")
	def Defaults(self) -> None:
		"""
		Without values, the links written with their URI get an icon, and no host is added.

		Checks the configuration values' defaults.
		"""
		config = {"pyTooling_ExternalLink_Icons": None, "pyTooling_ExternalLink_Hosts": {}}
		checkExternalLinkConfiguration(None, config)

		self.assertIs(ExternalLinkIcons.Explicit, config["pyTooling_ExternalLink_Icons"])
		self.assertEqual({}, config["pyTooling_ExternalLink_Hosts"])

	@testcase("Errors")
	def Errors(self) -> None:
		"""
		A malformed value is rejected with a message naming the configuration value, and a note.

		Checks the message and the notes per malformed value.
		"""
		for icons, hosts, message, notes in (
			("some",     {},              "conf.py: pyTooling_ExternalLink_Icons: 'some' is not a selection of links.",
			 ["Allowed values: none, explicit, all."]),
			(True,       {},              "conf.py: pyTooling_ExternalLink_Icons: Value is not of type 'str'.",
			 ["Got type 'bool'."]),
			("explicit", ["github.com"],  "conf.py: pyTooling_ExternalLink_Hosts: Value is not a dictionary.",
			 ["Got type 'list'."]),
			("explicit", {1: "github"},   "conf.py: pyTooling_ExternalLink_Hosts: Host '1' is not of type 'str'.",
			 ["Got type 'int'."]),
			("explicit", {"": "github"},  "conf.py: pyTooling_ExternalLink_Hosts: A host is empty.",
			 []),
			("explicit", {"a.org": 1},    "conf.py: pyTooling_ExternalLink_Hosts: Icon of host 'a.org' is not of type 'str'.",
			 ["Got type 'int'."]),
			("explicit", {"a.org": "hg"}, "conf.py: pyTooling_ExternalLink_Hosts: Icon 'hg' of host 'a.org' is not an icon.",
			 ["Allowed values: external, mail, github, gitlab, python."]),
		):
			config = {"pyTooling_ExternalLink_Icons": icons, "pyTooling_ExternalLink_Hosts": hosts}
			with self.subTest(message=message):
				with self.assertRaises(SphinxExtensionError) as context:
					checkExternalLinkConfiguration(None, config)

				self.assertEqual(message, str(context.exception))
				self.assertEqual(notes, getattr(context.exception, "__notes__", []))


@testsuite("External links in a document")
class Rendering(Project):
	"""The CSS classes of the external links in a built page, per configuration."""

	_document = (
		"Index\n#####\n\n"
		"* named `Sphinx <https://www.sphinx-doc.org/>`_\n"
		"* anonymous `pyTooling <https://PyPI.org/project/pyTooling>`__\n"
		"* bare https://gitlab.com/group/project\n"
		"* extlink :gh:`pyTooling/pyTooling`\n"
		"* mail Paebbels@gmail.com\n"
		"* relative `license <license.html>`__\n"
		"* internal :ref:`genindex`\n"
		"* intersphinx :py:class:`Other.Thing` and :py:class:`Local.Thing`\n"
		"\n"
		".. image:: logo.png\n"
		"   :target: https://github.com/pyTooling\n"
	)

	def _buildLinks(self, builder: str = "html", **config: object) -> None:
		"""
		Write two inventories and the logo, and build the document with extlinks and intersphinx.

		Inventory 'other' is published on 'docs.python.org', inventory 'local' beside the project, with a relative URI.

		:param builder: Optional, name of the builder. Default: ``"html"``.
		:param config:  Configuration values overriding the defaults.
		"""
		inventories = {}
		for name in ("Other", "Local"):
			inventory = self._path / f"{name}.inv"
			inventory.write_bytes(
				f"# Sphinx inventory version 2\n# Project: {name}\n# Version: 1.0\n"
				f"# The remainder of this file is compressed using zlib.\n".encode("utf-8") +
				compress(f"{name}.Thing py:class 1 api.html#$ -\n".encode("utf-8"))
			)
			inventories[name] = str(inventory)

		(self._path / "src" / "logo.png").write_bytes(b"")
		self._build(
			self._document,
			builder,
			extensions=["pyTooling.Sphinx", "sphinx.ext.extlinks", "sphinx.ext.intersphinx"],
			extlinks={"gh": ("https://GitHub.com/%s", "%s")},
			intersphinx_mapping={
				"other": ("https://docs.python.org/3/", inventories["Other"]),
				"local": ("../local/",                  inventories["Local"]),
			},
			**config
		)

	def _assertExplicitLinks(self, html: str) -> None:
		"""
		Check the links written with their URI are marked, each with its icon, and the others aren't.

		:param html: The page's HTML.
		"""
		for link in (
			'<a class="pytooling-external-link pytooling-link-icon-external reference external" '
			'href="https://www.sphinx-doc.org/">',
			'<a class="pytooling-external-link pytooling-link-icon-python reference external" '
			'href="https://PyPI.org/project/pyTooling">',
			'<a class="pytooling-external-link pytooling-link-icon-gitlab reference external" '
			'href="https://gitlab.com/group/project">',
			'<a class="extlink-gh pytooling-external-link pytooling-link-icon-github reference external" '
			'href="https://GitHub.com/pyTooling/pyTooling">',
			'<a class="pytooling-external-link pytooling-link-icon-mail reference external" href="mailto:',
			'<a class="reference external" href="license.html">',
			'<a class="reference internal" href="genindex.html">',
			'<a class="reference external image-reference" href="https://github.com/pyTooling">',
		):
			with self.subTest(link=link):
				self.assertIn(link, html)

	@testcase("Explicit links")
	def Explicit(self) -> None:
		"""
		By default, the links written with an absolute URI are marked, also those of an extlink role and e-mail addresses.

		A relative or internal link, a link holding an image and an intersphinx link aren't. Builds the document and
		checks every link's classes.
		"""
		self._buildLinks()

		self.assertEqual([], self._warningLines())
		html = self._html("index")
		self._assertExplicitLinks(html)
		self.assertIn('<a class="reference external" href="https://docs.python.org/3/api.html#Other.Thing"', html)
		self.assertIn('<a class="reference external" href="../local/api.html#Local.Thing"', html)
		self.assertNotIn("pytooling-intersphinx-link", html)

	@testcase("All links")
	def All(self) -> None:
		"""
		With 'all', the intersphinx links are marked too; one with a relative URI gets the generic icon.

		Builds the document and checks every link's classes.
		"""
		self._buildLinks(pyTooling_ExternalLink_Icons="all")

		self.assertEqual([], self._warningLines())
		html = self._html("index")
		self._assertExplicitLinks(html)
		self.assertIn(
			'<a class="pytooling-intersphinx-link pytooling-link-icon-python reference external" '
			'href="https://docs.python.org/3/api.html#Other.Thing"', html
		)
		self.assertIn(
			'<a class="pytooling-intersphinx-link pytooling-link-icon-external reference external" '
			'href="../local/api.html#Local.Thing"', html
		)

	@testcase("No links")
	def Disabled(self) -> None:
		"""
		With 'none', no link is marked.

		Builds the document and checks no link icon's class is on the page.
		"""
		self._buildLinks(pyTooling_ExternalLink_Icons="none")

		self.assertEqual([], self._warningLines())
		self.assertNotIn("pytooling-link-icon", self._html("index"))

	@testcase("Own hosts")
	def OwnHosts(self) -> None:
		"""
		'pyTooling_ExternalLink_Hosts' adds a host and replaces an icon.

		Builds the document with GitLab's icon for 'sphinx-doc.org' and the generic one for 'pypi.org', and checks both
		links.
		"""
		self._buildLinks(pyTooling_ExternalLink_Hosts={"Sphinx-Doc.org": "gitlab", "pypi.org": "external"})

		self.assertEqual([], self._warningLines())
		html = self._html("index")
		self.assertIn(
			'<a class="pytooling-external-link pytooling-link-icon-gitlab reference external" '
			'href="https://www.sphinx-doc.org/">', html
		)
		self.assertIn(
			'<a class="pytooling-external-link pytooling-link-icon-external reference external" '
			'href="https://PyPI.org/project/pyTooling">', html
		)

	@testcase("Other formats")
	def OtherFormats(self) -> None:
		"""
		Only HTML marks the links: a format without the stylesheet keeps them as they are.

		Builds the document as pseudo-XML, which shows every node's classes, and checks no link is marked.
		"""
		self._buildLinks("pseudoxml", pyTooling_ExternalLink_Icons="all")

		self.assertEqual([], self._warningLines())
		pseudoXML = (self._path / "build" / "pseudoxml" / "index.pseudoxml").read_text(encoding="utf-8")
		self.assertIn('refuri="https://GitHub.com/pyTooling/pyTooling"', pseudoXML)
		self.assertNotIn("pytooling", pseudoXML)

	@testcase("Malformed configuration value")
	def Malformed(self) -> None:
		"""
		A malformed configuration value stops the build.

		Builds the document with an unknown selection and checks the error.
		"""
		with self.assertRaises(SphinxExtensionError) as context:
			self._buildLinks(pyTooling_ExternalLink_Icons="some")

		self.assertEqual(
			"conf.py: pyTooling_ExternalLink_Icons: 'some' is not a selection of links.", str(context.exception)
		)
