#-------------------------------------------------------------------------------
#
#    QuestaSim Configuration Tool
#
#    Author: Harry E. Zhurov
#
#-------------------------------------------------------------------------------

import os
import re

import SCons.Builder
import SCons.Scanner

from utils import *

#-------------------------------------------------------------------------------
#
#    Action functions
#
#-------------------------------------------------------------------------------
def simlib(target, source, env):

    trg      = target[0]
    trg_path = str(trg)
    trg_dir  = str(trg.dir)

    do_files  = glob.glob( os.path.join(env['SIM_SCRIPT_PATH'], '**/compile.do'), recursive=True)

    print_action('compile sim libraries at:  \'' + trg_path + '\'')

    if not os.path.exists(trg_path):
        print_info('create root simlib directory')
        Execute( Mkdir(trg_path) )

    # process sources and compile target lib
    lib_pattern  = 'vmap\s+(\w+)\s+[\w\/]+'
    vlog_pattern = 'vlog((?:.+\n)+)'
    vcom_pattern = 'vcom((?:.+\n)+)'

    map_vendor_libs = True

    for f in do_files:
        print('================================')
        with open(str(f)) as file:
            contents = file.read()

            lib_list = re.findall(lib_pattern, contents)

            for lib in lib_list:
                # create target lib if need
                lib_path = os.path.join(trg_path, lib)
                if not os.path.exists(lib_path):
                    rcode = create_simlib(env, lib_path, map_vendor_libs)
                    map_vendor_libs = False
                    if rcode: return rcode

            cmd_list  = [env['VLOGCOM'] + env['VLOG_FLAGS'] + item for item in re.findall(vlog_pattern, contents)]
            cmd_list += [env['VCOMCOM'] + env['VCOM_FLAGS'] + item for item in re.findall(vcom_pattern, contents)]

            for item in cmd_list:
                cmd = item.replace('\\\n', ' ')
                cmd = cmd.replace('"', '')
                rcode = pexec(cmd, trg_path)
                if rcode:
                    Execute( Delete(trg_path) )
                    return rcode
                print('-'*80)

    return None
    
#-------------------------------------------------------------------------------
def work_lib(target, source, env):
    
    trg      = target[0]
    trg_path = str(trg)
    trg_dir  = str(trg.dir)
    
    simlibs = simlib_list(env['SIMLIB_PATH'])
    #-----------------------------------------------------------------
    #
    #   Create work library
    #
    if not os.path.exists(trg_path):
        # create project simulation library
        rcode = create_simlib(env, trg_path, True)              
        if rcode: return rcode
              
        # map simulation libraries
        for i in simlibs:
          rcode = vmap_simlib(env, simlibs[i], trg_dir)
          if rcode: return rcode
        
        # map work library      
        rcode = vmap_simlib(env, os.path.abspath(trg_path), trg_dir)
        if rcode: return rcode
    
    #-----------------------------------------------------------------
    #
    #   Create handoff file
    #
    if 'vivado' in env['TOOLS']:
        glbl_path = File(os.path.join(env['XILINX_VIVADO'], 'data/verilog/src/glbl.v'))
        source.append(glbl_path)
     
    # simlib stuff
    lib_opt = ''
    if simlibs.keys():
        lib_opt  += ' -L ' +' -L '.join(simlibs.keys())
        
    hdl_wrappers  = glob.glob(os.path.join(env['BUILD_SYN_PATH'], env['VIVADO_PROJECT_NAME'] + '.gen', 'sources_1/bd/*/hdl/*_wrapper*'), recursive=True)
    hdl_wrappers += glob.glob(os.path.join(env['BUILD_SYN_PATH'], env['VIVADO_PROJECT_NAME'] + '.srcs', 'sources_1/**/hdl/*_wrapper*'), recursive=True)   # '<name>_sim_wrapper.v' support 
                                                                                                                                                          # for Versal NoC Simulation
    # source files and other options
    src_list = ' '.join(['{' + os.path.join(f.abspath) + '}' for f in source] + hdl_wrappers)
    incpath  = ' '.join(env['SIM_INC_PATH'])
    
    out = ''

    out += 'set CFG_DIR {'    + env['CFG_PATH'] + '}'             + os.linesep
    out += 'set TB_NAME {'    + env['TESTBENCH_NAME'] + '}'       + os.linesep
    out += 'set WLIB_NAME {'  + env['SIM_WORKLIB_NAME'] + '}'     + os.linesep
    out += 'set SRC [list '   + src_list + ']'                    + os.linesep
    out += 'set INC_PATH {'   + incpath  + '}'                    + os.linesep
    out += 'set VLOG_FLAGS {' + env['VLOG_FLAGS'] + '}'           + os.linesep
    out += 'set VOPT_FLAGS {' + env['VOPT_FLAGS'] + lib_opt + '}' + os.linesep
    out += 'set VSIM_FLAGS {' + env['VSIM_FLAGS'] + '}'           + os.linesep
    
    handoff_path = os.path.join( str(trg.dir), 'handoff.do')
    with open(handoff_path, 'w') as ofile:
        ofile.write(out)
        
    #-----------------------------------------------------------------
    #
    #   Compile work library
    #
    cmd  = env['QUESTASIM'] + ' -c'
    cmd += ' -do ' + env['SIM_CMD_SCRIPT']
    cmd += ' -do c'      
    cmd += ' -do exit'

    print(cmd)
    msg = colorize('Compile project work library', 'yellow')
    print(colorize('-'*80, 'yellow'))
    print(' '*20, msg, os.linesep)
    rcode = pexec(cmd, trg_dir, env['VOPT_FILTER_RULES'])
    print(colorize('-'*80, 'yellow'))
    if rcode:
        return rcode
                
    return None

