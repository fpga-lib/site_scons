#-------------------------------------------------------------------------------
#
#    Xilinx Vivado SCons Tool
#
#    Author: Harry E. Zhurov
#
#-------------------------------------------------------------------------------

import os
import sys
import re

import SCons.Builder
import SCons.Scanner

from utils import *

from site_scons.site_tools.vivado.ipcores import *
from site_scons.site_tools.vivado.params  import *
from site_scons.site_tools.vivado.project import *
from site_scons.site_tools.vivado.hls     import *

#-------------------------------------------------------------------------------
#
#    Scanners
#
#---------------------------------------------------------------------
#
#    Config scanner
#
def scan_cfg_files(node, env, path):

    fname = str(node)
    if get_suffix(fname) != env['CONFIG_SUFFIX']:
        return env.File([])
        
    with open(fname) as f:
        cfg = yaml.safe_load(f)
        
    if 'import' in cfg and cfg['import']:
        imports = []
        imps = cfg['import'].split()
        for i in imps:
            fn = i + '.' + env['CONFIG_SUFFIX']
            found = False
            for p in path:
                full_path = os.path.join(p.path, fn)
                if os.path.exists(full_path):
                    imports.append(full_path)
                    found = True
                    break

            if not found:
                print_error('E: import config file ' + fn + ' not found')
                sys.exit(-2)

        return env.File(imports)

    else:
        return env.File([])

#---------------------------------------------------------------------
#
#    HDL scanner
#
def scan_hdl_files(node, env, path):

    pattern = '`include\s+\"([\w\-]+\.\w+)\"'

    inclist = [] 
    contents = node.get_text_contents()
    includes = re.findall(pattern, contents)

    for i in includes:
        found = False
        for p in path:
            full_path = os.path.join( os.path.abspath(str(p)), i)
            if os.path.exists(full_path):
                inclist.append(full_path)
                found = True
                break

