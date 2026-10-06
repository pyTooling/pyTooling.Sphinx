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
Unit tests for :mod:`pyTooling.Sphinx.Shields`: the directive's options and content, and the badge table.
"""
from pyTooling.Sphinx         import SphinxExtensionError
from pyTooling.Sphinx.Shields import SHIELDS, Shield, Shields
from pyTooling.Testing        import Testcase, testsuite, testcase


if __name__ == "__main__":  # pragma: no cover
	print("ERROR: you called a testcase declaration file as an executable module.")
	print("Use: 'python -m unittest <testcase module>'")
	exit(1)


@testsuite("Shields options")
class ShieldOptions(Testcase):
	"""What the directive's options state, and what the badge URLs are formatted from."""

	@testcase("GitHub slug")
	def GitHub(self) -> None:
		"""
		The ':github:' slug is split into organization and repository.

		Derives the settings from 'pyTooling/pyVHDLModel' and checks both parts.
		"""
		settings = Shields._Settings({"github": "pyTooling/pyVHDLModel"})

		self.assertEqual("pyTooling", settings["GitHubOrganization"])
		self.assertEqual("pyVHDLModel", settings["GitHubRepository"])

	@testcase("GitHub slug with dashes and underscores")
	def GitHub_Escaped(self) -> None:
		"""
		The 'github' badge writes organization and repository as a static badge's label and message.

		Formats the badge of 'edaa-org/my_repo' and checks that '-' and '_' are doubled, as shields.io reads a single
		one as a separator or a space.
		"""
		settings = Shields._Settings({"github": "edaa-org/my_repo"})

		self.assertEqual("edaa-org", settings["GitHubOrganization"])
		self.assertIn("/badge/edaa--org-my__repo-63bf7f?", SHIELDS["github"].ImageURL(settings, False))
		self.assertEqual("https://GitHub.com/edaa-org/my_repo", SHIELDS["github"].TargetURL(settings))

	@testcase("Malformed GitHub slug")
	def GitHub_Malformed(self) -> None:
		"""
		A slug without exactly one slash is rejected.

		Derives the settings from a slug without a slash and from one with two, and checks the SphinxExtensionError.
		"""
		for slug in ("pyTooling", "pyTooling/pyTooling/doc"):
			with self.subTest(slug=slug), self.assertRaises(SphinxExtensionError):
				Shields._Settings({"github": slug})

	@testcase("Unstated options")
	def Unstated(self) -> None:
		"""
		An option that isn't stated derives no setting.

		Derives the settings from ':pypi:' alone and checks only 'PyPI' is set.
		"""
		self.assertEqual({"PyPI": "pyTooling"}, Shields._Settings({"pypi": "pyTooling"}))

	@testcase("GitHub link")
	def Link_GitHub(self) -> None:
		"""
		A 'github:' link is a file on the repository's default branch.

		Derives the source license's URL from 'github:LICENSE.md' and checks it points to 'blob/HEAD'.
		"""
		settings = Shields._Settings({"github": "pyTooling/pyTooling", "source-license": "github:LICENSE.md"})

		self.assertEqual("https://GitHub.com/pyTooling/pyTooling/blob/HEAD/LICENSE.md", settings["SourceLicenseURL"])

	@testcase("URL link")
	def Link_URL(self) -> None:
		"""
		A URL is used as written.

		Derives the source license's URL from a license and a URL and checks the URL.
		"""
		settings = Shields._Settings({"source-license": "MIT https://example.org/license"})

		self.assertEqual("https://example.org/license", settings["SourceLicenseURL"])

	@testcase("GitHub link without repository")
	def Link_GitHubWithoutRepository(self) -> None:
		"""
		A 'github:' link needs the ':github:' option.

		Derives the settings from a 'github:' link without ':github:' and checks the error names the option.
		"""
		with self.assertRaises(SphinxExtensionError) as context:
			Shields._Settings({"source-license": "github:LICENSE.md"})

		self.assertIn(":github:", str(context.exception))

	@testcase("Invalid link")
	def Link_Invalid(self) -> None:
		"""
		A link is 'github:' or a URL.

		Derives the settings from a bare file name and checks the SphinxExtensionError.
		"""
		with self.assertRaises(SphinxExtensionError):
			Shields._Settings({"github": "pyTooling/pyTooling", "source-license": "LICENSE.md"})

	@testcase("Source license from GitHub")
	def SourceLicense_GitHub(self) -> None:
		"""
		Without a stated license and a package, the source license badge asks GitHub.

		Derives the settings from ':github:' and a 'github:' link and checks the GitHub license image.
		"""
		settings = Shields._Settings({"github": "pyTooling/pyTooling", "source-license": "github:LICENSE.md"})

		self.assertEqual("github/license/pyTooling/pyTooling", settings["SourceLicenseImage"])

	@testcase("Source license from PyPI")
	def SourceLicense_PyPI(self) -> None:
		"""
		With a package, the source license badge asks PyPI.

		Derives the settings with ':pypi:' added and checks the PyPI license image.
		"""
		settings = Shields._Settings({
			"github": "pyTooling/pyTooling",
			"pypi": "pyTooling",
			"source-license": "github:LICENSE.md"
		})

		self.assertEqual("pypi/l/pyTooling", settings["SourceLicenseImage"])

	@testcase("Stated source license")
	def SourceLicense_Stated(self) -> None:
		"""
		A stated source license replaces the one GitHub reports.

		Derives the settings from 'Apache-2.0' and a URL and checks the static badge with doubled dashes.
		"""
		settings = Shields._Settings({"source-license": "Apache-2.0 https://example.org/license"})

		self.assertEqual("badge/code-Apache--2.0-blue", settings["SourceLicenseImage"])

	@testcase("Documentation license")
	def DocumentationLicense(self) -> None:
		"""
		The documentation license is stated, with a logo and a link.

		Derives the settings from 'CC-BY-4.0' and a 'github:' link and checks the badge text with doubled dashes, the
		Creative Commons logo and the URL.
		"""
		settings = Shields._Settings({
			"github": "pyTooling/pyTooling",
			"documentation-license": "CC-BY-4.0 github:doc/Doc-License.rst"
		})

		self.assertEqual("CC--BY--4.0", settings["DocumentationLicenseBadge"])
		self.assertEqual("&logo=CreativeCommons&logoColor=fff", settings["DocumentationLicenseLogo"])
		self.assertEqual(
			"https://GitHub.com/pyTooling/pyTooling/blob/HEAD/doc/Doc-License.rst",
			settings["DocumentationLicenseURL"]
		)

	@testcase("Documentation license missing")
	def DocumentationLicense_Missing(self) -> None:
		"""
		A documentation license option without a license is rejected.

		Derives the settings from a link alone and checks the SphinxExtensionError.
		"""
		with self.assertRaises(SphinxExtensionError):
			Shields._Settings({"github": "pyTooling/pyTooling", "documentation-license": "github:doc/Doc-License.rst"})

	@testcase("Invalid license")
	def License_Invalid(self) -> None:
		"""
		A license is an SPDX expression; a misspelt identifier is rejected.

		Derives the settings from 'CC-BY-5.0' and checks the SphinxExtensionError.
		"""
		with self.assertRaises(SphinxExtensionError):
			Shields._Settings({"documentation-license": "CC-BY-5.0 https://example.org/license"})

	@testcase("License reference")
	def License_Reference(self) -> None:
		"""
		A license outside the SPDX list is a 'LicenseRef-' reference.

		Derives the settings from 'LicenseRef-Company' and checks the badge text and that there is no logo.
		"""
		settings = Shields._Settings({"documentation-license": "LicenseRef-Company https://example.org/license"})

		self.assertEqual("LicenseRef--Company", settings["DocumentationLicenseBadge"])
		self.assertEqual("", settings["DocumentationLicenseLogo"])

	@testcase("Normalized license expression")
	def License_Normalized(self) -> None:
		"""
		A license expression is written normalized, its operators in upper case.

		Derives the settings from 'MIT or Apache-2.0' and checks 'MIT OR Apache-2.0', URL-encoded.
		"""
		settings = Shields._Settings({"documentation-license": "MIT or Apache-2.0 https://example.org/license"})

		self.assertEqual("MIT%20OR%20Apache--2.0", settings["DocumentationLicenseBadge"])

	@testcase("Creative Commons logo")
	def License_CreativeCommonsLogo(self) -> None:
		"""
		The Creative Commons logo needs every license of the expression to be a Creative Commons license.

		Derives the logo from three expressions: two Creative Commons licenses get it, a mix in either order doesn't.
		"""
		for expression, logo in (
			("CC-BY-4.0 OR CC-BY-SA-4.0", "&logo=CreativeCommons&logoColor=fff"),
			("CC-BY-4.0 OR MIT", ""),
			("MIT OR CC-BY-4.0", ""),
		):
			with self.subTest(expression=expression):
				settings = Shields._Settings({"documentation-license": f"{expression} https://example.org/license"})

				self.assertEqual(logo, settings["DocumentationLicenseLogo"])

	@testcase("Workflow and branch")
	def Workflow(self) -> None:
		"""
		The workflow's branch is optional.

		Derives the settings from 'Pipeline.yml' without and with '@main', and checks the workflow and the branch query.
		"""
		self.assertEqual("", Shields._Settings({"github-action": "Pipeline.yml"})["WorkflowBranch"])

		settings = Shields._Settings({"github-action": "Pipeline.yml@main"})

		self.assertEqual("Pipeline.yml", settings["Workflow"])
		self.assertEqual("branch=main&", settings["WorkflowBranch"])

	@testcase("Documentation on GitHub Pages")
	def Documentation_GitHubPages(self) -> None:
		"""
		'github-pages' derives the documentation's URL from the repository.

		Derives the settings and checks the URL, the label and the URL-encoded query.
		"""
		settings = Shields._Settings({"github": "pyTooling/pyTooling", "documentation": "github-pages"})

		self.assertEqual("https://pyTooling.github.io/pyTooling/", settings["DocumentationURL"])
		self.assertEqual("pyTooling.github.io%2FpyTooling", settings["DocumentationLabel"])
		self.assertEqual("https%3A%2F%2FpyTooling.github.io%2FpyTooling%2F", settings["DocumentationQuery"])

	@testcase("Documentation at a URL")
	def Documentation_URL(self) -> None:
		"""
		Any other host is given as a URL.

		Derives the settings from a ReadTheDocs URL and checks the URL and the ReadTheDocs logo.
		"""
		settings = Shields._Settings({"documentation": "https://pytooling.readthedocs.io/en/latest/"})

		self.assertEqual("https://pytooling.readthedocs.io/en/latest/", settings["DocumentationURL"])
		self.assertEqual("&logo=ReadTheDocs&logoColor=fff", settings["DocumentationLogo"])

	@testcase("Invalid documentation option")
	def Documentation_Invalid(self) -> None:
		"""
		The documentation is 'github-pages' or a URL.

		Derives the settings from a host name without a scheme and checks the SphinxExtensionError.
		"""
		with self.assertRaises(SphinxExtensionError):
			Shields._Settings({"documentation": "pytooling.readthedocs.io"})


