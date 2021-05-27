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
#    External Environment
#
MENTOR        = os.environ['MENTOR']
QUESTA        = os.path.join(MENTOR, 'questa', 'questasim', 'bin')
XILINX_VIVADO = os.environ['XILINX_VIVADO']

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
          
    print('generate script:           \'' + trg.name + '\'')
    
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
    search_root = env['IPSIM_CONFIG_PATH']
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
          
    print('compile library:           \'' + trg.name + '\'')
    
    if not os.path.exists(trg_path):
        #print('create lib  \'' + trg.name + '\'')
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
    src_list = ['{' + os.path.join(f.abspath) + '}' for f in source]
    if 'vivado' in env['TOOLS']:
        glbl_path = os.path.join(XILINX_VIVADO, 'data/verilog/src/glbl.v')
        src_list.append(glbl_path)
    
    out = ''

    out += 'set CFG_DIR {'    +  env['CFG_PATH'] + '}'         + os.linesep
    out += 'set TB_NAME {'    +  env['TESTBENCH_NAME'] + '}'   + os.linesep
    out += 'set WLIB_NAME {'  +  env['SIM_WORKLIB_NAME'] + '}' + os.linesep
    out += 'set SRC [list '   +  ' '.join(src_list) + ']'      + os.linesep
    out += 'set INC_PATH {'   +  env['SIM_INC_PATH'] + '}'     + os.linesep
    out += 'set VLOG_FLAGS {' +  env['VLOG_FLAGS'] + '}'       + os.linesep
    out += 'set VOPT_FLAGS {' +  env['VOPT_FLAGS'] + '}'       + os.linesep
    
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
    print('-'*80)
    print(' '*8, 'Compile project work library' + os.linesep)
    rcode = pexec(cmd, trg_dir)
    print('-'*80)
    if rcode:
        return rcode
                
    return None

#-------------------------------------------------------------------------------
def questa_gui(target, source, env):
    cmd = env['VSIMGUI'] + ' -do ' + env['SIM_CMD_SCRIPT']
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
    return env.QuestaGui('dummy', [])
    
#-------------------------------------------------------------------------------

#-------------------------------------------------------------------------------
#
#    Set up tool construction environment
#
def generate(env):
    
    Scanner = SCons.Scanner.Scanner
    Builder = SCons.Builder.Builder
    
    env['TESTBENCH_NAME'] = 'top_tb'
    
    env['ENV']['CAD']     = os.environ['CAD']
    env['ENV']['DISPLAY'] = os.environ['DISPLAY']
    env['ENV']['HOME']    = os.environ['HOME']
        
    root_dir        = str(env.Dir('#'))
    cfg_name        = os.path.abspath(os.curdir)

    env['CFG_NAME'] = cfg_name
    env['VLOGCOM']  = os.path.join(QUESTA, 'vlog')
    env['VLIBCOM']  = os.path.join(QUESTA, 'vlib')
    env['VMAPCOM']  = os.path.join(QUESTA, 'vmap')
    env['VSIMCOM']  = os.path.join(QUESTA, 'vsim')
    env['VSIMGUI']  = os.path.join(MENTOR, 'questa.sh') + ' -gui'
    
    env['VLOG_FLAGS']        = ' -incr -sv -mfcu'
    env['VLOG_OPTIMIZATION'] = ' -O5'
    if 'vivado' in env['TOOLS']:
        env['VOPT_FLAGS'] = ' glbl'
    
    env['IP_SIMLIB_NAME']    = 'ipsimlib'
    env['SIM_WORKLIB_NAME']  = 'wlib'
    env['SIM_INC_PATH']      = ''
    
    env['SIM_SCRIPT_SUFFIX'] = 'do'
    
    env['BUILD_SIM_PATH']    = os.path.join(root_dir, 'build', os.path.basename(cfg_name), 'sim')
    env['IP_SIMLIB_PATH']    = os.path.join(env['IP_OOC_PATH'], env['IP_SIMLIB_NAME'])
    env['IPSIM_CONFIG_PATH'] = os.path.join(root_dir, 'lib', 'ipsim')
    env['SIM_CMD_SCRIPT']    = os.path.abspath(search_file('questa.tcl', str(Dir('#'))))
    
    env['VERBOSE'] = True

    #-----------------------------------------------------------------
    #
    #   Builders
    #
    IpSimLibScript = Builder(action = ip_simlib_script)
    IpSimLib       = Builder(action = ip_simlib, target_factory = env.fs.Dir)
    WorkLib        = Builder(action = work_lib,  target_factory = env.fs.Dir)
    QuestaGui      = Builder(action = questa_gui)
    
    Builders = {
        'IpSimLibScript' : IpSimLibScript,
        'IpSimlib'       : IpSimLib,
        'WorkLib'        : WorkLib,
        'QuestaGui'      : QuestaGui
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
        
#-------------------------------------------------------------------------------
def exists(env):
    print('questa tool: exists')
#-------------------------------------------------------------------------------
    
