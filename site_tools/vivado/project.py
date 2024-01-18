#-------------------------------------------------------------------------------
#
#    Project Target Support for Xilinx Vivado SCons Tool
#
#    Author: Harry E. Zhurov
#
#-------------------------------------------------------------------------------

import os
import re

from utils import *

#---------------------------------------------------------------------
#
#    Create Vivado project
#
def vivado_project(target, source, env):

    trg          = str(target[0])
    trg_path     = os.path.abspath(trg)
    project_name = env['VIVADO_PROJECT_NAME']
    project_dir  = env['BUILD_SYN_PATH']
    project_path = os.path.join( project_dir, project_name + '.' + env['VIVADO_PROJECT_SUFFIX'] )

    print_action('create Vivado project:     \'' + project_name + '\'')

    #-------------------------------------------------------
    #
    #   Classify sources
    #
    syn     = []
    sim     = []
    ip      = []
    bd      = []
    xdc     = []
    tcl     = []
    incpath = env['INC_PATH']

    for s in source:
        s = str(s)
        sfx = get_suffix(s)
        if sfx not in [env['IP_CORE_SUFFIX'], env['BD_SUFFIX']] :
            path   = search_file(s, env['CFG_PATH'])
            suffix = get_suffix(path)
            if suffix == env['TOOL_SCRIPT_SUFFIX']:
                tcl.append( os.path.abspath(path) )

            elif suffix == env['CONFIG_SUFFIX']:
                try:
                    path_list, used_in = read_sources(path, env['CFG_PATH'], True)
                    
                except SearchFileException as e:
                    print_error('E: ' + e.msg)
                    print_error('    while running "CreateVivadoProject" builder')
                    Exit(-1)

                for item in path_list:
                    src_suffix = get_suffix(item)
                    if src_suffix in [env['V_SUFFIX'], env['SV_SUFFIX'], env['SV_HEADER_SUFFIX'], env['SV_PACKAGE_SUFFIX']]:
                        if used_in == 'syn':
                            syn.append(item)
                        elif used_in == 'sim':
                            sim.append(item)
                        else:
                            print_error('E: unsupported "use_in" value: "' + used_in + '" in ' + path)
                            return -2
                        incpath.append(os.path.dirname(item))

                    if src_suffix in env['CONSTRAINTS_SUFFIX']:
                        xdc.append(item)
            else:
                print_error('E: unsupported file type. Only \'yml\', \'tcl\' file types supported')
                return -1

        elif sfx == env['IP_CORE_SUFFIX']:
            ip.append(os.path.abspath(s))
        else:
            bd.append(os.path.abspath(s))
            

    #-------------------------------------------------------
    #
    #   Delete old project
    #
    if env['CLEAR_PROJECT_DIR']:
        project_items = glob.glob(os.path.join(project_dir, project_name) + '*')
    #   if os.path.exists(env['BD_SIM_PATH']):
    #       project_items.append(env['BD_SIM_PATH'])
            
        for item in project_items:
            Execute( Delete(item) )

    #-------------------------------------------------------
    #
    #   Project create script
    #
    title_text =\
    'Vivado project "' + project_name + '" create script' + os.linesep*2 + \
    'This file is automatically generated. Do not edit the file manually.'

    text  = 'set PROJECT_NAME ' + env['VIVADO_PROJECT_NAME'] + os.linesep
    text += 'set TOP_NAME '     + env['TOP_NAME']            + os.linesep
    text += 'set TOP_TB_NAME '  + env['TESTBENCH_NAME']      + os.linesep
    text += 'set DEVICE '       + env['DEVICE']              + os.linesep*2

    user_params = env['USER_DEFINED_PARAMS']
    for key in user_params:
        text += 'set ' + key + ' ' + user_params[key] + os.linesep

    project_create_args = [env['PROJECT_CREATE_FLAGS'], '${PROJECT_NAME}.' + env['VIVADO_PROJECT_SUFFIX'], '.']
        
    text += os.linesep
    text += '# Project structure'                                                                      + os.linesep
    text += 'create_project ' + ' '.join(project_create_args)                                          + os.linesep*2
    text += 'set_property FLOW "Vivado Synthesis ' + env['VIVADO_VERNUM'] + '" [get_runs synth_1]'     + os.linesep
    text += 'set_property FLOW "Vivado Implementation ' + env['VIVADO_VERNUM'] + '" [get_runs impl_1]' + os.linesep*2

    text += '# Add syn sources' + os.linesep
    text += 'puts "------------------------------------------------------------"' + os.linesep
    text += 'puts "add syn sources"' + os.linesep
    flist = ['    ' + h for h in syn]
    text += 'add_files -scan_for_includes \\' + os.linesep
    text += (' \\' + os.linesep).join(flist)
    text += os.linesep*2

    text += 'puts "------------------------------------------------------------"' + os.linesep
    text += '# Add sim sources' + os.linesep
    text += 'puts "add sim sources"' + os.linesep
    flist = ['    ' + h for h in sim]
    if flist:
        text += 'add_files -scan_for_includes -fileset sim_1 \\' + os.linesep
        text += (' \\' + os.linesep).join(flist)
    text += os.linesep*2
    
    text += 'puts "------------------------------------------------------------"' + os.linesep
    text += '# Add constraints' + os.linesep
    text += 'puts "add constraints"' + os.linesep
    flist = ['    ' + x for x in xdc]
    if flist:
        text += 'add_files -fileset constrs_1 -norecurse \\'  + os.linesep
        text += (' \\' + os.linesep).join(flist)
    text += os.linesep

    text += 'puts "------------------------------------------------------------"' + os.linesep
    text += '# Add IP' + os.linesep
    text += 'puts "add IPs"' + os.linesep
    for i in ip:
        text += 'read_ip ' + i + os.linesep
    text += os.linesep

    text += 'puts "------------------------------------------------------------"' + os.linesep
    text += '# Add BD' + os.linesep
    text += 'puts "add BDs"' + os.linesep
    for i in bd:
        text += 'read_bd ' + i + os.linesep
        bd_name = get_name(i)
        bd_wrapper_path = os.path.join( env['BD_OOC_PATH'], bd_name, bd_name + '.gen', 'sources_1', 'bd', bd_name, 'hdl', bd_name + '_wrapper.v' )
        text += 'add_files -norecurse {' + bd_wrapper_path +'}' + os.linesep*2
        #text += 'make_wrapper -inst_template -files [get_files {' + i + '}]' + os.linesep
        #text += 'add_files -norecurse ${PROJECT_NAME}.gen/sources_1/bd/${bd_name}/hdl/${bd_name}_wrapper.v'
    text += os.linesep
        
        
    text += '# Properties'                                                     + os.linesep
    text += 'puts "------------------------------------------------------------"' + os.linesep
    text += 'puts "set project properties"' + os.linesep
    text += 'set_property part ${DEVICE} [current_project]'                    + os.linesep
    text += 'set_property TARGET_SIMULATOR "Questa" [current_project]'         + os.linesep
    text += 'set_property include_dirs [lsort -unique [lappend incpath ' + \
             ' '.join(incpath) + ']] [get_filesets sources_1]'                 + os.linesep
    text += 'set_property include_dirs [lsort -unique [lappend incpath ' + \
          ' '.join(incpath) + ']] [get_filesets sim_1]'                        + os.linesep
    text += 'update_compile_order -fileset sources_1'                          + os.linesep
    text += 'set_property top ${TOP_NAME} [get_filesets sources_1]'            + os.linesep
    text += 'set_property top ${TOP_TB_NAME} [get_filesets sim_1]'             + os.linesep
    text += 'update_compile_order -fileset sources_1'                          + os.linesep
    text += 'set_property top_lib xil_defaultlib [get_filesets sim_1]'         + os.linesep
    text += 'update_compile_order -fileset sim_1'                              + os.linesep
    text += os.linesep
    #text += 'set_property used_in_simulation false [get_files  -filter {file_type == systemverilog} -of [get_filesets sources_1]]' + os.linesep
    #text += 'set_property used_in_simulation false [get_files  -filter {file_type == verilog} -of [get_filesets sources_1]]'       + os.linesep
    text += os.linesep

    text += '# User-defined scripts' + os.linesep
    text += 'puts "------------------------------------------------------------"' + os.linesep
    text += 'puts "add user hooks"' + os.linesep
    for t in tcl:
        text += 'source ' + t + os.linesep

    text += 'close_project' + os.linesep

    out = generate_title(title_text, '#')
    out += text
    out += generate_footer('#')

    script_name = project_name + '-project-create.' + env['TOOL_SCRIPT_SUFFIX']
    script_path = os.path.join(str(project_dir), script_name)
    with open(script_path, 'w') as ofile:
        ofile.write(out)

    #-------------------------------------------------------
    #
    #   Create project
    #
    logfile  = os.path.join(project_dir, project_name + '-project-create.log')
    cmd = []
    cmd.append(env['SYNCOM'])
    cmd.append(env['SYNFLAGS'])
    cmd.append('-log ' + logfile)
    cmd.append('-source ' + os.path.abspath(script_path))
    cmd = ' '.join(cmd)

    if env['VERBOSE']:
        print(cmd)

    rcode = pexec(cmd, project_dir, exec_env=env['ENV'])
    if rcode:
        print_error('\n' + '*'*60)
        print_error('E: project create ends with error code, see log for details')
        print_error('*'*60 + '\n')
        Execute( Delete(project_path) )
        Execute( Delete(trg_path) )
        return -2
    else:
        Execute( Copy(trg_path, project_path) )
        print_success('\n' + '*'*35)
        print_success('Vivado project successfully created')
        print_success('*'*35 + '\n')

    return None

