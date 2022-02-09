#-------------------------------------------------------------------------------
#
#    HLS Target Support for Xilinx Vivado SCons Tool
#
#    Author: Harry E. Zhurov
#
#-------------------------------------------------------------------------------

import os
import sys

from utils import *

top_path = os.path.abspath(str(Dir('#'))) # <- scons-chdir fix!!!

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
            print_warning('W: HLS module clock period not specified in configuration file: \'' + src_path + '\'')
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

        print('src_csyn_list:', self.params['src_csyn_list'])
        self.src_syn_list, usedin = read_sources( self.params['src_csyn_list'], env['CFG_PATH'] )

        #-----------------------------------------------------------------
        # simulation source list
        if not 'src_csim_list' in self.params:
            self.src_sim_list = []
        else:
            self.src_sim_list, usedin = read_sources( self.params['src_csim_list'], env['CFG_PATH'] )

        #-----------------------------------------------------------------
        # hook list
        if not 'hook_list' in self.params:
            self.hook_list = []
        else:
            self.hook_list, usedin = read_sources( self.params['hook_list'], env['CFG_PATH'] )

        #-----------------------------------------------------------------
        # flags
        if not 'cflags' in self.params:
            self.cflags = ''
        else:
            if self.params['cflags']:
                self.cflags = ' -cflags ' + self.params['cflags']
            else:
                self.cflags = ''

        if not 'csimflags' in self.params:
            self.csimflags = ''
        else:
            if self.params['csimflags']:
                self.csimflags = ' -csimflags ' + self.params['csimflags']
            else:
                self.csimflags = ''
                        
#-------------------------------------------------------------------------------
def generate_csynth_script(script_path, trg_path, params, env):
    text  = generate_title('This file is automatically generated. Do not edit the file!', '#')

    print_info('create HLS csynth script:  \'' + os.path.basename(script_path) + '\'')
    #-----------------------------------------------------------------
    # generate script body
    text += 'set PROJECT_NAME  ' + params.name    + os.linesep
    text += 'set TOP_NAME      ' + params.name    + os.linesep
    text += 'set DEVICE        ' + env['DEVICE']  + os.linesep
    text += 'set SOLUTION_NAME sol_1'             + os.linesep*2

    text += '# Project structure'                 + os.linesep
    text += 'open_project -reset ${PROJECT_NAME}' + os.linesep*2

    text += '# Add syn sources'                   + os.linesep
    print('<<', params.src_syn_list)
    for s in params.src_syn_list:    
        print(s)                    
        text += 'add_files ' + params.cflags + ' ' + s   + os.linesep
    text += os.linesep*2

    text += '# Add sim sources' + os.linesep
    for s in params.src_sim_list:
        text += 'add_files -tb ' + params.csimflags + ' ' + s + os.linesep
    text += os.linesep*2

    text += '# Add hooks'          + os.linesep
    for s in params.hook_list:                        
        text += 'source ' + s   + os.linesep
    text += os.linesep*2

    text += 'set_top ${TOP_NAME}' + os.linesep

    text += '# Add solution' + os.linesep
    text += 'open_solution -reset -flow_target vivado ${SOLUTION_NAME}'     + os.linesep
    text += 'set_part ${DEVICE}'                                            + os.linesep
    text += 'create_clock -period ' + params.clock_period + ' -name ' + params.clock_name + os.linesep
    if hasattr(params, 'clock_uncertainty'):
        text += 'set_clock_uncertainty ' + params.clock_uncertainty      + os.linesep*2

    text += '# Add hooks' + os.linesep
    for h in params.hook_list:
        text += 'source ' + h + os.linesep
    text += os.linesep*2

    text += 'csynth_design' + os.linesep*2

    text += 'export_design -rtl verilog -format ip_catalog' + \
            ' -ipname '   + params.name   + ' -version ' + params.version + \
            ' -vendor ' + params.vendor + ' -library ' + params.library + \
            ' -output ' + trg_path + os.linesep*2


    text += generate_footer('#')

    with open(script_path, 'w') as ofile:
        ofile.write(text)
    