@testsuite("Shields content")
class ShieldContent(Testcase):
	"""The directive's content: rows of badge identifiers, each needing its options."""

	@testcase("Rows of badges")
	def Rows(self) -> None:
		"""
		Every line of the content is a row of badge identifiers.

		Parses three lines with an empty one, spaces and a trailing comma, and checks the two rows.
		"""
		rows = Shields._ParseRows(["github, src-license", "", "pypi-tag,pypi-status , "])

		self.assertEqual([["github", "src-license"], ["pypi-tag", "pypi-status"]], rows)

	@testcase("Empty content")
	def Rows_Empty(self) -> None:
		"""
		Content without a badge is rejected.

		Parses an empty and a blank line and checks the SphinxExtensionError.
		"""
		with self.assertRaises(SphinxExtensionError):
			Shields._ParseRows(["", "  "])

	@testcase("Unknown badge")
	def Rows_Unknown(self) -> None:
		"""
		An unknown badge identifier is rejected, naming the known ones.

		Parses 'gha-test' and checks the error names 'github-action'.
		"""
		with self.assertRaises(SphinxExtensionError) as context:
			Shields._ParseRows(["gha-test"])

		self.assertIn("github-action", str(context.exception))

	@testcase("Missing option")
	def Options_Missing(self) -> None:
		"""
		A badge whose option isn't stated is rejected, naming the option.

		Checks 'pypi-tag' with only ':github:' and checks the error names ':pypi:'.
		"""
		with self.assertRaises(SphinxExtensionError) as context:
			Shields._CheckOptions([["pypi-tag"]], {"github": "pyTooling/pyTooling"})

		self.assertIn(":pypi:", str(context.exception))

	@testcase("Options present")
	def Options(self) -> None:
		"""
		A badge with its options passes.

		Checks 'pypi-tag' and 'github' with ':github:' and ':pypi:' stated.
		"""
		Shields._CheckOptions([["pypi-tag", "github"]], {"github": "pyTooling/pyTooling", "pypi": "pyTooling"})


