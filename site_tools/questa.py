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
def ip_simlib_script(target, source, env):

    src = source[0]
    trg = target[0]

    src_path = str(src)
    trg_path = str(trg)
    
    ip_name = drop_suffix(src.name)
          
    print_action('generate script:           \'' + trg.name + '\'')
    
    # IP type
    pattern = 'componentRef\s+.+spirit\:name=\"(\w+)\"'
    with open(src_path) as f:
        contents = f.read()
    res = re.search(pattern, contents)
    if res:
        ip_type = res.groups()[0]
    else:
        print('E: IP type not found in IP core file (xci)')
        return -1
    
    # read IP sim sources
    param_sect  = 'sources'
    search_root = env['IP_SIM_SRC_LIST_PATH']
    src_sim     =  read_src_list(ip_type + '.' + env['CONFIG_SUFFIX'], search_root)
    
    src_str = ' '.join(src_sim).replace('${ip_name}', ip_name)
    
    # create script
    title_text =\
    'IP core "' + ip_name + '" simulation library compile script' + os.linesep*2 + \
    'This file is automatically generated. Do not edit the file manually.'
    
    text  = 'onerror {quit -f -code 255}' + os.linesep*2
    text += 'vlog -work ipsimlib' + env['VLOG_FLAGS'] + env['VLOG_OPTIMIZATION'] + ' \\' + os.linesep
    for i in src_sim:
        text += ' '*4 + i.replace('${ip_name}', ip_name) + ' \\' + os.linesep
    
    text += os.linesep + 'exit' + os.linesep
        
    out = generate_title(title_text, '#')
    out += text
    out += generate_footer('#')
        
    with open(trg_path, 'w') as ofile:
        ofile.write(out)
               
    return None

#-------------------------------------------------------------------------------
def ip_simlib(target, source, env):

    trg = target[0]

    trg_path = str(trg)
    trg_dir  = str(trg.dir)
          
    print_action('compile library:           \'' + trg.name + '\'')
    
    if not os.path.exists(trg_path):
        rcode = pexec(env['VLIBCOM'] + ' ' + trg.name, trg_dir)
        if rcode: return rcode
        
        rcode = pexec(env['VMAPCOM'] + ' -c', trg_dir)
        if rcode: return rcode

        cmd = []
        cmd.append(env['VMAPCOM'])
        cmd.append(trg.name)
        cmd.append(os.path.abspath(trg_path))
        cmd = ' '.join(cmd)

        if env['VERBOSE']:
          print(cmd)
        
        rcode = pexec(cmd, trg_dir)
        if rcode: return rcode
                            
    for src in source:
        cmd = []
        cmd.append(env['VSIMCOM'])
        cmd.append(' -batch')
        cmd.append(' -do ' + os.path.abspath(str(src)))
        cmd = ' '.join(cmd)
        
        ip_name = src.name.replace('-ipsim.'+env['SIM_SCRIPT_SUFFIX'], '')
        print('-'*80)
        print(' '*8, 'Compile', '\'' + ip_name + '\'', 'modules for simlib')
        rcode = pexec(cmd, env['IP_OOC_PATH'])
        print('-'*80)
        if rcode: 
            Execute( Delete(src) )        
            return rcode
        
    return None
#-------------------------------------------------------------------------------
def work_lib(target, source, env):
    
    trg      = target[0]
    trg_path = str(trg)
    trg_dir  = str(trg.dir)
    
    #-----------------------------------------------------------------
    #
    #   Create work library
    #
    if not os.path.exists(trg_path):
        rcode = pexec(env['VLIBCOM'] + ' ' + trg.name, trg_dir)   # create lib
        if rcode: return rcode

        rcode = pexec(env['VMAPCOM'] + ' -c', trg_dir)            # copy modelsim.ini from queta
        if rcode: return rcode
    
        # map IP simulation library
        cmd = []
        cmd.append(env['VMAPCOM'])
        cmd.append(env['IP_SIMLIB_NAME'])
        cmd.append(env['IP_SIMLIB_PATH'])
        cmd = ' '.join(cmd)
        
        if env['VERBOSE']:
          print(cmd)
        
        rcode = pexec(cmd, trg_dir)                               # map logical name to physical lib
        if rcode: return rcode
        
        # map work library      
        cmd = []
        cmd.append(env['VMAPCOM'])
        cmd.append(trg.name)
        cmd.append(os.path.abspath(trg_path))
        cmd = ' '.join(cmd)
        
        if env['VERBOSE']:
            print(cmd)
        
        rcode = pexec(cmd, trg_dir)                               # map logical name to physical lib
        if rcode: return rcode
             
    
    #-----------------------------------------------------------------
    #
    #   Create handoff file
    #
    if 'vivado' in env['TOOLS']:
        glbl_path = File(os.path.join(env['XILINX_VIVADO'], 'data/verilog/src/glbl.v'))
        source.append(glbl_path)
        
    src_list = ' '.join(['{' + os.path.join(f.abspath) + '}' for f in source])
    incpath  = ' '.join(env['SIM_INC_PATH'])
    
    out = ''

    out += 'set CFG_DIR {'    + env['CFG_PATH'] + '}'         + os.linesep
    out += 'set TB_NAME {'    + env['TESTBENCH_NAME'] + '}'   + os.linesep
    out += 'set WLIB_NAME {'  + env['SIM_WORKLIB_NAME'] + '}' + os.linesep
    out += 'set SRC [list '   + src_list + ']'                + os.linesep
    out += 'set INC_PATH {'   + incpath  + '}'                + os.linesep
    out += 'set VLOG_FLAGS {' + env['VLOG_FLAGS'] + '}'       + os.linesep
    out += 'set VOPT_FLAGS {' + env['VOPT_FLAGS'] + '}'       + os.linesep
    out += 'set VSIM_FLAGS {' + env['VSIM_FLAGS'] + '}'       + os.linesep
    
    handoff_path = os.path.join( str(trg.dir), 'handoff.do')
    with open(handoff_path, 'w') as ofile:
        ofile.write(out)
        
    #-----------------------------------------------------------------
    #
    #   Compile work library
    #
    cmd  = env['VSIMCOM'] + ' -c'
    cmd += ' -do ' + env['SIM_CMD_SCRIPT']
    cmd += ' -do c'             
    cmd += ' -do exit'          

    #print(cmd)
    msg = colorize('Compile project work library', 'yellow')
    print(colorize('-'*80, 'yellow'))
    print(' '*20, msg, os.linesep)
    rcode = pexec(cmd, trg_dir)
    print(colorize('-'*80, 'yellow'))
    if rcode:
        return rcode
                
    return None

