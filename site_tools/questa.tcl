#-------------------------------------------------------------------------------
#
#     QuestaSim build and run stuff
#
#-------------------------------------------------------------------------------

onerror {quit}
#-------------------------------------------------------------------------------
#
#     Info
#
puts "**************************************************************************"
puts "*"
puts "*    Info"
puts "*"
puts "Available commands:\n"
puts "    * 'c'       : compile work library."
puts "    * 's'       : launch simulation run."
puts "    * 'r'       : restart simulation run."
puts "    * 'rr'      : restart simulation run with reset transcript file."
puts "    * 'show_res': show results of existing simulation run (see below)."
puts "    * 'swc'     : save waveform configuration to file (see below)."
puts "\n"
puts "Memo:\n"
puts "    'vsim -view <log-name>.wlf' can be used to view resutls of completed run."
puts "         Use 'show_res <cfg-name> to view waveform, memory view, etc of "
puts "         specified simulation run log."
puts "         Use 'swc <wave-cfg-name>' to save waveform config in the file "
puts "         <wave-cfg-name>.do"
puts "**************************************************************************"

#-------------------------------------------------------------------------------
#
#     Settings
#
quietly source handoff.do

quietly set DesignName $TB_NAME
quietly set WaveFileName    ${DesignName}
quietly append WaveFileName "_wave.do"

quietly set WorkLib $WLIB_NAME

#---------------------------------------------------------------------
#
#     Include directories list
#
set SRC_DIRS {}

foreach f $SRC {
    lappend SRC_DIRS [file dirname $f];
}

quietly set INC_DIRS [concat ${SRC_DIRS} ${CFG_DIR} ${INC_PATH}]
quietly set INC_DIRS [lsort -unique $INC_DIRS];
quietly set IncDirs [join ${INC_DIRS} "+"];
#---------------------------------------------------------------------
#
#     Toolchain
#
set vlog_cmd {}
set vcom_cmd {}
set vopt_cmd {}
set vsim_cmd {}

quietly append vlog_cmd "vlog";
quietly append vcom_cmd "vcom";
quietly append vopt_cmd "vopt";
quietly append vsim_cmd "vsim";

#---------------------------------------------------------------------
#
#     Tool flags
#
#-----------------------------------------------------------
#
#     VLOG
#
set vlog_flags {}
if {[info exists WorkLib]} {
        quietly append vlog_flags " -work $WorkLib";
}
quietly append vlog_flags " +incdir+" "$IncDirs";
quietly append vlog_flags " " ${VLOG_FLAGS}

#-----------------------------------------------------------
#
#     VOPT
#
quietly set OptimizedDesignName "opt_$DesignName"
quietly set vopt_flags {}
if {[info exists WorkLib]} {
    quietly append vopt_flags " -work $WorkLib";
}
quietly append vopt_flags " " ${VOPT_FLAGS}
quietly append vopt_flags " " $DesignName
quietly append vopt_flags " -o " $OptimizedDesignName;


#-----------------------------------------------------------
#
#     VSIM
#
set vsim_flags {}
if {[info exists WorkLib]} {
        quietly append vsim_flags " -lib $WorkLib";
}
if {[info exists TimeResolution]} {
        quietly append vsim_flags " -t $TimeResolution";
}
quietly append vsim_flags " " ${VSIM_FLAGS}
quietly append vsim_flags " -wlf func.wlf";
quietly append vsim_flags " -quiet";
quietly append vsim_flags " " $OptimizedDesignName;

#-------------------------------------------------------------------------------
#
#     Commands
#
proc launch_cmd { Cmd Args } {
    set io [open "| $Cmd $Args" r]
    puts [read $io];
    if {[catch {close $io} err]} {
        puts "[file tail $Cmd] report error: $err"
        return 0;
    }
    return 1;
}
#-------------------------------------------------------------------------------
proc compile {} {

    global vlog_cmd vlog_flags;
    global vcom_cmd vcom_flags;
    global vopt_cmd vopt_flags;

    global SRC

    if {[launch_cmd ${vlog_cmd} [concat ${vlog_flags} ${SRC}]] == 0} {
        exit -code -1;
    }

    if {[launch_cmd ${vopt_cmd} ${vopt_flags}] == 0} {
        exit -code -1;
    }
}
#-------------------------------------------------------------------------------
proc sim_begin { } {
    global vsim_cmd vsim_flags;

    quit -sim;

    global StdArithNoWarnings;
    global NumericStdNoWarnings;

    set cmd [concat ${vsim_cmd} ${vsim_flags}];
    eval ${cmd}
    radix -hex
    log -r /*

    puts "StdArithNoWarnings   = $StdArithNoWarnings"
    puts "NumericStdNoWarnings = $NumericStdNoWarnings"
}

#-------------------------------------------------------------------------------
proc c { } {
    compile;
}
#-------------------------------------------------------------------------------
proc s { { res empty} { wave_ena 1 } } {

    global CFG_DIR

    set res_name ${CFG_DIR}/sim/${res}

    sim_begin;

    if {[file exists ${res_name}]} {
        do ${res_name}
    }

    run -all

    if { $wave_ena != 0 } {
        view wave
    }
    view transcript
}
#-------------------------------------------------------------------------------
proc run_sim {} {

    sim_begin;
    
    set errcode sim_error_status_code
    
    if { [file exists $errcode] } {
        file delete $errcode
    } 
        
    onfinish final
    run -all

    if { [file exists $errcode] } {
        set fd [open $errcode r]
        set exit_code [read $fd]
        close $fd
    } else {
        set exit_code 0
    }
    puts "\n******************************************************************************"

    exit -code $exit_code
}
#-------------------------------------------------------------------------------
proc r { { wave_ena 1 } } {
    restart -force
    run -all

    if { $wave_ena != 0 } {
        view wave
    }
    view transcript
}
#-------------------------------------------------------------------------------
proc rr {} {
    transcript file "";
    transcript file transcript;
    r
}
#-------------------------------------------------------------------------------
proc show_res { res } {
}
#-------------------------------------------------------------------------------
proc sres { res } {
    global CFG_DIR

    set res_name ${CFG_DIR}/sim/${res}

    if {[file exists ${res_name}]} {
        do ${res_name}
    } else {
        echo "E: result script file does not exist"
    }
}
#-------------------------------------------------------------------------------
proc swc { wave_cfg } {
    global CFG_DIR

    set wave_cfg_name "${CFG_DIR}/sim/${wave_cfg}.do"
    
    write format wave "${wave_cfg_name}"
}
#-------------------------------------------------------------------------------