#-------------------------------------------------------------------------------
def generate_hls_ip_create_script(script_path, params, env):
    text  = generate_title('This file is automatically generated. Do not edit the file!', '#')

    
    text += generate_footer('#')

    with open(script_path, 'w') as ofile:
        ofile.write(text)
#-------------------------------------------------------------------------------
def generate_hls_ip(csynth_script_path, trg_path, exec_dir, env):
    
    ip_repo_name = os.path.join( os.path.dirname(trg_path), get_name(trg_path))
    print_info('generate HDL IP from HLS:  \'' + ip_repo_name + '\'')

    logfile = os.path.join(exec_dir, 'create.log')
    
    cmd = []
    cmd.append(env['HLSCOM'])
    cmd.append(env['HLSFLAGS'])
    cmd.append('-l ' + logfile)
    cmd.append(csynth_script_path)
    cmd = ' '.join(cmd)

    if env['VERBOSE']:
        print(cmd)

    rcode = pexec(cmd, exec_dir)

    import zipfile
    with zipfile.ZipFile(trg_path, 'r') as ziparchive:
        ziparchive.extractall(ip_repo_name)
    
    return rcode
    
#-------------------------------------------------------------------------------
#
#   Builder
#
def hls_csynth(target, source, env):

    print(os.getcwd())
    print(env.HlsCSynth.__dict__)

    
    ####################################################
    print('>>>>>>>', os.path.abspath(str(Dir('#'))))
    print('>>>top:', top_path)
    
    os.chdir(top_path)   # <- scons-chdir fix!!!
    print('>> current path:', os.getcwd())
    ####################################################
    
    src         = source[0]
    trg         = target[0]
    src_path    = str(src)
    trg_path    = os.path.abspath( str(trg) )
    module_name = get_name(trg.name)
    
    print_action('create HLS module:         \'' + module_name + '\'')

    # parameters processing
    params = Params( read_config(str(src), search_root = env['CFG_PATH']), src_path, env)
    if params.error:
        return -2

    # generate csynth script
    csynth_script_path = os.path.join(env['BUILD_HLS_PATH'], 
                                      env['HLS_SCRIPT_DIRNAME'], 
                                      get_name(trg.name)) + '-csynth' + '.' + env['TOOL_SCRIPT_SUFFIX']
    generate_csynth_script(csynth_script_path, trg_path, params, env)

    # create hls ip
    generate_hls_ip(csynth_script_path, trg_path, env['BUILD_HLS_PATH'], env)
    
    
    # generate hls ip create script
    
    return None
    
#-------------------------------------------------------------------------------
#
#   Pseudo-builder
#
def launch_hls_csynth(env, src):
    
    dirlist = [os.path.join(env['BUILD_HLS_PATH'], get_name(s)) for s in src]
    dirlist.append(os.path.join(env['BUILD_HLS_PATH'], env['HLS_SCRIPT_DIRNAME']))
    create_dirs(dirlist)
    
    targets = []
    
    # generate dependencies from sources
    for s in src:
        params = read_config(s)
        
        #-----------------------------------------------------------------
        # synthesis source list
        if not 'src_csyn_list' in params:
            print_error('E: HLS module has no synthesis source list in configuration file: \'' + s + '\'')
            return -2
    
        src_csyn_list = read_sources( params['src_csyn_list'] )
    
        #-----------------------------------------------------------------
        # simulation source list
        if not 'src_csim_list' in params:
            src_csim_list = []
        else:
            src_csim_list = read_sources( params['src_csim_list'] )
    
        #-----------------------------------------------------------------
        # hook list
        if not 'hook_list' in params:
            hook_list = []
        else:
            hook_list = read_sources( params['hook_list'] )
            
        source = src + src_csyn_list + src_csim_list + hook_list
    
        trg_name = get_name(s)
        target   = os.path.join(env['BUILD_HLS_PATH'], 'ip', trg_name + '.' + env['HLS_TARGET_SUFFIX'])
        targets.append( env.HlsCSynth(target, source, env) )
            
    return targets
        
#-------------------------------------------------------------------------------

