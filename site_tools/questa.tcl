#-------------------------------------------------------------------------------
#
#     QuestaSim build and run stuff
#
#-------------------------------------------------------------------------------

onerror {quit}
#-------------------------------------------------------------------------------
#
#     Settings
#
quietly source handoff.do

quietly set PROLOGUE_SCRIPT "prologue.tcl"

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
#quietly append vlog_flags " -incr";
quietly append vlog_flags " +incdir+" "$IncDirs";
#quietly append vlog_flags " -sv";
#quietly append vlog_flags " -mfcu";          # (?) is it reaaly need?
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
quietly append vopt_flags " +acc";          # (!) deprecated - see replacements 
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
        return;
    }
    
    if {[launch_cmd ${vopt_cmd} ${vopt_flags}] == 0} {
        return;
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
    run -all
    exit
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
    global CFG_DIR

    set res_name ${CFG_DIR}/sim/${res}

    if {[file exists ${res_name}]} {    
        do ${res_name}
    } else {
        puts "E: result script file does not exist"
    }
}
#-------------------------------------------------------------------------------
#
#     Run service tasks
#
#source ${SCRIPT_DIR}/cfg_header_gen.tcl
#cfg_header_gen ${SCRIPT_DIR} ${CFG_DIR}
#-------------------------------------------------------------------------------
#if {[file exists ${CFG_DIR}/${PROLOGUE_SCRIPT}] == 1} {
#    source ${CFG_DIR}/${PROLOGUE_SCRIPT}
#}
#-------------------------------------------------------------------------------
#if {$argc > 0} {
#    set cmd_arg [lindex $argv 0];
#
#    switch $cmd_arg {
#        "-c" {
#            puts "Compile project"
#            Compile
#        }
#        default {
#            puts "Unrecognized command $cmd_arg"
#        }
#    }
#    #puts " Args $argc are: $cmd_arg"
#}
#-------------------------------------------------------------------------------

