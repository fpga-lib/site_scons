#-------------------------------------------------------------------------------
#
#    Xilinx Vivado Non-Project Flow Configuration Tool
#
#    Author: Harry E. Zhurov
#
#-------------------------------------------------------------------------------

import os

import SCons.Builder
import SCons.Scanner

from utils import *

#-------------------------------------------------------------------------------
#
#    External Environment
#
XILINX_VIVADO = os.environ['XILINX_VIVADO']
VIVADO        = os.path.join(XILINX_VIVADO, 'bin', 'vivado')

#-------------------------------------------------------------------------------
#
#    Action functions
#
#---------------------------------------------------------------------
#
#    Build Tcl script to create OOC IP
#
def ip_create_script(target, source, env):

    src = source[0]
    trg = target[0]
    
    src_path = str(src)
    trg_path = str(trg)

    print('generate script:   \'' + trg.name + '\'')

    param_sect = 'config'

    ip_name = drop_suffix(src.name)
    ip_cfg  = read_ip_config(src_path, param_sect, env['CFG_PATH'])

    title_text =\
    'IP core "' + ip_name + '" creating script' + os.linesep*2 + \
    'This file is automatically generated. Do not edit the file manually,' + os.linesep + \
    'change parameters of IP in corresponing configuration file (cfg/ip/<IP name>)'

    text  = 'set ip_name    ' + ip_name                                   + os.linesep
    text += 'set DEVICE     ' + env['DEVICE']                             + os.linesep
    text += 'set IP_OOC_DIR ' + os.path.join(env['IP_OOC_PATH'], ip_name) + os.linesep*2
    text += 'set_part  ${DEVICE}'                                         + os.linesep
    text += 'create_ip -name ' + ip_cfg['type']
    text += ' -vendor xilinx.com'
    text += ' -library ip'
    text += ' -module_name ${ip_name}'
    text += ' -dir ${IP_OOC_DIR}'                                         + os.linesep*2

    ip_params  = ip_cfg[param_sect]
    max_pn_len = max_str_len(ip_params.keys())
    max_pv_len = max_str_len([str(i) for i in ip_params.values()])

    for p in ip_params:
        v             = str(ip_params[p])
        name_len      = len(p)
        value_len     = len(v)
        name_padding  = len(param_sect) + max_pn_len - name_len + 2
        value_padding = max_pv_len - value_len + 2
        line  = 'set_property ' + param_sect + '.' + p + ' '*name_padding + v 
        line += ' '*value_padding + '[get_ips ${ip_name}]'

        text += line + os.linesep

    text += os.linesep
    text += 'generate_target all [get_ips  ${ip_name}]'             + os.linesep
    text += 'export_ip_user_files -of_objects [get_ips ${ip_name}] '
    text += '-sync -force -quiet'                                   + os.linesep
    text += 'exit'

    out = generate_title(title_text, '#')
    out += text
    out += generate_footer('#')

    with open(trg_path, 'w') as ofile:
        ofile.write(out)

    return None
#---------------------------------------------------------------------
#
#    Build Tcl script to synthesize OOC IP
#
def ip_syn_script(target, source, env):
    
    src = source[0]
    trg = target[0]
    
    src_path = str(src)
    trg_path = str(trg)

    print('generate script:   \'' + trg.name + '\'')

    with open(src_path) as src_f:
        ip_create_script = src_f.read()

    ip_name = drop_suffix(src.name)

    title_text =\
    'IP core "' + ip_name + '" synthesizing script' + os.linesep*2 + \
    'This file is automatically generated. Do not edit the file manually,' + os.linesep + \
    'change parameters of IP in corresponing configuration file (cfg/ip/<IP name>)'

    text  = 'set ip_name    ' + ip_name                                     + os.linesep
    text += 'set DEVICE     ' + env['DEVICE']                               + os.linesep
    text += 'set IP_OOC_DIR ' + env['IP_OOC_PATH']                          + os.linesep
    text += 'set OUT_DIR    [file join ${IP_OOC_DIR} ${ip_name}]'           + os.linesep*2
    text += 'set_part  ${DEVICE}'                                           + os.linesep
    text += 'read_ip   [file join ${IP_OOC_DIR} ' 
    text += '${ip_name} ${ip_name} ${ip_name}.' + env['IP_CORE_SUFFIX']+']' + os.linesep
    text += 'synth_ip  [get_ips ${ip_name}]'                                + os.linesep
    text += 'exit'

    out = generate_title(title_text, '#')
    out += text
    out += generate_footer('#')

    #print(out)

    with open(trg_path, 'w') as ofile:
        ofile.write(out)

    return None
