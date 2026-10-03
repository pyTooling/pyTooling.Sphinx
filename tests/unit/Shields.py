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
from pyTooling.Testing        import Testcase


if __name__ == "__main__":  # pragma: no cover
	print("ERROR: you called a testcase declaration file as an executable module.")
	print("Use: 'python -m unittest <testcase module>'")
	exit(1)


class ShieldOptions(Testcase):
	"""What the directive's options state, and what the badge URLs are formatted from."""

	def test_TheGitHubSlugIsSplit(self) -> None:
		"""Every badge URL names the organization and the repository apart; the option states them as one slug."""
		settings = Shields._Settings({"github": "pyTooling/pyVHDLModel"})

		self.assertEqual("pyTooling", settings["GitHubOrganization"])
		self.assertEqual("pyVHDLModel", settings["GitHubRepository"])

	def test_AMalformedSlugIsRejected(self) -> None:
		"""'<organization>/<repository>' has exactly one slash, and silently mis-splitting it makes dead badges."""
		for slug in ("pyTooling", "pyTooling/pyTooling/doc"):
			with self.subTest(slug=slug), self.assertRaises(SphinxExtensionError):
				Shields._Settings({"github": slug})

	def test_AnOptionNotStatedDerivesNothing(self) -> None:
		"""A project states only what its badges use."""
		self.assertEqual({"PyPI": "pyTooling"}, Shields._Settings({"pypi": "pyTooling"}))

	def test_AGitHubLinkIsAFileOnTheDefaultBranch(self) -> None:
		"""'HEAD' is the default branch, whatever the repository calls it."""
		settings = Shields._Settings({"github": "pyTooling/pyTooling", "source-license": "github:LICENSE.md"})

		self.assertEqual("https://GitHub.com/pyTooling/pyTooling/blob/HEAD/LICENSE.md", settings["SourceLicenseURL"])

	def test_AURLIsUsedAsWritten(self) -> None:
		settings = Shields._Settings({"source-license": "MIT https://example.org/license"})

		self.assertEqual("https://example.org/license", settings["SourceLicenseURL"])

	def test_AGitHubLinkNeedsTheRepository(self) -> None:
		"""'github:' names a file, and only ':github:' says in which repository."""
		with self.assertRaises(SphinxExtensionError) as context:
			Shields._Settings({"source-license": "github:LICENSE.md"})

		self.assertIn(":github:", str(context.exception))

	def test_ALinkIsGitHubOrAURL(self) -> None:
		with self.assertRaises(SphinxExtensionError):
			Shields._Settings({"github": "pyTooling/pyTooling", "source-license": "LICENSE.md"})

	def test_TheSourceLicenseIsReportedByGitHub(self) -> None:
		"""Without a license before the link and without a package, the badge asks GitHub."""
		settings = Shields._Settings({"github": "pyTooling/pyTooling", "source-license": "github:LICENSE.md"})

		self.assertEqual("github/license/pyTooling/pyTooling", settings["SourceLicenseImage"])

	def test_APackagesLicenseIsReportedByPyPI(self) -> None:
		"""A package's metadata states its license exactly; GitHub has to recognize a license file's text."""
		settings = Shields._Settings({
			"github": "pyTooling/pyTooling",
			"pypi": "pyTooling",
			"source-license": "github:LICENSE.md"
		})

		self.assertEqual("pypi/l/pyTooling", settings["SourceLicenseImage"])

	def test_AStatedSourceLicenseReplacesGitHubs(self) -> None:
		settings = Shields._Settings({"source-license": "Apache-2.0 https://example.org/license"})

		self.assertEqual("badge/code-Apache--2.0-blue", settings["SourceLicenseImage"])

	def test_TheDocumentationLicenseIsStated(self) -> None:
		"""Nothing reports it, so the option carries it; a static badge's dashes are doubled."""
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

	def test_ADocumentationLicenseWithoutALicenseIsRejected(self) -> None:
		with self.assertRaises(SphinxExtensionError):
			Shields._Settings({"github": "pyTooling/pyTooling", "documentation-license": "github:doc/Doc-License.rst"})

	def test_ALicenseIsAnSPDXExpression(self) -> None:
		"""A misspelt identifier is reported rather than drawn."""
		with self.assertRaises(SphinxExtensionError):
			Shields._Settings({"documentation-license": "CC-BY-5.0 https://example.org/license"})

	def test_ALicenseOutsideTheSPDXListIsAReference(self) -> None:
		settings = Shields._Settings({"documentation-license": "LicenseRef-Company https://example.org/license"})

		self.assertEqual("LicenseRef--Company", settings["DocumentationLicenseBadge"])
		self.assertEqual("", settings["DocumentationLicenseLogo"])

	def test_ALicenseIsWrittenAsParsed(self) -> None:
		"""The badge shows the expression normalized, with its operators in upper case."""
		settings = Shields._Settings({"documentation-license": "MIT or Apache-2.0 https://example.org/license"})

		self.assertEqual("MIT%20OR%20Apache--2.0", settings["DocumentationLicenseBadge"])

	def test_TheCreativeCommonsLogoNeedsOnlyCreativeCommonsLicenses(self) -> None:
		"""Every license of the expression decides, not how its text begins."""
		for expression, logo in (
			("CC-BY-4.0 OR CC-BY-SA-4.0", "&logo=CreativeCommons&logoColor=fff"),
			("CC-BY-4.0 OR MIT", ""),
			("MIT OR CC-BY-4.0", ""),
		):
			with self.subTest(expression=expression):
				settings = Shields._Settings({"documentation-license": f"{expression} https://example.org/license"})

				self.assertEqual(logo, settings["DocumentationLicenseLogo"])

	def test_TheWorkflowBranchIsOptional(self) -> None:
		"""Without it, the badge shows the workflow's latest run on any branch."""
		self.assertEqual("", Shields._Settings({"github-action": "Pipeline.yml"})["WorkflowBranch"])

		settings = Shields._Settings({"github-action": "Pipeline.yml@main"})

		self.assertEqual("Pipeline.yml", settings["Workflow"])
		self.assertEqual("branch=main&", settings["WorkflowBranch"])

	def test_GitHubPagesIsDerived(self) -> None:
		settings = Shields._Settings({"github": "pyTooling/pyTooling", "documentation": "github-pages"})

		self.assertEqual("https://pyTooling.github.io/pyTooling/", settings["DocumentationURL"])
		self.assertEqual("pyTooling.github.io%2FpyTooling", settings["DocumentationLabel"])
		self.assertEqual("https%3A%2F%2FpyTooling.github.io%2FpyTooling%2F", settings["DocumentationQuery"])

	def test_AnotherHostIsAURL(self) -> None:
		"""ReadTheDocs, or anything else."""
		settings = Shields._Settings({"documentation": "https://pytooling.readthedocs.io/en/latest/"})

		self.assertEqual("https://pytooling.readthedocs.io/en/latest/", settings["DocumentationURL"])
		self.assertEqual("&logo=ReadTheDocs&logoColor=fff", settings["DocumentationLogo"])

	def test_TheDocumentationIsGitHubPagesOrAURL(self) -> None:
		with self.assertRaises(SphinxExtensionError):
			Shields._Settings({"documentation": "pytooling.readthedocs.io"})