@testsuite("Badge table")
class ShieldTable(Testcase):
	"""The badge table, and the two URLs each of its entries formats."""

	_OPTIONS = {
		"github":                "pyTooling/pyTooling",
		"pypi":                  "pyTooling",
		"codacy":                "0123456789abcdef",
		"gitter":                "hdl/community",
		"source-license":        "github:LICENSE.md",
		"documentation-license": "CC-BY-4.0 github:doc/Doc-License.rst",
		"github-action":         "Pipeline.yml@main",
		"documentation":         "github-pages",
	}

	@testcase("Badge URLs")
	def URLs(self) -> None:
		"""
		Every badge formats its image and target URL from its options.

		Derives the settings from each badge's options, plus ':github:' for 'github:' links, and formats both URLs.
		"""
		for identifier, shield in SHIELDS.items():
			with self.subTest(shield=identifier):
				options = {option: self._OPTIONS[option] for option in shield.Options}
				if "github" not in options:
					options["github"] = self._OPTIONS["github"]     # 'github:' links name the repository
				settings = Shields._Settings(options)

				self.assertTrue(shield.ImageURL(settings, False).startswith("https://img.shields.io/"))
				shield.TargetURL(settings)

	@testcase("Raster badge for LaTeX")
	def URLs_LaTeX(self) -> None:
		"""
		LaTeX gets the rasterized badge, as a PDF can't embed an SVG.

		Formats the image URL of 'pypi-tag' for HTML and for LaTeX and checks they differ only in the host.
		"""
		shield = SHIELDS["pypi-tag"]
		settings = Shields._Settings(self._OPTIONS)

		self.assertEqual(
			shield.ImageURL(settings, False).replace("img.shields.io", "raster.shields.io"),
			shield.ImageURL(settings, True)
		)

	@testcase("Badge without target")
	def Target_None(self) -> None:
		"""
		A badge stating a fact has no target URL.

		Formats the target of 'pypi-status' and checks None.
		"""
		self.assertIsNone(SHIELDS["pypi-status"].TargetURL(Shields._Settings(self._OPTIONS)))

	@testcase("Badge identifiers")
	def Identifiers(self) -> None:
		"""
		Every badge identifier is written as a document writes it: lower case, with dashes.

		Checks each identifier is lower case and has no underscore.
		"""
		for identifier in SHIELDS:
			with self.subTest(shield=identifier):
				self.assertEqual(identifier.lower(), identifier)
				self.assertNotIn("_", identifier)

	@testcase("Alternative texts")
	def AlternativeText(self) -> None:
		"""
		Every badge has an alternative text.

		Checks the alternative text of each badge isn't empty.
		"""
		for identifier, shield in SHIELDS.items():
			with self.subTest(shield=identifier):
				self.assertNotEqual("", shield.AlternativeText)

	@testcase("Options of badges")
	def Options(self) -> None:
		"""
		Every option a badge needs is an option of the directive.

		Checks each option of each badge is in 'option_spec'.
		"""
		for identifier, shield in SHIELDS.items():
			for option in shield.Options:
				with self.subTest(shield=identifier, option=option):
					self.assertIn(option, Shields.option_spec)

	@testcase("Shield options")
	def Shield_Options(self) -> None:
		"""
		A shield without options needs none.

		Creates shields without options, with None and with a list, and checks the options as a tuple.
		"""
		self.assertEqual((), Shield("text", "path").Options)
		self.assertEqual((), Shield("text", "path", options=None).Options)
		self.assertEqual(("pypi",), Shield("text", "path", options=["pypi"]).Options)

	@testcase("Shield parameter checks")
	def Shield_Parameters(self) -> None:
		"""
		A shield checks its alternative text, path and target.

		Creates shields with None and an integer for each parameter and checks the ValueError or TypeError.
		"""
		with self.subTest("alternativeText"), self.assertRaises(ValueError):
			Shield(None, "path")

		with self.subTest("alternativeText"), self.assertRaises(TypeError):
			Shield(1, "path")

		with self.subTest("path"), self.assertRaises(ValueError):
			Shield("text", None)

		with self.subTest("path"), self.assertRaises(TypeError):
			Shield("text", 1)

		with self.subTest("target"), self.assertRaises(TypeError):
			Shield("text", "path", 1)