#---------------------------------------------------------------------
#
#    Generate IP
#
def ip_create(target, source, env):

    src      = source[0]
    trg      = target[0]
    
    src_path = str(src)
    trg_path = str(trg)
    ip_name  = drop_suffix(trg.name)
    trg_dir  = os.path.join(env['IP_OOC_PATH'], ip_name)
    logfile  = os.path.join(trg_dir, 'create.log')

    print('create IP core     \'' + trg.name + '\'')

    Execute( Delete(trg_dir) )        
    Execute( Mkdir(trg_dir) )

    cmd = []
    cmd.append(env['SYNCOM'])
    cmd.append(env['SYNFLAGS'])
    cmd.append('-log ' + logfile)
    cmd.append(' -source ' + os.path.abspath(src_path))
    cmd = ' '.join(cmd)
    
    if env['VERBOSE']:
        print(cmd)

    rcode = pexec(cmd, trg_dir)

    return rcode

#---------------------------------------------------------------------
#
#    Run OOC IP synthesis
#
def ip_synthesize(target, source, env):

    src      = source[0]
    trg      = target[0]
    
    src_path = str(src)
    trg_path = str(trg)
    ip_name  = drop_suffix(trg.name)
    trg_dir  = os.path.join(env['IP_OOC_PATH'], ip_name)
    logfile  = os.path.join(trg_dir, 'syn.log')

    print('synthesize IP core \'' + trg.name + '\'')

    cmd = []
    cmd.append(env['SYNCOM'])
    cmd.append(env['SYNFLAGS'])
    cmd.append('-log ' + logfile)
    cmd.append(' -source ' + os.path.abspath(src_path))
    cmd = ' '.join(cmd)

    if env['VERBOSE']:
        print(cmd)
    rcode = pexec(cmd, trg_dir)

    return rcode

#---------------------------------------------------------------------
#
#    Create Configuration Parameters header
#
def cfg_params_header(target, source, env):
    
    trg      = target[0]
    trg_path = str(trg)
    
    params = {}
    for src in source:
        params.update( read_config(str(src), search_root = env['CFG_PATH']) )
        
    max_len = max_str_len(params.keys()) + 2
    guard   = 'GUARD_' + os.path.splitext(trg.name)[0].upper() + '_SVH'
    text  = generate_title('This file is automatically generated. Do not edit the file!', '//')
    text += '`ifndef ' + guard + os.linesep
    text += '`define ' + guard + os.linesep*2
    
    text += '// synopsys translate_off' + os.linesep
    text += '`ifndef SIMULATOR'         + os.linesep
    text += '`define SIMULATOR'         + os.linesep
    text += '`endif // SIMULATOR'       + os.linesep
    text += '// synopsys translate_on'  + os.linesep*2
    
    for p in params:
        text += '`define ' + p + ' '*(max_len - len(p)) + str(params[p]) + os.linesep
    
    text += os.linesep + '`endif // ' + guard + os.linesep
    text += generate_footer('//')
        
    with open(trg_path, 'w') as ofile:
        ofile.write(text)
        
    return None

