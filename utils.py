#*******************************************************************************
#*
#*    Build support utilities
#*
#*    Version 2.0
#*
#*    Copyright (c) 2016-2022, Harry E. Zhurov
#*
#*******************************************************************************

import os
import sys
import subprocess
import re
import glob
import yaml
import math

import select

from SCons.Script import *
from colorama import Fore, Style

#-------------------------------------------------------------------------------
# 
# 
# 
def namegen(fullpath, ext):
    basename = os.path.basename(fullpath)
    name     = os.path.splitext(basename)[0]
    return name + os.path.extsep + ext
#-------------------------------------------------------------------------------
def pexec(cmd, wdir = os.curdir, filter=[]):
    p = subprocess.Popen(cmd.split(),
                         cwd = str(wdir),
                         universal_newlines = True,
                         stdin    = subprocess.PIPE,
                         stdout   = subprocess.PIPE,
                         stderr   = subprocess.PIPE,
                         encoding = 'utf8')

    supp_warn = []
    while True:
        rlist, wlist, xlist = select.select([p.stdout, p.stderr], [], [])
        out = ''
        for r in rlist:
            if r == p.stdout:
                out += p.stdout.readline()
            elif r == p.stderr:
                out += p.stderr.readline()
        
        if len(out) == 0 and p.poll() is not None:
            break
        if out:
            match = False
            if filter:
                for item in filter:
                    if re.search(item, out):
                        supp_warn.append(out)
                        match = True
                        break

                res = re.search('(Errors\:\s\d+,\sWarnings\:\s)(\d+)', out)
                if res:
                    warn = int(res.groups()[1])
                    supp_warn_cnt = len(supp_warn)
                    out = res.groups()[0] + str(warn - supp_warn_cnt) + ' (Suppressed warnings: ' + str(supp_warn_cnt) + ')'
                    
                    with open(os.path.join(wdir, 'suppresed-warnings.log'), 'w') as f:
                        for item in supp_warn:
                            f.write("%s" % item)                    
                    
            if not match:
                print(out.strip())

    rcode = p.poll()
    
    return rcode
    
#-------------------------------------------------------------------------------
def print_info(text):
    print(Fore.LIGHTCYAN_EX + text + Style.RESET_ALL)
#-------------------------------------------------------------------------------
def print_action(text):
    print(Fore.LIGHTGREEN_EX + text + Style.RESET_ALL)
               
#-------------------------------------------------------------------------------
def print_warning(text):
    print(Fore.LIGHTYELLOW_EX + text + Style.RESET_ALL)
    
#-------------------------------------------------------------------------------
def print_error(text):
    print(Fore.LIGHTRED_EX + text + Style.RESET_ALL)
                   
#-------------------------------------------------------------------------------
def print_success(text):
    print(Fore.GREEN + text + Style.RESET_ALL)

#-------------------------------------------------------------------------------
def colorize(text, color, light=False):
    
    color = color.upper()
    if light:
        color = 'LIGHT' + color + '_EX'
    
    c = eval('Fore.' + color)
        
    return c + text + Style.RESET_ALL
    
#-------------------------------------------------------------------------------
def clog2(n: int) -> int:
    if n < 1:
        raise ValueError("expected argument value >= 1")
    res     = 0
    shifter = 1
    while n > shifter:
        shifter <<= 1
        res      += 1
    return res
#-------------------------------------------------------------------------------
def max_str_len(x):
    return len(max(x, key=len))
#-------------------------------------------------------------------------------
def search_file(fn, search_root=''):
    fname = os.path.basename(fn)
    fpath = os.path.join(search_root, fname)

    if os.path.exists(fpath):
        full_path = str.split(fpath)
    else:
        full_path = glob.glob( os.path.join(search_root, '**', fname), recursive=True )
        
    if not len(full_path):
        print_error('E: file not found: ' + fn)
        sys.exit(1)

    if len(full_path) > 1:
        print_error('E: duplicate files found: ' + ' AND '.join(full_path))
        sys.exit(1)
        
    return full_path[0]
