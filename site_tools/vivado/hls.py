#-------------------------------------------------------------------------------
#
#    HLS Target Support for Xilinx Vivado SCons Tool
#
#    Author: Harry E. Zhurov
#
#-------------------------------------------------------------------------------

import os
import sys
import re

from utils import *

root_path = os.path.abspath(str(Dir('#'))) # <- scons-chdir fix!!!

#-------------------------------------------------------------------------------
class Params:

    def __init__(self, params_dict, src_path, env):
        self.params = params_dict
        self.error  = False
    
        #-----------------------------------------------------------------
        # name
        if not 'name' in self.params:
            print_error('E: HLS module name not specified in configuration file: \'' + src_path + '\'')
            self.error = True
            return

        self.name = self.params['name']                                                                                         

        #-----------------------------------------------------------------
        # version
        if not 'version' in self.params:
            self.version = '1.0'
        else:
            self.version = str( self.params['version'] )

        #-----------------------------------------------------------------
        # vendor
        if not 'vendor' in self.params:
            self.vendor = 'user-hls'
        else:
            self.vendor = self.params['vendor']

        #-----------------------------------------------------------------
        # library
        if not 'library' in self.params:
            self.library = 'user-library'
        else:
            self.library = self.params['library']

        #-----------------------------------------------------------------
        # clock
        if not 'clock_period' in self.params:
            print_warning('W: HLS module clock period is not specified in configuration file: \'' + src_path + '\'')
            self.clock_period = '10ns'
        else:
            self.clock_period = self.params['clock_period']

        if not 'clock_name' in self.params:
            self.clock_name = self.name + '_clk'
        else:
            self.clock_name = self.params['clock_name']
            
        if 'clock_uncertainty' in self.params:
            self.clock_uncertainty = self.params['clock_uncertainty']
            
        #-----------------------------------------------------------------
        # synthesis source list
        if not 'src_csyn_list' in self.params:
            print_error('E: HLS module has no synthesis source list in configuration file: \'' + i + '\'')
            self.error = True
            return
        
        self.src_syn_list, usedin = read_sources( self.params['src_csyn_list'], os.path.dirname(src_path), True )

        #-----------------------------------------------------------------
        # simulation source list
        if not 'src_csim_list' in self.params:
            self.src_sim_list = []
        else:
            self.src_sim_list, usedin = read_sources( self.params['src_csim_list'], os.path.dirname(src_path), True )

        #-----------------------------------------------------------------
        # hook list
        if not 'hook_list' in self.params:
            self.hook_list = []
        else:
            self.hook_list, usedin = read_sources( self.params['hook_list'], os.path.dirname(src_path), True )

        #-----------------------------------------------------------------
        # flags
        if not 'cflags' in self.params:
            self.cflags = []
        else:
            if not SCons.Util.is_List(self.params['cflags']):
                self.cflags = self.params['cflags'].split()
            else:
                self.cflags = self.params['cflags']

        if not 'csimflags' in self.params:
            self.csimflags = []
        else:
            if not SCons.Util.is_List(self.params['csimflags']):
                self.csimflags = self.params['csimflags'].split()
            else:
                self.csimflags = self.params['csimflags']
                        
#-------------------------------------------------------------------------------
def generate_csynth_script(script_path, trg_path, params, env):

    text  = generate_title('This file is automatically generated. Do not edit the file!', '#')

    #-----------------------------------------------------------------
    # generate script body
    text += 'set PROJECT_NAME  ' + params.name    + os.linesep
    text += 'set TOP_NAME      ' + params.name    + os.linesep
    text += 'set DEVICE        ' + env['DEVICE']  + os.linesep
    text += 'set SOLUTION_NAME sol_1'             + os.linesep*2

    text += '# Project structure'                 + os.linesep
    text += 'open_project -reset ${PROJECT_NAME}' + os.linesep*2

    text += '# Add syn sources'                   + os.linesep
    for s in params.src_syn_list: 
        cflags = ' ' 
        if params.cflags:
            cflags = ' -cflags "' + ' '.join(params.cflags) + '" '
        if s.endswith('.json'):
            # HLS blackboxes
            text += 'add_files -blackbox ' + s + os.linesep
        else:
            # normal HLS sources
            text += 'add_files ' + cflags + s + os.linesep
    text += os.linesep*2

    text += '# Add sim sources' + os.linesep
    for s in params.src_sim_list:
        csimflags = ' ' 
        if params.csimflags:
            csimflags = ' -csimflags "' + ' '.join(params.csimflags) + '" '
        text += 'add_files -tb' + csimflags + s + os.linesep
    text += os.linesep*2