#-------------------------------------------------------------------------------
#
#    Scanners
#
#---------------------------------------------------------------------
#
#    Scanner functions
#
def scan_cfg_files(node, env, path):

    fname = str(node)
    with open(fname) as f:
        cfg = yaml.safe_load(f)

    if 'import' in cfg:
        imports = []
        for i in cfg['import'].split():
            fn = i + '.' + env['CONFIG_SUFFIX']
            found = False
            for p in path:
                full_path = os.path.join(p.path, fn)
                if os.path.exists(full_path):
                    imports.append(full_path)
                    found = True
                    break

            if not found:
                print('E: import config file', fn, 'not found')

        return env.File(imports)

    else:
        return env.File([])

#-------------------------------------------------------------------------------
#
#    Targets
#
def make_trg_nodes(src, src_suffix, trg_suffix, trg_dir, builder):

    s0 = src
    if(type(s0)) != str:
        s0 = str(s0[0])

    src_name = os.path.split(s0)[1]
    trg_name = src_name.replace(src_suffix, trg_suffix)
    trg      = os.path.join(trg_dir, trg_name)
    trg_list = builder(trg, src)

    #Depends(trg_list, 'top.scons')
    return trg_list

#---------------------------------------------------------------------
#
#    Processing OOC IP targets
#
def ip_create_scripts(env, src):
    res     = []
    src_sfx = '.'+env['IP_CONFIG_SUFFIX']
    trg_sfx = '-create.'+env['TOOL_SCRIPT_SUFFIX']
    trg_dir = os.path.join(env['IP_OOC_PATH'], env['IP_SCRIPT_DIRNAME'])
    create_dirs([trg_dir])
    builder = env.IpCreateScript
    for i in src:
        ip_src = os.path.join(env['CFG_IP_PATH'], i + '.' + env['IP_CONFIG_SUFFIX'])
        res.append(make_trg_nodes(ip_src, src_sfx, trg_sfx, trg_dir, builder))    

    return res
#---------------------------------------------------------------------
def ip_syn_scripts(env, src):
    res     = []
    src_sfx = '.'+env['IP_CONFIG_SUFFIX']
    trg_sfx = '-syn.'+env['TOOL_SCRIPT_SUFFIX']
    trg_dir = os.path.join(env['IP_OOC_PATH'], env['IP_SCRIPT_DIRNAME'])
    builder = env.IpSynScript
    for i in src:
        ip_src = os.path.join(env['CFG_IP_PATH'], i + '.' + env['IP_CONFIG_SUFFIX'])
        res.append(make_trg_nodes(ip_src, src_sfx, trg_sfx, trg_dir, builder))    

    return res
#---------------------------------------------------------------------
def create_ips(env, src):
    res     = []
    src_sfx = '-create.'+env['TOOL_SCRIPT_SUFFIX']
    trg_sfx = '.'+env['IP_CORE_SUFFIX']
    builder = env.IpCreate
    for i in src:
        ip_name = get_ip_name(i, src_sfx)
        trg_dir = os.path.join( env['IP_OOC_PATH'], ip_name, ip_name )
        res.append(make_trg_nodes(i, src_sfx, trg_sfx, trg_dir, builder))    

    return res
#---------------------------------------------------------------------
def syn_ips(env, src, deps=None):
    if deps:
        if len(src) != len(deps):
            print('E: ip_syn: src count:', len(src), 'must be equal deps count:', len(deps))
            sys.exit(2)

        src = list(zip(src, deps))
    else:
        print('E: ip_syn: "deps" argument (typically xci IP Core node list) not specified')
        sys.exit(2)

    res         = []
    script_sfx  = '-syn.'+env['TOOL_SCRIPT_SUFFIX']
    ip_core_sfx = '.' + env['IP_CORE_SUFFIX']
    trg_sfx     = '.'+env['DCP_SUFFIX']
    builder     = env.IpSyn
    for i in src:
        s = i[0]
        d = i[1]

        ip_name = get_ip_name(s, script_sfx)
        trg_dir = os.path.join( env['IP_OOC_PATH'], ip_name, ip_name )
        trg = make_trg_nodes(s + d, script_sfx, trg_sfx, trg_dir, builder)
        res.append(trg)

    return res