#-------------------------------------------------------------------------------
def questa_gui(target, source, env):
    cmd = env['QUESTASIM'] + ' -gui ' + ' -do ' + env['SIM_CMD_SCRIPT']
    print(cmd)
    env.Execute('cd ' + env['BUILD_SIM_PATH'] + ' && ' + cmd)
    
    return None
    
#-------------------------------------------------------------------------------
def questa_run(target, source, env):
    cmd = env['QUESTASIM'] + ' -batch ' + ' -do ' + env['SIM_CMD_SCRIPT'] + ' -do run_sim'
    print(cmd)
    env.Execute('cd ' + env['BUILD_SIM_PATH'] + ' && ' + cmd)

    return None

#-------------------------------------------------------------------------------
#
#    Helper functions
#

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
    trg = os.path.join(env['IP_OOC_PATH'], env['IP_SIMLIB_NAME'])
    return env.IpSimlib(trg, src)

#-------------------------------------------------------------------------------
def compile_worklib(env, src):
    trg     = env.Dir(os.path.join(env['BUILD_SIM_PATH'], env['SIM_WORKLIB_NAME']))
    trg_dir = str(trg.dir)
    create_dirs([trg_dir])
    return env.WorkLib(trg, src)

#-------------------------------------------------------------------------------
def launch_questa_gui(env):
    return env.QuestaGui('launch_questa_gui', [])
    
#-------------------------------------------------------------------------------
def launch_questa_run(env):
    return env.QuestaRun('launch_questa_run', [])

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
        
        
    #-----------------------------------------------------------------
    #
    #    Construction Variables
    #
    root_dir              = str(env.Dir('#'))
    cfg_name              = os.path.basename( os.getcwd() )
                          
    env['TESTBENCH_NAME'] = 'top_tb'
    env['CFG_NAME']       = cfg_name
    env['VLOGCOM']        = os.path.join(env['QUESTABIN'], 'vlog')
    env['VLIBCOM']        = os.path.join(env['QUESTABIN'], 'vlib')
    env['VMAPCOM']        = os.path.join(env['QUESTABIN'], 'vmap')
    env['VSIMCOM']        = os.path.join(env['QUESTABIN'], 'vsim')
    
    env['VLOG_FLAGS']        = ' -incr -sv -mfcu'
    env['VLOG_OPTIMIZATION'] = ' -O5'
    env['VOPT_FLAGS']        = ''
    env['VSIM_FLAGS']        = ''
    if 'vivado' in env['TOOLS']:
        env['VOPT_FLAGS'] = ' glbl'
        
    env['IP_SIMLIB_NAME']       = 'ipsimlib'
    env['SIM_WORKLIB_NAME']     = 'wlib'
    env['SIM_INC_PATH']         = ''
                                
    env['SIM_SCRIPT_SUFFIX']    = 'do'
                              
    env['BUILD_SIM_PATH']       = os.path.join(root_dir, 'build', cfg_name, 'sim')
    env['IP_SIMLIB_PATH']       = os.path.join(env['IP_OOC_PATH'], env['IP_SIMLIB_NAME'])
    env['IP_SIM_SRC_LIST_PATH'] = os.path.join(root_dir, 'site_scons', 'ip_simsrc_list_xilinx')
    env['SIM_CMD_SCRIPT']       = os.path.abspath(search_file('questa.tcl', root_dir))
    
    env['VERBOSE'] = True

    #-----------------------------------------------------------------
    #
    #   Builders
    #
    IpSimLibScript = Builder(action = ip_simlib_script)
    IpSimLib       = Builder(action = ip_simlib, target_factory = env.fs.Dir)
    WorkLib        = Builder(action = work_lib,  target_factory = env.fs.Dir)
    QuestaGui      = Builder(action = questa_gui)
    QuestaRun      = Builder(action = questa_run)
    
    Builders = {
        'IpSimLibScript' : IpSimLibScript,
        'IpSimlib'       : IpSimLib,
        'WorkLib'        : WorkLib,
        'QuestaGui'      : QuestaGui,
        'QuestaRun'      : QuestaRun
    }
    
    env.Append(BUILDERS = Builders)

    #-----------------------------------------------------------------
    #
    #   IP core processing pseudo-builders
    #
    env.AddMethod(ip_simlib_scripts, 'IpSimLibScripts')
    env.AddMethod(compile_simlib,    'CompileSimLib')
    env.AddMethod(compile_worklib,   'CompileWorkLib')
    env.AddMethod(launch_questa_gui, 'LaunchQuestaGui')
    env.AddMethod(launch_questa_run, 'LaunchQuestaRun')
        
#-------------------------------------------------------------------------------
def exists(env):
    print('questa tool: exists')
#-------------------------------------------------------------------------------
    
