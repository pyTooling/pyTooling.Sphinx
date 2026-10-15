![GitHub Downloads (all assets, specific tag)](https://img.shields.io/github/downloads/OSVVM/OsvvmLibraries/2026.05/total)
# OSVVM 2026.05
OSVVM release 2026.05 adds the following
<ul>
	<li>Script Exit on build done</li>
	<li>Script Bug Fix: two RunTest when running interactively</li>
	<li>Script bug: VhdlLsToml</li>
	<li>Script bug: Simulate and generics</li>
        <li>Updates to remove Assert WARNING/ERROR</li>
	<li>CoveragePkg Refactor</li>
	<li>MemoryGenericPkg Support for 64 bit integers</li>
	<li>AlertLogPkg Use Parent ID</li>
	<li>DynamicVectorGenericPkg</li>
	<li>VHDL-2019 Interface Support</li>
	<li>Ethernet Bug: Fixed RefXxxClk generation</li>
	<li><strong>Breaking Change: &nbsp; AXI4 Memory is now AXI word width</strong></li>
	<li><strong>Breaking Change: &nbsp; SetAxi4Options/GetAxi4Options</strong></li>
</ul>
&nbsp;

<strong>Script Exit on build done</strong>
If `$::osvvm::ExitOnBuildDone` is set and neither `$::osvvm::SimulateInteractive` nor `$::osvvm::Debug` are set, then exit with a code.   The code is 1 if there was an error and 0 otherwise.
	
<strong>Script Bug Fix: two RunTest when running interactively</strong>
If simulate/RunTest is not run from within a build (such as interactively) a second run of RunTest will fail due to not finding the file.   Reported as issue <a href="https://github.com/OSVVM/OSVVM/issues/107">issue 107</a>
 
Issue started due to 2026.01 where if simulate is run interactively it is wrapped in a build so proper directories, results files, and index entry are created.   

Simulate was updated to maintain CurrentWorkingDirectory when it is run interactively.

<strong>Script bug: VhdlLsToml</strong>
Fixed issues with VhdlLsToml file creation.

<strong>Script bug:  Simulate and generics</strong>
If an analyze failed and simulate is called with generics, the generics were remaining set for the next simulate.  

<strong>Updates to remove Assert WARNING/ERROR</strong>
Updated the following:
<ul>
	<li>FifoFillPkg_slv.vhd (from osvvm_common) - changed +i to +1</li>
	<li>WishboneManager.vhd - handling X in to_integer_null_is0</li>
	<li>bmp_pack.vhd (from osvvm_videobus) -  updated write_byte to handle x characters</li>
</ul>

<strong>CoveragePkg Refactor</strong>
CoveragePkg was refactored to separate the singleton implementation from the PT implementation. The PT implementation (in CoveragePtPkg) interacts with the singleton using an ID (which it acquires on demand).  The HTML functional coverage reports now include PT created coverage models.   
	
Going forward, only the singleton implementation (in CoveragePkg) will be updated.  The PT implementation has a method, GetCoverageID, to retrieve the internal ID.   As a result, new singleton functionality can be accessed - with a little work using GetCoverageID.
	
This release adds singleton methods WriteAllBins and GetNumIDs.   The file ID used by FileOpenWriteBin, named OsvvmCoverageWriteBinFile, is now in the declarative part of CoveragePkg (and hence visible).  
	
The updated PT implementation passes all existing OSVVM test cases without modification, so backward compatibility is expected. 
	
<strong>MemoryGenericPkg Support for 64 bit integers</strong>
Updated to support 64 bit implementations (as well as 32 bits) and to automatically select the size based the size your simulator is currently using.   

<strong>AlertLogPkg Use Parent ID</strong>
Most OSVVM data structures call AlertLogPkg.NewID to create an AlertLogID.   A new ReportMode, USE_PARENT_ID was added.   This allows data structures to use the parent ID rather than creating an ID.   This is appropriate for FIFOs where the only message is a FAILURE (and stop).  

<strong>DynamicVectorGenericPkg</strong>
A dynamic vector is a resizable vector. Like a vector it supports random access to elements via indices. The indices are numbered 0 to N-1, where N is the number of elements in the vector. As a data structure, it supports insertion and deletion, but it is optimized for insertion and deletion at the end of the vector (index N-1).
	
Dynamic vectors are implemented in a singleton data structure and can be passed around using their ID. This makes suitable for handling burst transfer information – particularly if the bursts are different sizes. As a singleton, different aspects of the verification environment such as packet generator, verification component (VC) driving the packet, and VC receiving and checking the packet can all reference the packet of data using its ID.
	
Dynamic vectors have similarities to C/Rust/Ada vectors, SystemVerilog dynamic arrays, Python lists, and Java VectorLists.
	
This release introduces dynamic vectors.  Upcoming releases will integrate them into the OSVVM model independent transaction interfaces.

<strong>VHDL-2019 Interface Support</strong>
Currently MIT address bus interface now supported by NVC and Aldec RivieraPRO.   Added VHDL-2019 interfaces to Interrupt Handler.
	
<strong>Ethernet</strong>
Bug fix for generation of RefGtxClk.   The divide by 2 was missing.

<strong>Breaking Change: &nbsp; AXI4 Memory is now AXI word width</strong>
AXI4 Memory is now AXI word width.   This better utilizes the memory (meaning uses less workstation memory) and takes advantages of past updates to the MemoryGenericPkg.  

If accessing the memory directly by using NewID in another VC, please update the call the NewID as follows:
<pre>    vMemID := NewID(
      Name       => MEMORY_NAME, 
      AddrWidth  => AXI_ADDR_WIDTH - AXI_BYTE_ADDR_WIDTH,  -- was AXI_ADDR_WIDTH
      DataWidth  => AXI_DATA_WIDTH,  -- was 8
      ParentID   => ParentID, 
      Search     => NAME
    ) ; </pre>


<strong>Breaking Change: &nbsp; SetAxi4Options/GetAxi4Options</strong>
SetAxi4Options/GetAxi4Options for settings other than an AXI4 bus value (such as BRESP) now interact directly with the internal settings of the VC rather than going through the transaction interface.

As a result, if a test case calls SetAxi4Options/GetAxi4Options at time 0 with a setting other than an AXI4 bus value (such as BRESP) the test case will crash.   Please add a WaitForClock(TRec, 0) before the first SetAxi4Options/GetAxi4Options call.   For more <a href="https://osvvm.org/archives/2944">see the blog post.</a>
<pre>  ManagerProc : process
    variable IntOption  : integer ;
  begin
    WaitForClock(ManagerRec, 0) ;
    SetAxi4Options(ManagerRec, WRITE_RESPONSE_READY_DELAY_CYCLES, 2) ; </pre>


## Release Files
All Git repositories and submodules have been packaged in a single zip file. 

| Asset Name | File Size | SHA256 |
|------------|-----------|--------|
| [OsvvmLibraries - 2026.05 - all-in-one (ZIP)](https://github.com/OSVVM/OsvvmLibraries/releases/download/2026.05/OsvvmLibraries-2026.05.zip) | 44.1MiB | `fc5874b8a5a7178c2f30d9c53253084b4b2d02c3a9580393ab8d5cea058d089b` |
| [OsvvmLibraries - 2026.05 - all-in-one (TAR/GZ)](https://github.com/OSVVM/OsvvmLibraries/releases/download/2026.05/OsvvmLibraries-2026.05.tar.gz) | 42.9MiB | `fc5aa6bad7caccbe99ec4507975badd0ec3a86def08c40d1f2efc6cee2e6c13a` |
| [OsvvmLibraries - 2026.05 - all-in-one (TAR/ZST)](https://github.com/OSVVM/OsvvmLibraries/releases/download/2026.05/OsvvmLibraries-2026.05.tar.zst) | 41.1MiB | `039e0d04eaf06a87346d7ac9ab8d106e39171f560f400e052ffcf608581e95b5` |

# Changes



------
Released on 2026-06-06 05:05:57 UTC by JimLewis
