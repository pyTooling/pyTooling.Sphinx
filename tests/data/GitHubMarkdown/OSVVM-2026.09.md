# OSVVM 2026.09

All Git repositories and submodules have been packaged in a single zip file. This file contains the following
OSVVM components.

## Release Files

| Asset Name | File Size | SHA256 |
|------------|-----------|--------|
| [OsvvmLibraries - 2026.09 - all-in-one (ZIP)](https://github.com/OSVVM/OsvvmLibraries/releases/download/2026.09/OsvvmLibraries-2026.09.zip) | 43.4MiB | `236214bf06b8f755a19203b49f1f4df4660c36460a4d771449379c5a3a7459a1` |
| [OsvvmLibraries - 2026.09 - all-in-one (TAR/GZ)](https://github.com/OSVVM/OsvvmLibraries/releases/download/2026.09/OsvvmLibraries-2026.09.tar.gz) | 42.2MiB | `c13b074cd3d4912ecaa1430d3b0f347981f4a1c43c3d6fd65fd9f2c594e2a07a` |
| [OsvvmLibraries - 2026.09 - all-in-one (TAR/ZST)](https://github.com/OSVVM/OsvvmLibraries/releases/download/2026.09/OsvvmLibraries-2026.09.tar.zst) | 40.6MiB | `7ab4d89e50e81c7d5a56ec9ad4ca89141c5f8360a3e70701a1bb750af4dbe83b` |

# Changes
Gilda Radner taught us, "...it is always something ...". &nbsp; OSVVM release 2026.09 addresses some of the small "always something" things so I can move on and worry about the bigger things a little later.
<ul>
	<li>Linking of HTML transcripts to the HTML log file -  for regressions when not using in mirroring
        <ul>
	    <li>Fixed constant OsvvmSettingsPkg_default In 2026.08 constant should be named %%x and not %%+</li>
        </ul></li>
        <li>For Alert/Log with Wrapped lines,
	<ul>
	    <li>If start with LF, indent, but only wrap if  ALERT_LOG_WRAP</li>
	    <li>If ALERT_LOG_WRAP, do not wrap unless line is longer than threshold</li>
        </ul></li>
        <li>In HTML files added handling of characters '<' and '>' so they are not seen as an HTML tag
	<ul>
	    <li>Line continuation indication changed from %%> to %%:</li>
        </ul></li>
        <li>Calling TestName explicitly in the scripts suspends renaming of test cases with generics
	<ul>
	    <li>Facilitates formulating names your way</li>
        </ul></li>
        <li>When simulate finishes, in tcl, $::osvvm::TestCaseStatus holds simulate completion status (PASSED, FAILED, ...)</li>
        <li>Fixed file name case sensitivity  issue in CoSim *.pro file (only impacts usage on Linux/Unix)</li>
</ul>



------
Released on 2026-10-04 15:39:47 UTC by JimLewis