#   text += '# Add hooks' + os.linesep
#   for s in params.hook_list:
#       text += 'source ' + s + os.linesep
#   text += os.linesep*2

    text += 'set_top ${TOP_NAME}' + os.linesep

    text += '# Add solution' + os.linesep
    text += 'open_solution -reset -flow_target vivado ${SOLUTION_NAME}'     + os.linesep
    text += 'set_part ${DEVICE}'                                            + os.linesep
    text += 'create_clock -period ' + params.clock_period + ' -name ' + params.clock_name + os.linesep
    if hasattr(params, 'clock_uncertainty'):
        text += 'set_clock_uncertainty ' + str(params.clock_uncertainty)      + os.linesep*2

    text += '# Add hooks' + os.linesep
    for h in params.hook_list:
        text += 'source ' + h + os.linesep
    text += os.linesep*2

    text += 'csynth_design' + os.linesep*2

    text += 'export_design -rtl verilog -format ip_catalog' + \
            ' -ipname '   + params.name   + ' -version ' + params.version + \
            ' -vendor ' + params.vendor + ' -library ' + params.library + \
            ' -output ' + trg_path + '.zip' + os.linesep*2
            
    text += 'exit'


    text += generate_footer('#')

    with open(script_path, 'w') as ofile:
        ofile.write(text)
    
#-------------------------------------------------------------------------------
def generate_hls_ip_create_script(script_path, ip_repo_module, name, env):
    
    ip_component = os.path.join(ip_repo_module, 'component.xml')
    ip_name      = name + env['HLS_IP_NAME_SUFFIX']
    
    print_info('generate script:           \'' + os.path.basename(script_path) + '\'')
    
    text  = generate_title('This file is automatically generated. Do not edit the file!', '#')

    text += 'set ip_name    ' + ip_name                                       + os.linesep
    text += 'set DEVICE     ' + env['DEVICE']                                 + os.linesep
    text += 'set BASE_PATH  ' + env['BUILD_SYN_PATH']                         + os.linesep
    text += 'set IP_OOC_DIR ' + os.path.join(env['IP_OOC_PATH'], ip_name)     + os.linesep*2

    text += 'create_project -in_memory -part ${DEVICE}' + os.linesep
    text += 'set_property ip_repo_paths ${BASE_PATH}/hls/ip [current_project]' + os.linesep
    text += 'update_ip_catalog' + os.linesep
    text += 'set core [ipx::open_core -set_current false ' + ip_component + ']' + os.linesep
    text += 'set vlnv [get_property vlnv $core]' + os.linesep
    text += 'ipx::unload_core $core' + os.linesep
    text += 'set_part  ${DEVICE}' + os.linesep
    text += 'create_ip -vlnv $vlnv -module_name ${ip_name} -dir ${IP_OOC_DIR}' + os.linesep*2
    
    text += 'generate_target all [get_ips  ${ip_name}]' + os.linesep
    text += 'export_simulation -of_objects [get_ips ${ip_name}] -simulator questa -absolute_path -force -directory ${BASE_PATH}/sim_script' + os.linesep*2
    
    text += 'exit ' + os.linesep
    text += generate_footer('#')

    with open(script_path, 'w') as ofile:
        ofile.write(text)
        
#-------------------------------------------------------------------------------
def compile_hls_ip_repo_module(csynth_script_path, trg_path, env):
    
    name         = get_name(trg_path)
    exec_dir     = env['BUILD_HLS_PATH']
    hls_prj_path = os.path.join(exec_dir, name)
    print_info('compile HDL IP from HLS:   \'' + name + '\'')

    Execute( Delete(hls_prj_path) )
    Execute( Delete(trg_path) )
    
    logfile = os.path.join(hls_prj_path, 'create.log')
    
    cmd = []
    cmd.append(env['HLSCOM'])
    cmd.append(env['HLSFLAGS'])
    cmd.append('-l ' + logfile)
    cmd.append(os.path.abspath(csynth_script_path))
    cmd = ' '.join(cmd)

    if env['VERBOSE']:
        print(cmd)

    rcode = pexec(cmd, exec_dir, exec_env=env['ENV'])

    import zipfile
    zipfn = trg_path + '.zip'
    with zipfile.ZipFile(zipfn, 'r') as ziparchive:
        ziparchive.extractall(trg_path)
        Execute( Delete(zipfn) )

    return rcode
    
