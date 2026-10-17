The 2024.07 release adds:
<ul>
       <li>Breaking changes in Test Status and CreateClock
       <ul>
	   <li>To maintain backward compabitility, set the script variable OsvvmVersionCompatibility to a value 2024.05 or less in OsvvmSettingsLocal.tcl.</li>
	   <li>OSVVM provides OsvvmSettingsLocal_example.tcl that can be used to create your OsvvmSettingsLocal.tcl</li>
	   <li>AlertLogPkg and TbUtilPkg below show individual ways to override these.</li>
	   <li style="color:Red;">Note however, if you used selected paths to these procedures, it is a breaking change as the paths have changed from "OSVVM.TbUtilPkg.CreateClock" to "OSVVM.CreateClockPkg.CreateClock"</li>
 	   <li>Note there are also breaking changes related to TbUtilPkg and named association of Polarity input.  See TbUtilPkg below for details.</li>
       </ul></li>
       <li>AlertLogPkg
       <ul>
	   <li>Test Status now reports as: PASSED, FAILED, NOCHECKS, TIMEOUT.</li>
	   <li>By default status NOCHECKS is FAILED.  Set script variable FailOnNoChecks to false in OsvvmSettingsLocal.tcl to make it PASSED (old behavior)</li>
 	   <li>PathTail now adds generate label to the name it creates.</li>
       </ul></li>
       <li>TbUtilPkg
       <ul>
	   <li>Added predefined barrier signals: OsvvmTestInit, OsvvmResetDone, OsvvmTestDone, TestDone, OsvvmVcInit </li>
	   <li>All procedures that have a Clk input now have a ClkActive input</li>
	   <li>The polarity input on procedures has changed name to differentiate it from ClkActive. Expected impact is minimal.  Named association calls will need to be updated with the new name.  Procedures impacted:  WaitForTransaction, WaitForTransactionOrIrq, WaitForBarrier(2), WaitForClock, WaitForLevel</li>
	   <li>Moved CreateClock and CreateReset and friends from TbUtilPkg to ClockResetPkg</li>
       </ul></li>
       <li>CoveragePkg: Coverage models with Coverage Weight of 0 print last and are hidden in the html by default</li>
       <li>MemoryGenericPkg
       <ul>
	   <li>Throws Errors on AddrWidth > 40 and warnings if AddrWidth  > 36.</li>
           <li>With the Error message, AddrWidth is truncated to 40 and the memory tries to operate.</li>
           <li>Note some simulators die even at AddrWidth = 36.</li>
           <li>Thanks to those reported tool crashes without warnings.</li>
       </ul></li>
       <li>ClockResetPkg
       <ul>
	   <li>Updated CreateClock with Offset, ClkActive, and Enable .  Clock starts with ClkActive value after  the Offset.  At startup it has the initial signal value if set, otherwise, not ClkActive (if Offset > 0 sec).</li>
	   <li>Old version of create clock is available as OldCreateClock.  Its startup behavior is slightly different.</li>
	   <li>Old version of create clock is available as CreateClock when ClockResetVersion is set to 2024.05 or less in OsvvmSettingsLocal.tcl. 
 New versions will not be available though.</li>
	   <li>Added CreateJitterClock whose jitter is controlled by a coverage model</li>
	   <li>Thanks to those who continued asking about an upgrade to CreateClock</li>
       </ul></li>
       <li>ScoreboardPkg
       <ul>
	   <li>Made all generic functions impure</li>
	   <li>Added scoreboards for unsigned, signed, and integer_vector (IntV)</li>
       </ul></li>
       <li>ReportPkg
       <ul>
	   <li>Added TimeOut input to EndOfTestReports</li>
	   <li>Added scoreboard reporting for: unsigned, signed, and integer_vector (IntV)</li>
       </ul></li>
       <li>Scripts
       <ul>
	   <li>Include now has better error handling and restoration of state</li>
	   <li>Updated support for Synopsys VCS, Cadence Xcelium, and added support for Siemens Visualizer</li>
	   <li>Fixed DoWaves for Aldec.  Fixed SetLogEnable. </li>
       </ul></li>
       <li>AXI4
       <ul>
	   <li>Shortened AlertLogID Names to improve reports</li>
	   <li>AxiStreamReceiver - Added OsvvmVcInit to support setting of WaitForGet before TReady is active.</li>
       </ul></li>
       <li>UART: Minor updates to work around tool issues (Synopsys VCS and Cadence Xcelium).</li>
       <li>Regressions run on
       <ul>
	   <li>GHDL 4.1.0.  Latest release run on GitHub Actions</li>
	   <li>NVC 1.13.0</li>
	   <li>Aldec RivieraPRO 2023.10</li>
	   <li>Aldec ActiveHDL 14</li>
	   <li>Aldec VSimSA 14 (related to ActiveHDL)</li>
	   <li>Siemens Questa 2024.02_1.</li>
	   <li>Siemens Visualizer 2024.02_1 runs and individual tests pass, but hangs when running a large number of test cases</li>
	   <li>Synopsys VCS V-2023.12-SP2</li>
	   <li>Cadence Xcelium 2024.03 - passes osvvm library internal tests, but does not pass the OSVVM public tests (for OSVVM VC)</li>
	   <li>Xilinx XSIM 2024.1 - passes osvvm library internal tests, but does not pass the OSVVM public tests (for OSVVM VC)</li>
       </ul></li>
</ul>

To download the release as a zip, see:   <a href="https://osvvm.org/downloads">https://osvvm.org/downloads</a>