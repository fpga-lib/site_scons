#*******************************************************************************
#*
#*    Build support utilities
#*
#*    Version 1.0
#*
#*    Copyright (c) 2016-2021, Harry E. Zhurov
#*
#*******************************************************************************

import os
import sys
import subprocess
import re
import glob
import yaml

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
def pexec(cmd, wdir = os.curdir):
    p = subprocess.Popen(cmd.split(),
                         cwd = str(wdir),
                         universal_newlines = True,
                         stdin    = subprocess.PIPE,
                         stdout   = subprocess.PIPE,
                         stderr   = subprocess.PIPE,
                         encoding = 'utf8')

    while True:
        out = p.stdout.readline()    
        if len(out) == 0 and p.poll() is not None:
            break
        if out:
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
class Dict2Class(object):

    def __init__(self, in_dict, name=''):
        
        self.data = in_dict
        self.name = name

        for key in in_dict:
            setattr(self, key, in_dict[key])
            
    def get_data(self):
        return [a for a in dir(self) if not a.startswith('__') and not callable(getattr(self, a))]
            
#-------------------------------------------------------------------------------
def eval_cfg_dict(cfg_dict: dict, imps=None) -> dict:
    
#   print('\n>>>>>>>>>>>>>>')
#   print('cfg_dict:', cfg_dict)
#   print('imps:',imps)
#   print('<<<<<<<<<<<<<<\n')

    if imps:               # deflating imported parameters
        for i in imps:
            var = i
            exec( var + ' = ' + 'Dict2Class(imps[i], var)' )
        
    for key in cfg_dict:
        var = key
        exec(var + '= cfg_dict[key]')

    for key in cfg_dict:
        if isinstance(cfg_dict[key], str):
            if cfg_dict[key][0] == '=':
                cfg_dict[key] = eval(cfg_dict[key][1:])            # evaluate new dict value
                if isinstance(cfg_dict[key], str):
                    exec(key + ' = "' + cfg_dict[key] + '"')       # update local variable
                    cfg_dict[key] = re.sub('`', '"', cfg_dict[key])
                else:
                    exec(key + ' = ' + str(cfg_dict[key]))         # update local variable
                
    return cfg_dict

#-------------------------------------------------------------------------------
def read_config(fn: str, param_sect='parameters', search_root=''):

    path = search_file(fn, search_root)
    with open( path ) as f:
        cfg = yaml.safe_load(f)

    imps = {}
    if 'import' in cfg:
        imports = cfg['import'].split()

        for i in imports:
            imp_fn = i + '.yml'                         # file name of imported data
            imps[i] = read_config(imp_fn, search_root=search_root)
                
    params = cfg[param_sect]
    params = eval_cfg_dict(params, imps)

    return params

#-------------------------------------------------------------------------------
def import_config(fn: str):
    return Dict2Class( read_config(fn) )
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
        
    return cfg['sources']
    
#-------------------------------------------------------------------------------
def read_sources(fn):
    src = read_src_list(fn)
    root_dir = str(Dir('#'))
    return [os.path.join(root_dir, i) for i in src]

#-------------------------------------------------------------------------------
def get_dirs(flist):
    return [os.path.dirname(f) for f in flist]

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