#---------------------------------------------------------------------
def create_cfg_params_header(env, trg, src):

    if not SCons.Util.is_List(src):
        src = src.split()
    source = []
    for s in src:
        ss = os.path.abspath(search_file(s))
        source.append(ss)
        
    env.CfgParamsHeader(trg, source)
    
    return trg
#---------------------------------------------------------------------

#-------------------------------------------------------------------------------
#
#    Set up tool construction environment
#
def generate(env):
    
    Scanner = SCons.Scanner.Scanner
    Builder = SCons.Builder.Builder
    
    env['SYNCOM']   = VIVADO + ' -mode batch '
    env['SYNSHELL'] = VIVADO + ' -mode tcl '
    env['SYNGUI']   = VIVADO + ' -mode gui '

    env.Append(SYNFLAGS = ' -notrace')
    env.Append(SYNFLAGS = ' -nojournal')
    
    
    env['VERBOSE'] = True
    
    env['CFG_PATH']             = os.path.abspath(os.curdir)  # current configuration path
    env['IP_SCRIPT_DIRNAME']    = '_script'

    env['CONFIG_SUFFIX']        = 'yml'
    env['IP_CONFIG_SUFFIX']     = 'yml'
    env['TOOL_SCRIPT_SUFFIX']   = 'tcl'
    env['IP_CORE_SUFFIX']       = 'xci'
    env['DCP_SUFFIX']           = 'dcp'
    env['VERILOG']              = 'v'
    env['SYSTEMVERILOG']        = 'sv'
    env['VERILOGHEADER']        = 'vh'
    env['SYSTEMVERILOGHEADER']  = 'svh'
    
    #-----------------------------------------------------------------
    #
    #   Scanners
    #
    CfgImportScanner = Scanner(name          = 'CfgImportScanner',
                       function      = scan_cfg_files,
                       skeys         = ['.' + env['IP_CONFIG_SUFFIX']],
                       recursive     = True,
                       path_function = SCons.Scanner.FindPathDirs('SETTINGS_SEARCH_PATH')
                      )    

    #-----------------------------------------------------------------
    #
    #   Builders
    #
    IpCreateScript  = Builder(action         = ip_create_script,
                              suffix         = env['TOOL_SCRIPT_SUFFIX'],
                              #src_suffix     = env['IP_CONFIG_SUFFIX'],
                              source_scanner = CfgImportScanner)
                    
    IpSynScript     = Builder(action         = ip_syn_script,
                              suffix         = env['TOOL_SCRIPT_SUFFIX'],
                              source_scanner = CfgImportScanner)
                             
                    
    IpCreate        = Builder(action     = ip_create,
                              suffix     = env['IP_CORE_SUFFIX'],
                              src_suffix = env['TOOL_SCRIPT_SUFFIX'])
                    
    IpSyn           = Builder(action     = ip_synthesize,
                              suffix     = env['DCP_SUFFIX'],
                              src_suffix = env['IP_CORE_SUFFIX'])
                    
    CfgParamsHeader = Builder(action = cfg_params_header)
        
    Builders = {
        'IpCreateScript'  : IpCreateScript,
        'IpSynScript'     : IpSynScript,
        'IpCreate'        : IpCreate,
        'IpSyn'           : IpSyn,
        'CfgParamsHeader' : CfgParamsHeader
    }

    env.Append(BUILDERS = Builders)
    
    #-----------------------------------------------------------------
    #
    #   IP core processing pseudo-builders
    #
    env.AddMethod(ip_create_scripts, 'IpCreateScripts')
    env.AddMethod(ip_syn_scripts,    'IpSynScripts')
    env.AddMethod(create_ips,        'CreateIps')
    env.AddMethod(syn_ips,           'SynIps')
    
    env.AddMethod(create_cfg_params_header, 'CreateCfgParamsHeader')
    
        
#-------------------------------------------------------------------------------
def exists(env):
    print('vivado-npf tool: exists')
#-------------------------------------------------------------------------------
    
