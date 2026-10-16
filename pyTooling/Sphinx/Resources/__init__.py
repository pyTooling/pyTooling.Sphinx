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
Resources shipped for :mod:`pyTooling.Sphinx`.

Stylesheets:

* :file:`pyTooling.css` - the styles the roles in :mod:`~pyTooling.Sphinx.Roles`, the dependency tables, the
  trees, the Unicode tables, the report tables of domain ``report`` and the icons behind external links need.

Scripts:

* :file:`pyTooling.js` - copies a text into the clipboard, when a reader clicks a copy button of a Unicode table.

LaTeX packages:

* :file:`pyTooling.Sphinx.sty` - the commands LaTeX writes for the style roles ``:strike:`` and ``:underline:``, which
  draw their lines with package ``ulem``.

Data:

* :file:`GitHubEmoji.txt` - GitHub's emoji, their code points and shortcodes, which
  :class:`~pyTooling.Sphinx.GitHubMarkdown.GitHubMarkdown` converts. Generated from github/gemoji (MIT license,
  Copyright (c) 2019 GitHub, Inc.); its header names the version and holds the license text.
"""