#-------------------------------------------------------------------------------
class ConfigDict(object):

    def __init__(self, in_dict, name=''):
        
        self.data = in_dict
        self.name = name

        for key in in_dict:
            setattr(self, key, in_dict[key])
            
    def get_data(self):
        return [a for a in dir(self) if not a.startswith('__') and not callable(getattr(self, a))]
            
#-------------------------------------------------------------------------------
def eval_cfg_dict(cfg_file_path: str, cfg_dict: dict, imps=None) -> dict:
    
#   print('\n>>>>>>>>>>>>>>')
#   print('cfg_dict:', cfg_dict)
#   print('imps:',imps)
#   print('<<<<<<<<<<<<<<\n')

    if imps:               # deflating imported parameters
        for i in imps:
            var = i
            exec( var + ' = ' + 'ConfigDict(imps[i], var)' )
        
    for key in cfg_dict:
        try:
            if '.' in key:
                class dummy():
                    pass
                
                nlist = key.split('.')
                kname = nlist[0]
                exec(kname + ' = dummy()')
                for i in nlist[1:]:
                    kname += '.' + i
                    exec(kname + ' = dummy()')
                    
                exec(kname + ' = cfg_dict[key]')
                
            else:
                var = key
                exec(var + '= cfg_dict[key]')
        except Exception as e:
            print_error('E: ' + str(e))
            print_error('    File: ' + cfg_file_path + ', line: ' + var + ' : "' + cfg_dict[key] + '"')
            sys.exit(-1)

    for key in cfg_dict:
        if isinstance(cfg_dict[key], str):
            if cfg_dict[key] and cfg_dict[key][0] == '=':
                expr = cfg_dict[key][1:];
                try:
                    cfg_dict[key] = eval(expr)            # evaluate new dict value
                except Exception as e:
                    print_error('E: ' + str(e))
                    print_error('    File: ' + cfg_file_path + ', line: ' + expr)
                    sys.exit(-1)
                    
                try:
                    if isinstance(cfg_dict[key], str):
                        exec(key + ' = "' + cfg_dict[key] + '"')       # update local variable
                        cfg_dict[key] = re.sub('`', '"', cfg_dict[key])
                    else:
                        exec(key + ' = ' + str(cfg_dict[key]))         # update local variable
                except Exception as e:
                    print_error('E: ' + str(e))
                    print_error('    File: ' + cfg_file_path + ', line: ' + expr)
                    print_error('    key: ' + key + ', value: ' + str(cfg_dict[key]))
                    sys.exit(-1)
                    
                
    return cfg_dict

#-------------------------------------------------------------------------------
def read_config(fn: str, param_sect='parameters', search_root=''):

    path = search_file(fn, search_root)
    with open( path ) as f:
        cfg = yaml.safe_load(f)
        
    imps = {}
    if 'import' in cfg and cfg['import']:
        imports = cfg['import'].split()

        for i in imports:
            imp_fn = i + '.yml'                         # file name of imported data
            imps[i] = read_config(imp_fn, search_root=search_root)
                
    params = cfg[param_sect]
    params = eval_cfg_dict(path, params, imps)

    return params

#-------------------------------------------------------------------------------
def import_config(fn: str, search_root=''):
    return ConfigDict( read_config(fn, 'parameters', search_root) )
#-------------------------------------------------------------------------------
def read_ip_config(fn, param_sect, search_root=''):

    cfg_params = read_config(fn, param_sect, search_root)
    
    with open( fn ) as f:
        cfg = yaml.safe_load(f)
        
    ip_cfg = {}
    ip_cfg['type']     = cfg['type']
    ip_cfg[param_sect] = cfg_params
        
    return ip_cfg

#-------------------------------------------------------------------------------
def read_src_list(fn: str, search_root=''):

    path = search_file(fn, search_root)
    with open( path ) as f:
        cfg = yaml.safe_load(f)
        
        if cfg:
            usedin = 'syn'
            if 'usedin' in cfg:
                usedin = cfg['usedin']
                
            return cfg['sources'], usedin
        else:
            return [], ''
    