#-------------------------------------------------------------------------------
def create_hls_ip(script_path, trg_path, exec_dir, env):
    
    name = os.path.basename(trg_path)
    print_info('create IP from HLS repo:   \'' + name + '\'')

    trg_dir = os.path.dirname(trg_path)
    Execute( Delete(trg_dir) )
    
    log_dir  = os.path.join(env['IP_OOC_PATH'], drop_suffix(name))
    logfile  = os.path.join(log_dir, 'create.log')
    
    cmd = []
    cmd.append(env['SYNCOM'])
    cmd.append(env['SYNFLAGS'])
    cmd.append('-log ' + logfile)
    cmd.append('-source ' + script_path)
    cmd = ' '.join(cmd)

    if env['VERBOSE']:
        print(cmd)

    rcode = pexec(cmd, exec_dir, exec_env=env['ENV'])
    
    from stat import S_IREAD, S_IRGRP, S_IROTH
    
    os.chmod(trg_path, S_IREAD | S_IRGRP | S_IROTH)  # make target (xci) read only to disable changing during IP synthesis

    return rcode

#-------------------------------------------------------------------------------
def add_sim_stuff(name, env):

     dat_files = glob.glob( os.path.join(env['SIM_SCRIPT_PATH'], name, '**/*.dat'), recursive=True)

     for f in dat_files:
         dst = os.path.join(env['BUILD_SIM_PATH'], os.path.basename(f) )
         if os.path.lexists(dst):
             os.remove(dst)

         os.symlink(f, dst)
         msg = colorize('create symbolic link for ', 'magenta')
         print(msg, f + ' in ' + env['BUILD_SIM_PATH'])

#-------------------------------------------------------------------------------
#
#   Builders
#
def hls_csynth_script(target, source, env):

    root_path = env['ROOT_PATH']
    os.chdir(root_path)   # <- scons-chdir fix!!!
    

    src         = source[0]
    trg         = target[0]
    src_path    = str(src)
    trg_path    = os.path.abspath( str(trg) )
    trg_name    = drop_suffix( os.path.basename(trg_path) )

    print_action('generate script:           \'' + trg.name + '\'')

    # parameters processing
    try:
        params = Params( read_config(src_path), src_path, env )

    except SearchFileException as e:
        print_error('E: HLS config read: ' + e.msg)
        print_error('    while building target: "' + trg_path + '"')
        Exit(-1)
    
    module_name = params.name

    # paths and names
    hls_path           = env['BUILD_HLS_PATH']
    hls_script_path    = os.path.join(hls_path, env['HLS_SCRIPT_DIRNAME'])
    hls_ip_repo_path   = os.path.join(hls_path, 'ip')
    hls_ip_repo_module = os.path.join(hls_ip_repo_path, module_name)
    
    # generate csynth script
    csynth_script_path = os.path.join(hls_script_path, module_name + '-csynth' + '.' + env['TOOL_SCRIPT_SUFFIX'])
    generate_csynth_script(csynth_script_path, hls_ip_repo_module, params, env)
    
    return None    
            
#-------------------------------------------------------------------------------
def hls_csynth(target, source, env):

    src         = source[0]
    trg         = target[0]
    src_path    = str(src)
    trg_path    = os.path.abspath( str(trg) )
    trg_name    = drop_suffix( os.path.basename(trg_path) )
    
    print_action('create HLS module from:    \'' + src_path + '\'')

    # retrieve parameters from source script
    with open(src_path, 'r') as sf:
        src_contents = sf.read();
        
    pattern = 'export_design.+-ipname\s(\w+)\s+-version\s(\d+\.\d+)\s+-vendor\s(\w+)\s+-library\s(\w+)'
    res = re.search(pattern, src_contents)
    
    if not res:
        print_error('E: invalid HLS module create script: \'' + src_path + '\'')
        Exit(-1)
        
    module_name = res.groups()[0]
    
    # paths and names
    hls_path           = env['BUILD_HLS_PATH']
    hls_ip_repo_path   = os.path.join(hls_path, 'ip')
    hls_ip_repo_module = os.path.join(hls_ip_repo_path, module_name)
    
    ip_create_script   = os.path.join(env['IP_OOC_PATH'], env['IP_SCRIPT_DIRNAME'], 
                                      trg_name + '-create.' + env['TOOL_SCRIPT_SUFFIX'])
    # create hls ip
    compile_hls_ip_repo_module(src_path, hls_ip_repo_module, env)
    
    # generate hls ip create script
    generate_hls_ip_create_script(ip_create_script, hls_ip_repo_module, module_name, env)
    
    # create hls ip
    create_hls_ip(ip_create_script, trg_path, os.path.join(env['IP_OOC_PATH'], trg_name), env)
    add_sim_stuff(trg_name, env)
    
    return None

