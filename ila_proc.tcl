#-------------------------------------------------------------------------------
#
#    Vivado ILA support routines
#
#    Adopted from example from the topic:
#
#    https://electronix.ru/forum/index.php?app=forums&module=forums&controller=topic&id=135103&do=findComment&comment=1422610
#
#    Many thanks to RobFPGA
#
#-------------------------------------------------------------------------------
proc create_probe {{ila u_ila_0} {mode DATA_AND_TRIGGER} {len 1}} {
    set probe_obj [create_debug_port $ila probe]
    puts "\n--------------"
    puts $probe_obj
    set_property PROBE_TYPE $mode [get_debug_ports $probe_obj]
    set_property PORT_WIDTH $len  [get_debug_ports $probe_obj]
}
#-------------------------------------------------------------------------------
proc net2probe {ila net_obj}  {
    set len [llength $net_obj]
    if {$len>0} {
        set net_obj [lsort -dictionary $net_obj]
        #   mark a nets as debug for simple search and view in the schematic
        set_property mark_debug true $net_obj
        # get last probe port
        set probe_obj [lindex  [get_debug_port $ila/probe*] end]
        set probe_len [llength [string map {0 ""} [get_property is_connected [get_pins [get_debug_ports $probe_obj]]]]]
        # adjust probe width
        set_property PORT_WIDTH [expr $probe_len+$len] [get_debug_ports $probe_obj]
        # and connect new nets to end of probe port
        connect_debug_port $probe_obj $net_obj
        if { [llength $net_obj] == 1} {
            puts "Connecting [format "%3d" $len] net : $net_obj"
        } else {
            puts "Connecting [format "%3d" $len] nets: [lindex $net_obj 0] ... [lindex $net_obj end]"
        }
    }
}
#-------------------------------------------------------------------------------
proc net_clocks {net_name} {
    set cells [all_fanin -flat -only_cells -startpoints_only [get_pins -of [get_nets $net_name]]]

    foreach cell $cells {
        set clock [get_clocks -of [get_cells $cell]]
        puts ">> cell:$cell -> clock:$clock"
    } 
}
#-------------------------------------------------------------------------------