#-------------------------------------------------------------------------------
#
#    args[0] is always config file name (yaml)
#    
#    args[1], if specified, defines current build variant path
#
#      Such context is used when function 'read_sources' called from project
#      root - this takes place on build phase of SCons, for example when 
#      'Create Vivado Project' builder running. '
#      usedin' parameter also returned in this case.
#
def read_sources(*args):
    
    fn = args[0]
    
    variant_path = args[1] if len(args) > 1 else os.getcwd()
    prefix_path = [variant_path, os.path.abspath(str(Dir('#')))]
    src, usedin = read_src_list(fn, variant_path)
    
    path_list = []
    if src:
        for s in src:
            path_exists = False
            for pp in prefix_path:
                path = os.path.join(pp, s)
                if os.path.exists(path):
                    path_list.append(path)
                    path_exists = True
                    break
                
            if not path_exists:
                print_error('E: file at relative path "' + s + '" does not exists')
                print_error('    detected while processing "' + fn +'"')
                sys.exit(-1)
            
    if len(args) > 1:
        return path_list, usedin
    else:
        return path_list

#-------------------------------------------------------------------------------
def get_dirs(flist):
    dset = set( [os.path.dirname(f) for f in flist] )
    
    return list(dset)

#-------------------------------------------------------------------------------
def prefix_suffix(fn, params):
    prefix = ''
    suffix = ''
    with open( fn ) as f:
        cfg = yaml.safe_load(f)
        
    if 'options' in cfg:
        opt = cfg['options']
        if 'prefix' in opt:
            prefix = opt['prefix']
        if 'suffix' in opt:
            suffix = opt['suffix']
            
        out = {}
        for p in params:
            new_key =  prefix + p + suffix
            out[new_key] = params[p]
            
        return out
    else:
        return params
    
#-------------------------------------------------------------------------------
def version_number(path):
    pattern = '(\d+)\.\d$'

    return re.search(pattern, path).groups()[0]

#-------------------------------------------------------------------------------
def get_suffix(path):
    return os.path.splitext(path)[1][1:]

#-------------------------------------------------------------------------------
def generate_title(text: str, comment: str) -> str:
    
    hsep_len = 81 - len(comment)
    
    empty_line   = comment + os.linesep
    title_header = comment + '-'*hsep_len + os.linesep + empty_line

    title_body = comment +  (4 - len(comment))*' '
    
    title_footer = empty_line + comment + '-'*hsep_len + os.linesep
    
    lines = text.split(os.linesep)
    out = title_header
    for line in lines:
        out += title_body+ line + os.linesep
        
    out += title_footer + os.linesep
    
    return out

#-------------------------------------------------------------------------------
def generate_footer(comment: str) -> str:

    hsep_len = 81 - len(comment)

    empty_line = ' ' + os.linesep
    separator  = comment + '-'*hsep_len + os.linesep

    return  empty_line + separator
#-------------------------------------------------------------------------------
def get_ip_name(node, suffix):
    
    if SCons.Util.is_List(node):
        path = str(node[0])
    name = os.path.split(path)[1]
    ip_name = name.replace(suffix, '')
    
    return ip_name
#-------------------------------------------------------------------------------
def get_name(path):
    return os.path.splitext( os.path.basename(path) )[0]
#-------------------------------------------------------------------------------
def drop_suffix(name):
    return os.path.splitext(name)[0]
#-------------------------------------------------------------------------------
def create_dirs(dirs):
    for i in dirs:
        if not os.path.exists(i):
            Execute( Mkdir(i) )
    
#-------------------------------------------------------------------------------
def get_build_variant_relpath():
    variant = ARGUMENTS.get('variant')
    if not variant:
        return os.path.basename( os.getcwd() )
    else:
        return variant
    
#-------------------------------------------------------------------------------