#       if not found:
#           print_error('E: include file ' + i + ' not found')
#           sys.exit(-2)

    return env.File(inclist)

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

    if not 'XILINX_HLS' in env:
        env['XILINX_HLS'] = os.environ['XILINX_HLS']
        
        
    VIVADO = os.path.join(env['XILINX_VIVADO'], 'bin', 'vivado')
    HLS    = os.path.join(env['XILINX_HLS'], 'bin', 'vitis_hls')
    
    if not os.path.exists(VIVADO):
        print_error('E: Vivado not found at the path: ' + VIVADO)
        sys.exit(-1)
    
    if not os.path.exists(HLS):
        print_error('E: Vitis HLS not found at the path: ' + HLS)
        sys.exit(-1)

    #-----------------------------------------------------------------
    #
    #    Construction Variables
    #
    root_dir                     = str(env.Dir('#'))
    build_variant                = get_build_variant_relpath()
    
    env['VIVADO_VERNUM']         = version_number(env['XILINX_VIVADO'])
    env['VIVADO_PROJECT_NAME']   = 'vivado_project'
    env['TOP_NAME']              = 'top'
    env['DEVICE']                = 'xc7a200tfbg676-2'

    env['VIVADO_PROJECT_MODE']   = True

    env['SYNCOM']                = VIVADO + ' -mode batch '
    env['SYNSHELL']              = VIVADO + ' -mode tcl '
    env['SYNGUI']                = VIVADO + ' -mode gui '

    env['HLSCOM']                =  HLS
    
    
    env['SYN_TRACE']             = ' -notrace'
    env['SYN_JOURNAL']           = ' -nojournal'
    env['PROJECT_CREATE_FLAGS']  = ''
    env['HLSFLAGS']              = ''

    env['VERBOSE']               = True

    env['ROOT_PATH']             = os.path.abspath(str(Dir('#')))
    env['CFG_PATH']              = os.path.abspath(os.curdir)  # current configuration path
    env['SETTINGS_SEARCH_PATH']  = env['CFG_PATH']
    env['BUILD_SRC_PATH']        = os.path.join(root_dir, 'build', build_variant, 'src')
    env['BUILD_SYN_PATH']        = os.path.join(root_dir, 'build', build_variant, 'syn')
    env['IP_OOC_PATH']           = os.path.join(env['BUILD_SYN_PATH'], 'ip_ooc')
    env['BUILD_HLS_PATH']        = os.path.join(env['BUILD_SYN_PATH'], 'hls')
    env['INC_PATH']              = ''

    env['IP_SCRIPT_DIRNAME']     = '_script'
    env['SIM_SCRIPT_DIRNAME']    = 'sim_script'
    env['SIM_SCRIPT_PATH']       = os.path.join(env['BUILD_SYN_PATH'], env['SIM_SCRIPT_DIRNAME'])
    env['HLS_SCRIPT_DIRNAME']    = '_script'

    env['HLS_IP_NAME_SUFFIX']    = '_hlsip'
    
    env['CONFIG_SUFFIX']         = 'yml'
    env['TOOL_SCRIPT_SUFFIX']    = 'tcl'
    env['IP_CORE_SUFFIX']        = 'xci'
    env['DCP_SUFFIX']            = 'dcp'
    env['BITSTREAM_SUFFIX']      = 'bit'
    env['CONSTRAINTS_SUFFIX']    = 'xdc'
    env['VIVADO_PROJECT_SUFFIX'] = 'xpr'
    env['V_SUFFIX']              = 'v'
    env['SV_SUFFIX']             = 'sv'
    env['V_HEADER_SUFFIX']       = 'vh'
    env['SV_HEADER_SUFFIX']      = 'svh'
    env['SV_PACKAGE_SUFFIX']     = 'pkg'
    env['HLS_TARGET_SUFFIX']     = 'zip'

    env['USER_DEFINED_PARAMS']   = {}

    env.Append(SYNFLAGS = env['SYN_TRACE'])
    env.Append(SYNFLAGS = env['SYN_JOURNAL'])


    #-----------------------------------------------------------------
    #
    #   Scanners
    #
    CfgImportScanner = Scanner(name  = 'CfgImportScanner',
                       function      = scan_cfg_files,
                       skeys         = ['.' + env['CONFIG_SUFFIX']],
                       recursive     = True,
                       path_function = SCons.Scanner.FindPathDirs('SETTINGS_SEARCH_PATH')
                      )

    HdlSourceScanner = Scanner(name  = 'HldSourceScanner',
                       function      = scan_hdl_files,
                       skeys         = ['.' + env['V_SUFFIX'], '.' + env['SV_SUFFIX']],
                       recursive     = True,
                       path_function = SCons.Scanner.FindPathDirs('INC_PATH')
                      )
    #-----------------------------------------------------------------
    #
    #   Builders
    #
    IpCreateScript     = Builder(action         = ip_create_script,
                                 suffix         = env['TOOL_SCRIPT_SUFFIX'],
                                 #src_suffix     = env['IP_CONFIG_SUFFIX'],
                                 source_scanner = CfgImportScanner)

    IpSynScript        = Builder(action         = ip_syn_script,
                                 suffix         = env['TOOL_SCRIPT_SUFFIX'],
                                 source_scanner = CfgImportScanner)


    IpCreate           = Builder(action     = ip_create,
                                 suffix     = env['IP_CORE_SUFFIX'],
                                 src_suffix = env['TOOL_SCRIPT_SUFFIX'])

    IpSyn              = Builder(action     = ip_synthesize,
                                 suffix     = env['DCP_SUFFIX'],
                                 src_suffix = env['IP_CORE_SUFFIX'])

    HlsCSynth          = Builder(action = hls_csynth, chdir=False) #, source_scanner = CScanner)
    
    CfgParamsHeader    = Builder(action = cfg_params_header, source_scanner = CfgImportScanner)
    CfgParamsTcl       = Builder(action = cfg_params_tcl,    source_scanner = CfgImportScanner)

    VivadoProject      = Builder(action = vivado_project)

    SynthVivadoProject = Builder(action = synth_vivado_project, source_scanner = HdlSourceScanner)
    ImplVivadoProject  = Builder(action = impl_vivado_project)


    OpenVivadoProject  = Builder(action = open_vivado_project)

    Builders = {
        'IpCreateScript'      : IpCreateScript,
        'IpSynScript'         : IpSynScript,
        'IpCreate'            : IpCreate,
        'IpSyn'               : IpSyn,

        'HlsCSynth'           : HlsCSynth,

        'CfgParamsHeader'     : CfgParamsHeader,
        'CfgParamsTcl'        : CfgParamsTcl,

        'VivadoProject'       : VivadoProject,

        'SynthVivadoProject'  : SynthVivadoProject,
        'ImplVivadoProject'   : ImplVivadoProject,

        'OpenVivadoProject'   : OpenVivadoProject
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

    env.AddMethod(launch_hls_csynth, 'LaunchHlsCSynth')
    env.AddMethod(hlsip_syn_scripts, 'HlsIpSynScripts')

    env.AddMethod(create_cfg_params_header,    'CreateCfgParamsHeader')
    env.AddMethod(create_cfg_params_tcl,       'CreateCfgParamsTcl')
    env.AddMethod(create_vivado_project,       'CreateVivadoProject')

    env.AddMethod(launch_synth_vivado_project, 'LaunchSynthVivadoProject')
    env.AddMethod(launch_impl_vivado_project,  'LaunchImplVivadoProject')

    env.AddMethod(launch_open_vivado_project,  'LaunchOpenVivadoProject')


#-------------------------------------------------------------------------------
def exists(env):
    print('vivado tool: exists')
#-------------------------------------------------------------------------------

