[![Sourcecode on GitHub](https://img.shields.io/badge/pyTooling-Sphinx-63bf7f?longCache=true&style=flat-square&longCache=true&logo=GitHub)](https://GitHub.com/pyTooling/pyTooling.Sphinx)
[![Sourcecode License](https://img.shields.io/pypi/l/pyTooling.Sphinx?longCache=true&style=flat-square&logo=Apache&label=code)](LICENSE.md)
[![Documentation](https://img.shields.io/website?longCache=true&style=flat-square&label=pyTooling.github.io%2FpyTooling.Sphinx&logo=GitHub&logoColor=fff&up_color=blueviolet&up_message=Read%20now%20%E2%9E%9A&url=https%3A%2F%2FpyTooling.github.io%2FpyTooling.Sphinx%2Findex.html)](https://pyTooling.github.io/pyTooling.Sphinx/)
[![Documentation License](https://img.shields.io/badge/doc-CC--BY%204.0-green?longCache=true&style=flat-square&logo=CreativeCommons&logoColor=fff)](doc/Doc-License.rst)  
[![PyPI](https://img.shields.io/pypi/v/pyTooling.Sphinx?longCache=true&style=flat-square&logo=PyPI&logoColor=FBE072)](https://pypi.org/project/pyTooling.Sphinx/)
![PyPI - Status](https://img.shields.io/pypi/status/pyTooling.Sphinx?longCache=true&style=flat-square&logo=PyPI&logoColor=FBE072)
![PyPI - Python Version](https://img.shields.io/pypi/pyversions/pyTooling.Sphinx?longCache=true&style=flat-square&logo=PyPI&logoColor=FBE072)  
[![GitHub Workflow - Build and Test Status](https://img.shields.io/github/actions/workflow/status/pyTooling/pyTooling.Sphinx/Pipeline.yml?branch=main&longCache=true&style=flat-square&label=build%20and%20test&logo=GitHub%20Actions&logoColor=FFFFFF)](https://GitHub.com/pyTooling/pyTooling.Sphinx/actions/workflows/Pipeline.yml)
[![Libraries.io status for latest release](https://img.shields.io/librariesio/release/pypi/pyTooling.Sphinx?longCache=true&style=flat-square&logo=Libraries.io&logoColor=fff)](https://libraries.io/github/pyTooling/pyTooling.Sphinx)
[![Codacy - Quality](https://img.shields.io/codacy/grade/d80355705a634d59835eeb01e8536cce?longCache=true&style=flat-square&logo=Codacy)](https://app.codacy.com/gh/pyTooling/pyTooling.Sphinx/dashboard)
[![Codacy - Coverage](https://img.shields.io/codacy/coverage/d80355705a634d59835eeb01e8536cce?longCache=true&style=flat-square&logo=Codacy)](https://app.codacy.com/gh/pyTooling/pyTooling.Sphinx/dashboard)
[![Codecov - Branch Coverage](https://img.shields.io/codecov/c/github/pyTooling/pyTooling.Sphinx?longCache=true&style=flat-square&logo=Codecov)](https://codecov.io/gh/pyTooling/pyTooling.Sphinx)

# pyTooling.Sphinx

**pyTooling.Sphinx** adds roles and directives to [Sphinx](https://www.sphinx-doc.org/): styled inline text and line
breaks working in HTML and LaTeX, condensed class interfaces, dependency tables generated from requirements files and
the package index, badges, and schema graphs.

Other packages build on it: [pyTooling.GitHub](https://GitHub.com/pyTooling/pyTooling.GitHub) contributes the domain
`gha` for GitHub Actions workflows, enabled as the extension `pyTooling.GitHub.Sphinx`.

> [!IMPORTANT]
> pyTooling.Sphinx requires **Python 3.12 or newer**, because it requires Sphinx 9.1 and Sphinx 9.1 does.

The extension is enabled in `conf.py`:

```python
# doc/conf.py
extensions = [
  ...,
  "pyTooling.Sphinx",
]
```

It links its stylesheet into every HTML page, appends its substitutions to `rst_prolog`, and sets up
`sphinx.ext.graphviz` for the schema graphs.


## Roles and Directives

### Roles

* [Style roles][Roles/Style] - `:red:`, `:underline:`, `:deletion:` and more: CSS classes on inline text, with the
  stylesheet giving them their meaning.
* [Inline Python code][Roles/PythonCode] - `:pycode:`, syntax-highlighted inline code.
* [Line break and horizontal rule][Roles/Breaks] - `|br|` and `|hr|`, in HTML and LaTeX.

### Directives

* [condensed-class][Directives/CondensedClass] - A class' public interface as one code block, parsed from its source.
* [dependency-table][Directives/DependencyTable] - A project's dependencies with versions and licenses, from its
  requirements files and the package index.
* [jsonschema-graph][Directives/JSONSchemaGraph] - Planned: a JSON schema as a Graphviz graph.
* [xmlschema-graph][Directives/XMLSchemaGraph] - An XML schema as a Graphviz graph, drawn from the schema file.
* [shields][Directives/Shields] - A project's badges from shields.io, in rows.

[Roles/Style]: https://pyTooling.github.io/pyTooling.Sphinx/Roles/Style.html
[Roles/PythonCode]: https://pyTooling.github.io/pyTooling.Sphinx/Roles/PythonCode.html
[Roles/Breaks]: https://pyTooling.github.io/pyTooling.Sphinx/Roles/Breaks.html
[Directives/CondensedClass]: https://pyTooling.github.io/pyTooling.Sphinx/Directives/CondensedClass.html
[Directives/DependencyTable]: https://pyTooling.github.io/pyTooling.Sphinx/Directives/DependencyTable.html
[Directives/JSONSchemaGraph]: https://pyTooling.github.io/pyTooling.Sphinx/Directives/JSONSchemaGraph.html
[Directives/XMLSchemaGraph]: https://pyTooling.github.io/pyTooling.Sphinx/Directives/XMLSchemaGraph.html
[Directives/Shields]: https://pyTooling.github.io/pyTooling.Sphinx/Directives/Shields.html


## Contributors

* [Patrick Lehmann](https://GitHub.com/Paebbels) (Maintainer)
* [and more...](https://GitHub.com/pyTooling/pyTooling.Sphinx/graphs/contributors)


## License

This Python package (source code) is licensed under [Apache License 2.0](LICENSE.md).  
The accompanying documentation is licensed under [Creative Commons - Attribution 4.0 (CC-BY 4.0)](doc/Doc-License.rst).


-------------------------

SPDX-License-Identifier: Apache-2.0
