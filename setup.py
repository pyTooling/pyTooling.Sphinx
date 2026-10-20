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
Package installer for 'More Sphinx roles, directives and domains'.
"""
from setuptools          import setup

from pathlib             import Path
from pyTooling.Packaging import DEFAULT_CLASSIFIERS, DescribePythonPackageHostedOnGitHub
from pyTooling.Warning   import WarningCollector

gitHubNamespace =        "pyTooling"
packageName =            "pyTooling.Sphinx"
packageDirectory =       packageName.replace(".", "/")
packageInformationFile = Path(f"{packageDirectory}/__init__.py")

with WarningCollector() as warnings:
	setup(
		**DescribePythonPackageHostedOnGitHub(
			packageName=packageName,
			description="More Sphinx roles, directives and domains.",
			gitHubNamespace=gitHubNamespace,
			unittestRequirementsFile=Path("tests/requirements.txt"),
			sourceFileWithVersion=packageInformationFile,
			classifiers=list(DEFAULT_CLASSIFIERS) + [
				"Framework :: Sphinx :: Domain",
				"Framework :: Sphinx :: Extension",
			],
			developmentStatus="alpha",
			pythonVersions=("3.12", "3.13", "3.14", "3.15"),
			additionalRequirements={
				"reports": [
					"pyEDAA.Reports ~= 0.20.0rc1",
				],
				"markdown": [
					"markdown-it-py ~= 4.2",
					"mdit-py-plugins ~= 0.6",
				],
			},
			dataFiles={
				packageName:                ["py.typed"],
				f"{packageName}.Resources": ["*.css", "*.js", "*.sty", "*.txt"]
			},
			debug=True
		)
	)

for warning in warnings:
	print(f"[setup.py] WARNING: {warning}")