#---------------------------------------------------------------------
#
#    Synthesize Vivado project
#
def synth_vivado_project(target, source, env):

    project_name = env['VIVADO_PROJECT_NAME']
    project_dir  = env['BUILD_SYN_PATH']
    project_path = os.path.join( project_dir, project_name + '.' + env['VIVADO_PROJECT_SUFFIX'] )

    print_action('synthesize Vivado project: \'' + project_name + '\'')
    #-------------------------------------------------------
    #
    #   Project build script
    #
    title_text =\
    'Vivado project "' + project_name + '" sythesize script' + os.linesep*2 + \
    'This file is automatically generated. Do not edit the file manually.'

    text  = 'open_project ' + project_path                                          + os.linesep

    text += os.linesep
    text += 'puts ""' + os.linesep
    text += 'puts "' + '\033\[1;33m>>>>>>>> Run Synthesis: Compiling and Mapping <<<<<<<<\\033\[0m' + '"' + os.linesep
    text += 'puts ""' + os.linesep

    text += os.linesep
    text += 'reset_run synth_1'                                                 + os.linesep
    text += 'launch_runs synth_1 -jobs 6'                                       + os.linesep
    text += 'wait_on_run synth_1'                                               + os.linesep
    text += 'if {[get_property PROGRESS [get_runs synth_1]] != "100%" } {'      + os.linesep
    text += '    error "\[XILINX_PRJ_BUILD:ERROR\] synth_1 failed"'             + os.linesep
    text += '} else {'                                                          + os.linesep
    text += '    puts "\[XILINX_PRJ_BUILD:INFO\] synth_1 completed. Ok."'       + os.linesep
    text += '}'                                                                 + os.linesep
    
    text += os.linesep
    text += 'close_project'

    out = generate_title(title_text, '#')
    out += text
    out += generate_footer('#')

    script_name = project_name + '-project-synth.' + env['TOOL_SCRIPT_SUFFIX']
    script_path = os.path.join(env['BUILD_SYN_PATH'], script_name)
    with open(script_path, 'w') as ofile:
        ofile.write(out)

    #-------------------------------------------------------
    #
    #   Run synthesize project
    #
    logfile  = os.path.join(env['BUILD_SYN_PATH'], project_name + '-project-synth.log')
    if os.path.exists(logfile):
        Execute( Delete(logfile))

    cmd = []
    cmd.append(env['SYNCOM'])
    cmd.append(env['SYNFLAGS'])
    cmd.append('-log ' + logfile)
    cmd.append('-source ' + os.path.abspath(script_path))
    cmd = ' '.join(cmd)

    if env['VERBOSE']:
        print(cmd)

    rcode = pexec(cmd, project_dir, exec_env=env['ENV'])
    if rcode:
        msg = 'E: project synthesis ends with error code, see log for details'
        print_error('\n' + '*'*len(msg))
        print_error(msg)
        print_error('*'*len(msg) + '\n')
        return -2
    else:
        msg = 'Vivado project successfully synthesized'
        print_success(os.linesep + '*'*len(msg))
        print_success(msg)
        print_success('*'*len(msg) + os.linesep)

    return None