class ShieldContent(Testcase):
	"""The directive's content: rows of badge identifiers, each needing its options."""

	def test_EveryLineIsARow(self) -> None:
		rows = Shields._ParseRows(["github, src-license", "", "pypi-tag,pypi-status , "])

		self.assertEqual([["github", "src-license"], ["pypi-tag", "pypi-status"]], rows)

	def test_EmptyContentIsRejected(self) -> None:
		with self.assertRaises(SphinxExtensionError):
			Shields._ParseRows(["", "  "])

	def test_AnUnknownBadgeIsRejected(self) -> None:
		with self.assertRaises(SphinxExtensionError) as context:
			Shields._ParseRows(["gha-test"])

		self.assertIn("github-action", str(context.exception))

	def test_ABadgeNamesTheOptionItMisses(self) -> None:
		with self.assertRaises(SphinxExtensionError) as context:
			Shields._CheckOptions([["pypi-tag"]], {"github": "pyTooling/pyTooling"})

		self.assertIn(":pypi:", str(context.exception))

	def test_ABadgeWithItsOptionsPasses(self) -> None:
		Shields._CheckOptions([["pypi-tag", "github"]], {"github": "pyTooling/pyTooling", "pypi": "pyTooling"})


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

	def test_EveryBadgeFormatsFromItsOptions(self) -> None:
		"""A placeholder its options don't fill is a 'KeyError' in the middle of a documentation build."""
		for identifier, shield in SHIELDS.items():
			with self.subTest(shield=identifier):
				options = {option: self._OPTIONS[option] for option in shield.Options}
				if "github" not in options:
					options["github"] = self._OPTIONS["github"]     # 'github:' links name the repository
				settings = Shields._Settings(options)

				self.assertTrue(shield.ImageURL(settings, False).startswith("https://img.shields.io/"))
				shield.TargetURL(settings)

	def test_LaTeXTakesTheRasterizedBadge(self) -> None:
		"""A PDF cannot embed an SVG, which is the whole reason the two variants exist."""
		shield = SHIELDS["pypi-tag"]
		settings = Shields._Settings(self._OPTIONS)

		self.assertEqual(
			shield.ImageURL(settings, False).replace("img.shields.io", "raster.shields.io"),
			shield.ImageURL(settings, True)
		)

	def test_ABadgeWithoutATargetHasNone(self) -> None:
		"""'pypi-status' states a fact and has nowhere to link to."""
		self.assertIsNone(SHIELDS["pypi-status"].TargetURL(Shields._Settings(self._OPTIONS)))

	def test_EveryIdentifierIsWrittenTheWayADocumentWritesIt(self) -> None:
		"""They are typed into a directive's content, so they are lower case and separated by dashes."""
		for identifier in SHIELDS:
			with self.subTest(shield=identifier):
				self.assertEqual(identifier.lower(), identifier)
				self.assertNotIn("_", identifier)

	def test_EveryBadgeHasAlternativeText(self) -> None:
		"""An image without it is unreadable to a screen reader and invisible when the host is down."""
		for identifier, shield in SHIELDS.items():
			with self.subTest(shield=identifier):
				self.assertNotEqual("", shield.AlternativeText)

	def test_EveryOptionABadgeNeedsExists(self) -> None:
		for identifier, shield in SHIELDS.items():
			for option in shield.Options:
				with self.subTest(shield=identifier, option=option):
					self.assertIn(option, Shields.option_spec)

	def test_AShieldWithoutOptionsNeedsNone(self) -> None:
		self.assertEqual((), Shield("text", "path").Options)
		self.assertEqual((), Shield("text", "path", options=None).Options)
		self.assertEqual(("pypi",), Shield("text", "path", options=["pypi"]).Options)

	def test_AShieldChecksItsParameters(self) -> None:
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