#-------------------------------------------------------------------------------
def questa_gui(target, source, env):
    cmd = env['QUESTASIM'] + ' -do ' + env['SIM_CMD_SCRIPT']
    print(cmd)
    env.Execute('cd ' + env['BUILD_SIM_PATH'] + ' && ' + cmd)
    
    return None
    
#-------------------------------------------------------------------------------
def questa_run(target, source, env):
    cmd = env['QUESTASIM'] + ' -batch ' + ' -do ' + env['SIM_CMD_SCRIPT'] + ' -do run_sim'
    print(cmd)
    rcode = env.Execute('cd ' + env['BUILD_SIM_PATH'] + ' && ' + cmd)
    print('-'*80)
    if rcode:
        env.Exit(rcode)

    return None

#-------------------------------------------------------------------------------
#
#    Helper functions
#

#-------------------------------------------------------------------------------
def vmap_vendor_libs(env, trg_dir):

    vlpath = env['VENDOR_LIB_PATH']

    libs  = []
    for name in os.listdir(vlpath):
        lpath = os.path.join(vlpath, name)
        if os.path.isdir(lpath):
            libs.append((name, lpath))

    for lib in libs:
        cmd = env['VMAPCOM'] + ' ' + lib[0] + ' ' + os.path.join(env['VENDOR_LIB_PATH'], lib[1] )
        rcode = pexec(cmd, trg_dir)
        if rcode: return rcode

    return None

#-------------------------------------------------------------------------------
def vmap_simlib(env, libpath, trg_dir):
    name    = os.path.basename(libpath)
    dirpath = os.path.dirname(libpath)
    cmd = []
    cmd.append(env['VMAPCOM'])
    cmd.append(name)
    cmd.append(libpath)
    cmd = ' '.join(cmd)

    rcode = pexec(cmd, trg_dir)                               # map logical name to physical lib
    return rcode
          
#-------------------------------------------------------------------------------
def simlib_list(libpath):
    libs = {}
    if os.path.exists(libpath):
        for i in os.listdir(libpath):
             p = os.path.abspath(os.path.join(libpath, i))
             if os.path.isdir(p):
                 libs[i] = p
             
    return libs

#-------------------------------------------------------------------------------
def create_simlib(env, libpath, map_vendor_libs, verbose=False):
    if not os.path.exists(libpath):
        name    = os.path.basename(libpath)
        dirpath = os.path.dirname(libpath)

        print_info('create library: \'' + name + '\'')
        
        rcode = pexec(env['VLIBCOM'] + ' ' + name, dirpath)
        if rcode: return rcode

        rcode = pexec(env['VMAPCOM'] + ' -c', dirpath)
        if rcode: return rcode

        if map_vendor_libs:
            print_info('map vendor libraries')
            rcode = vmap_vendor_libs(env, dirpath)
            if rcode: return rcode

        cmd = []
        cmd.append(env['VMAPCOM'])
        cmd.append(name)
        cmd.append(os.path.abspath(libpath))
        cmd = ' '.join(cmd)
        
        if verbose:
            print(cmd)

        rcode = pexec(cmd, dirpath)
        if rcode: return rcode

    return None
#-------------------------------------------------------------------------------

#-------------------------------------------------------------------------------
#
#    Scanners
#
#---------------------------------------------------------------------
#
#    Scanner functions
#

#-------------------------------------------------------------------------------
#
#    Targets
#
def make_trg_nodes(src, src_suffix, trg_suffix, trg_dir, builder):

    s0 = src
    if SCons.Util.is_List(s0):
        s0 = str(s0[0])

    src_name = os.path.split(s0)[1]
    trg_name = src_name.replace(src_suffix, trg_suffix)
    trg      = os.path.join(trg_dir, trg_name)
    trg_list = builder(trg, src)

    #Depends(trg_list, 'top.scons')
    return trg_list

#---------------------------------------------------------------------
#
#    Pseudo-builders: IP simulation library stuff
#
def ip_simlib_scripts(env, src):
    res     = []
    src_sfx = '.'+env['IP_CORE_SUFFIX']
    trg_sfx = '-ipsim.'+env['SIM_SCRIPT_SUFFIX']
    trg_dir = os.path.join(env['IP_OOC_PATH'], env['IP_SCRIPT_DIRNAME'])
    builder = env.IpSimLibScript
    for i in src:
        res.append(make_trg_nodes(i, src_sfx, trg_sfx, trg_dir, builder))    

    return res