#---------------------------------------------------------------------
#
#    Implement Vivado project
#
def impl_vivado_project(target, source, env):

    project_name = env['VIVADO_PROJECT_NAME']
    project_path = os.path.join(env['BUILD_SYN_PATH'], project_name + '.' + env['VIVADO_PROJECT_SUFFIX'])

    print_action('implement Vivado project:  \'' + project_name + '\'')
    #-------------------------------------------------------
    #
    #   Project build script
    #
    title_text =\
    'Vivado project "' + project_name + '" implement script' + os.linesep*2 + \
    'This file is automatically generated. Do not edit the file manually.'

    text  = 'open_project ' + project_path                                      + os.linesep

    text += os.linesep
    text += 'puts ""' + os.linesep
    text += 'puts "' + '\033\[1;33m>>>>>>>> Run Implementation: Place and Route <<<<<<<<\\033\[0m' + '"' + os.linesep
    text += 'puts ""' + os.linesep

    text += os.linesep
    text += 'reset_run impl_1'                                                  + os.linesep
    text += 'launch_runs impl_1 -jobs 6 -to_step write_bitstream'               + os.linesep
    text += 'wait_on_run impl_1'                                                + os.linesep
    text += 'if {[get_property PROGRESS [get_runs impl_1]] != "100%" } {'       + os.linesep
    text += '    error "\[XILINX_PRJ_BUILD:ERROR\] impl_1 failed"'              + os.linesep
    text += '} else {'                                                          + os.linesep
    text += '    puts "\[XILINX_PRJ_BUILD:INFO\] impl_1 completed. Ok."'        + os.linesep
    text += '}'                                                                 + os.linesep

    text += os.linesep
    text += 'close_project'

    out = generate_title(title_text, '#')
    out += text
    out += generate_footer('#')

    script_name = project_name + '-project-impl.' + env['TOOL_SCRIPT_SUFFIX']
    script_path = os.path.join(env['BUILD_SYN_PATH'], script_name)
    with open(script_path, 'w') as ofile:
        ofile.write(out)

    #-------------------------------------------------------
    #
    #   Run place&route project
    #
    logfile = os.path.join(env['BUILD_SYN_PATH'], project_name + '-project-impl.log')
    if os.path.exists(logfile):
        Execute( Delete(logfile))

    cmd = []
    cmd.append(env['SYNCOM'])
    cmd.append(env['SYNFLAGS'])
    cmd.append('-log ' + logfile)
    cmd.append('-source ' + os.path.abspath(script_path))
    cmd = ' '.join(cmd)

    if env['VERBOSE']:
        print(cmd)
        
    rcode = pexec(cmd, env['BUILD_SYN_PATH'], exec_env=env['ENV'])
    if rcode:
        msg = 'E: project build ends with error code, see log for details'
        print_error('\n' + '*'*len(msg))
        print_error(msg)
        print_error('*'*len(msg) + '\n')
    else:
        msg = 'Vivado project successfully implemented'
        print_success(os.linesep + '*'*len(msg))
        print_success(msg)
        print_success('*'*len(msg) + os.linesep)

    return None