#-------------------------------------------------------------------------------
def read_source_list(cfg_path, src_list_name):
    try:
        cfg_dirname = os.path.dirname(cfg_path)
        name        = os.path.basename(src_list_name)
        #print(name, cfg_dirname)
        return read_sources( name, cfg_dirname )

    except SearchFileException as e:
        print_error('E: ' + e.msg)
        print_error('    while processing file: "' + cfg_path + '"')
        Exit(-1)
    
#-------------------------------------------------------------------------------
#
#   Pseudo-builders
#
def create_hls_csynth_script(env, src):

    dirlist = [os.path.join(env['BUILD_HLS_PATH'], get_name(s)) for s in src]
    dirlist.append(os.path.join(env['BUILD_HLS_PATH'], env['HLS_SCRIPT_DIRNAME']))
    create_dirs(dirlist)
    
    targets = []
    
    # generate dependencies from sources
    for s in src:
        try:
            params = read_config(s)

        except SearchFileException as e:
            print_error('E: HLS config read: ' + e.msg)
            print_error('    while running "LaunchHlsCSynthScript" builder')
            Exit(-1)
        
        #-----------------------------------------------------------------
        # synthesis source list
        if not 'src_csyn_list' in params:
            print_error('E: HLS module has no synthesis source list in configuration file: \'' + s + '\'')
            Exit(-2)
    
        src_csyn_list = read_source_list(s, params['src_csyn_list'])
    
        #-----------------------------------------------------------------
        # simulation source list
        if not 'src_csim_list' in params:
            src_csim_list = []
        else:
            src_csim_list = read_source_list(s, params['src_csim_list'])
    
        #-----------------------------------------------------------------
        # hook list
        if not 'hook_list' in params:
            hook_list = []
        else:
            hook_list = read_source_list(s, params['hook_list'])
            
        source = str.split(s) + src_csyn_list + hook_list
    
        trg_name = get_name(s) + '-csynth.' + env['TOOL_SCRIPT_SUFFIX']
        target   = os.path.join(env['BUILD_HLS_PATH'], env['HLS_SCRIPT_DIRNAME'], trg_name)
        targets.append( env.HlsCSynthScript(target, source, env) )

    return targets
        
#-------------------------------------------------------------------------------
def launch_hls_csynth(env, src, cfg=None):

    from site_scons.site_tools.vivado.ipcores import make_trg_nodes

    if cfg:
        if len(src) != len(cfg):
            print_error('E: hls_csynth: src count:', len(src), 'must be equal to cfg count:', len(cfg))
            Exit(2)

        src = list(zip(src, cfg))
    else:
        if not SCons.Util.is_List(cfg):
            print_error('E: hls_csynth: "cfg" argument (hls module config YAML file) not specified')
            Exit(2)
    
    
    trglist = []
    src_sfx = '-csynth.'+env['TOOL_SCRIPT_SUFFIX']
    trg_sfx = env['HLS_IP_NAME_SUFFIX'] + '.'+env['IP_CORE_SUFFIX']
    builder = env.HlsCSynth
    for i in src:
        script = i[0]
        cfg    = i[1]

        # generate dependencies from sources
        try:
            params = read_config(cfg)

        except SearchFileException as e:
            print_error('E: HLS config read: ' + e.msg)
            print_error('    while running "LaunchHlsCSynth" builder')
            Exit(-1)

        #-----------------------------------------------------------------
        # synthesis source list
        if not 'src_csyn_list' in params:
            print_error('E: HLS module has no synthesis source list in configuration file: \'' + cfg + '\'')
            Exit(-2)

        csyn_list= read_source_list(cfg, params['src_csyn_list'])

        #-----------------------------------------------------------------
        # hook list
        if not 'hook_list' in params:
            hook_list = []
        else:
            hook_list = read_source_list(cfg, params['hook_list'])
            
        ip_name = get_ip_name(script, src_sfx) + env['HLS_IP_NAME_SUFFIX']
        trg_dir = os.path.join( env['IP_OOC_PATH'], ip_name, ip_name )
        trglist.append(make_trg_nodes(script + csyn_list + hook_list, src_sfx, trg_sfx, trg_dir, builder))

    return trglist
    
#-------------------------------------------------------------------------------
def hlsip_syn_scripts(env, src):
    
    from site_scons.site_tools.vivado.ipcores import make_trg_nodes
    
    trglist = []
    src_sfx = '.'+env['IP_CORE_SUFFIX']
    trg_sfx = '-syn.'+env['TOOL_SCRIPT_SUFFIX']
    trg_dir = os.path.join(env['IP_OOC_PATH'], env['IP_SCRIPT_DIRNAME'])
    builder = env.IpSynScript
    for i in src:
        trglist.append(make_trg_nodes(i, src_sfx, trg_sfx, trg_dir, builder))

    return trglist

#-------------------------------------------------------------------------------