#-------------------------------------------------------------------------------
def compile_simlib(env, src):
    trg = env['SIMLIB_PATH']
    
    return env.Simlib(trg, src)

#-------------------------------------------------------------------------------
def compile_worklib(env, src):
    trg     = env.Dir(os.path.join(env['BUILD_SIM_PATH'], env['SIM_WORKLIB_NAME']))
    trg_dir = str(trg.dir)
    create_dirs([trg_dir])
    return env.WorkLib(trg, src)

#-------------------------------------------------------------------------------
def launch_questa_gui(env, src = []):
    return env.QuestaGui('launch_questa_gui', src)
    
#-------------------------------------------------------------------------------
def launch_questa_run(env, src = []):
    return env.QuestaRun('launch_questa_run', src)

#-------------------------------------------------------------------------------

#-------------------------------------------------------------------------------
#
#    Set up tool construction environment
#
def generate(env):
    
    Scanner = SCons.Scanner.Scanner
    Builder = SCons.Builder.Builder
    
    #-----------------------------------------------------------------
    #
    #    External Environment
    #
    if not 'XILINX_VIVADO' in env:
        env['XILINX_VIVADO'] = os.environ['XILINX_VIVADO']
    
    if 'QUESTABIN' not in env:
        print_error('E: "QUESTABIN" construction environment variable must be defined and point to "bin" directory')
        Exit(-2)
        
    if 'QUESTASIM' not in env:
        print_error('E: "QUESTASIM" construction environment variable must be defined and point to "vsim" executable')
        Exit(-2)
        
    if 'VENDOR_LIB_PATH' not in env:
        env['VENDOR_LIB_PATH'] = os.path.join( os.path.dirname(env['QUESTASIM']), 'vendor', 'xlib', 'func')
        print_warning('Warning: Vendor Library Path not specified, use default path: ' + os.path.join(env['VENDOR_LIB_PATH'], 'vendor', 'xlib'))
        print()
        
    #-----------------------------------------------------------------
    #
    #    Construction Variables
    #
    root_dir              = str(env.Dir('#'))
    build_variant         = get_build_variant_relpath()
                          
    env['TESTBENCH_NAME'] = 'top_tb'
    env['VLOGCOM']        = os.path.join(env['QUESTABIN'], 'vlog')
    env['VCOMCOM']        = os.path.join(env['QUESTABIN'], 'vcom')
    env['VLIBCOM']        = os.path.join(env['QUESTABIN'], 'vlib')
    env['VMAPCOM']        = os.path.join(env['QUESTABIN'], 'vmap')
    env['VSIMCOM']        = os.path.join(env['QUESTABIN'], 'vsim')
    
    env['VLOG_FLAGS']        = ' -incr -sv -mfcu'
    env['VCOM_FLAGS']        = ' -64 -93'
    env['VLOG_OPTIMIZATION'] = ' -O5'
    env['VOPT_FLAGS']        = ''
    env['VSIM_FLAGS']        = ''
    if 'vivado' in env['TOOLS']:
        env['VOPT_FLAGS'] = ' glbl'
        
    env['SIMLIB_NAME']       = 'sim_lib'
    env['SIMLIB_PATH']       = os.path.join(env['BUILD_SYN_PATH'], env['SIMLIB_NAME'])
    env['SIM_WORKLIB_NAME']  = 'wlib'
    env['SIM_INC_PATH']      = ''
                             
    env['SIM_SCRIPT_SUFFIX'] = 'do'
                             
    env['BUILD_SIM_PATH']    = os.path.join(root_dir, 'build', build_variant, 'sim')
    env['SIM_CMD_SCRIPT']    = os.path.abspath(search_file('questa.tcl', root_dir))
    
    env['VOPT_FILTER_RULES'] = []
    
    env['VERBOSE'] = True

    #-----------------------------------------------------------------
    #
    #   Builders
    #
    SimLib         = Builder(action = simlib, target_factory = env.fs.Dir)
    WorkLib        = Builder(action = work_lib,  target_factory = env.fs.Dir)
    QuestaGui      = Builder(action = questa_gui)
    QuestaRun      = Builder(action = questa_run)
    
    Builders = {
        'Simlib'    : SimLib,
        'WorkLib'   : WorkLib,
        'QuestaGui' : QuestaGui,
        'QuestaRun' : QuestaRun
    }
    
    env.Append(BUILDERS = Builders)

    #-----------------------------------------------------------------
    #
    #   IP core processing pseudo-builders
    #
    env.AddMethod(compile_simlib,    'CompileSimLib')
    env.AddMethod(compile_worklib,   'CompileWorkLib')
    env.AddMethod(launch_questa_gui, 'LaunchQuestaGui')
    env.AddMethod(launch_questa_run, 'LaunchQuestaRun')
        
#-------------------------------------------------------------------------------
def exists(env):
    print('questa tool: exists')
#-------------------------------------------------------------------------------
    