#---------------------------------------------------------------------
#
#    Launch Vivado
#
def open_vivado_project(target, source, env):
    
    project_name = env['VIVADO_PROJECT_NAME']
    project_dir  = env['BUILD_SYN_PATH']
    project_path = os.path.join( project_dir, project_name + '.' + env['VIVADO_PROJECT_SUFFIX'] )
    
        
#   src          = source[0]
#   srce = os.path.splitext(src)[0] + '.' + env['VIVADO_PROJECT_SUFFIX']
#   src_path     = os.path.abspath(str(src))
#   src_dir      = os.path.abspath(str(src.dir))
#   project_name = env['VIVADO_PROJECT_NAME']

    print_action('open Vivado project:       \'' + project_name + '\'')
    
    logfile  = os.path.join(project_dir, project_name + '-project-open.log')
    if os.path.exists(logfile):
        Execute( Delete(logfile))
    
    cmd = []
    cmd.append(env['SYNGUI'])
    cmd.append(env['SYNFLAGS'])
    cmd.append('-log ' + logfile)
    cmd.append(project_path)
    cmd = ' '.join(cmd)
    
    print(cmd)
    env.Execute('cd ' + project_dir + ' && ' + cmd + ' &')
    
    return None

#-------------------------------------------------------------------------------
def create_vivado_project(env, src, ip_cores = [], bd = []):

    trg_name = env['VIVADO_PROJECT_NAME'] + '.prj'
    target   = os.path.join(env['BUILD_SYN_PATH'], trg_name)

    if not SCons.Util.is_List(src):
        src = src.split()

    source   = []
    for s in src:
        if os.path.isabs(s):
            source.append(s)
            continue
        path = search_file(s)
        path = os.path.abspath(path)
        source.append(path)

    env.VivadoProject(target, source + ip_cores + bd)

    return target

#---------------------------------------------------------------------
def launch_synth_vivado_project(env, prj, src):

    if not SCons.Util.is_List(prj):
        prj = prj.split()

    if not SCons.Util.is_List(src):
        src = src.split()

    prj_name = env['VIVADO_PROJECT_NAME']
    top_name = env['TOP_NAME']
    trg = os.path.join(env['BUILD_SYN_PATH'], prj_name + '.runs', 'synth_1', top_name + '.' + env['DCP_SUFFIX'])

    return env.SynthVivadoProject(trg, prj + src)

#---------------------------------------------------------------------
def launch_impl_vivado_project(env, src):

    prj_name = env['VIVADO_PROJECT_NAME']
    top_name = env['TOP_NAME']
    trg = os.path.join(env['BUILD_SYN_PATH'], prj_name + '.runs', 'impl_1', top_name + '.' + env['BITSTREAM_SUFFIX'])

    return env.ImplVivadoProject(trg, src)

#---------------------------------------------------------------------
def launch_open_vivado_project(env, src):

    return env.OpenVivadoProject('open_vivado_project', src)

#---------------------------------------------------------------------
