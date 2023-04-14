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

from pathlib import Path

import select

from SCons.Script import *
from colorama import Fore, Style

config_search_path = []
check_exclude_path = []

if 'SCONS_COLORING_DISABLE' in os.environ and os.environ['SCONS_COLORING_DISABLE'].upper() == 'YES':
    COLORING_DISABLE = True
else:
    COLORING_DISABLE = False

#-------------------------------------------------------------------------------
# 
# 
# 
def namegen(fullpath, ext):
    return Path(fullpath).with_suffix(os.path.extsep + ext)

#   basename = os.path.basename(fullpath)
#   name     = os.path.splitext(basename)[0]
#   return name + os.path.extsep + ext


#-------------------------------------------------------------------------------
def pexec(cmd, wdir = os.curdir, exec_env=os.environ.copy(), filter=[]):
    p = subprocess.Popen(cmd.split(),
                         cwd = str(wdir),
                         env=exec_env,
                         universal_newlines = True,
                         stdin    = subprocess.PIPE,
                         stdout   = subprocess.PIPE,
                         #stderr   = subprocess.PIPE,
                         stderr   = subprocess.STDOUT,
                         encoding = 'utf8')

    supp_warn = []
    while True:
#       rlist, wlist, xlist = select.select([p.stdout, p.stderr], [], [])
#       out = ''
#       for r in rlist:
#           if r == p.stdout:
#               out += p.stdout.readline()
#           elif r == p.stderr:
#               out += p.stderr.readline()
        
        out = p.stdout.readline()

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
                    
                    #with open(os.path.join(wdir, 'suppresed-warnings.log'), 'w') as f:
                    with open( Path.joinpath(wdir, 'suppresed-warnings.log'), 'w') as f:
                        for item in supp_warn:
                            f.write("%s" % item)                    
                    
            if not match:
                print(out.strip())

    rcode = p.poll()
    
    return rcode
    
#-------------------------------------------------------------------------------
def cexec(cmd, wdir = os.curdir, exec_env=os.environ.copy()):
    p = subprocess.Popen(cmd.split(), 
                         cwd = str(wdir),
                         env=exec_env,
                         universal_newlines = True,
                         stdin  = subprocess.PIPE,
                         stdout = subprocess.PIPE,
                         stderr = subprocess.PIPE )


    out, err = p.communicate()

    return p.returncode, out, err

#-------------------------------------------------------------------------------
def cprint(text, color):
    ccode, rcode = [color, Style.RESET_ALL] if not COLORING_DISABLE else ['', '']
    print(ccode + text + rcode)
    
#-------------------------------------------------------------------------------
def print_info(text):
    cprint(text, Fore.LIGHTCYAN_EX)
    
#-------------------------------------------------------------------------------
def print_action(text):
    cprint(text, Fore.LIGHTGREEN_EX)
               
#-------------------------------------------------------------------------------
def print_warning(text):
    cprint(text, Fore.LIGHTYELLOW_EX)
    
#-------------------------------------------------------------------------------
def print_error(text):
    cprint(text, Fore.LIGHTRED_EX)
                   
#-------------------------------------------------------------------------------
def print_success(text):
    cprint(text, Fore.GREEN)

#-------------------------------------------------------------------------------
def colorize(text, color, light=False):
    
    color = color.upper()
    if light:
        color = 'LIGHT' + color + '_EX'
    
    c = eval('Fore.' + color)
        
    ccode, rcode = [c, Style.RESET_ALL] if not COLORING_DISABLE else ['', '']

    return ccode + text + rcode
    
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
class SearchFileException(Exception):

    def __init__(self, msg):
        self.msg = msg
        
#-------------------------------------------------------------------------------
def pathlist(path):
    if SCons.Util.is_List(path):
        return [Path(p) for p in path]
    elif SCons.Util.is_String(path):
        return [Path(p) for p in path.split()]
    else:
        raise SearchFileException('invalid type for ' + path + '. Only List and String types supported')
        
        
#-------------------------------------------------------------------------------
def add_search_path(path):
    global config_search_path
    
    config_search_path += pathlist(path)
    
#   if SCons.Util.is_List(path):
#       config_search_path += [Path(p) for p in path]
#   else:
#       config_search_path.append(Path(path))
                
#-------------------------------------------------------------------------------
def get_search_path():
    return config_search_path
    
#-------------------------------------------------------------------------------
def add_check_exclude_path(path):
    global check_exclude_path

    if SCons.Util.is_List(path):
        check_exclude_path += path
    else:
        check_exclude_path.append(path)

#-------------------------------------------------------------------------------
def search_file(fn, search_path=[]):
    
    fp = Path(fn)
    #if os.path.exists(fn):
    if fp.exists():
        #return os.path.abspath(fn)
        return fp.absolute()
        
    if not SCons.Util.is_List(search_path):
        search_path = str.split(search_path)
        
    spath = [Path(p) for p in search_path + config_search_path]
    
    for p in spath:
        #path = os.path.join(p, fn)
        path = p.joinpath(fn)
        #if os.path.exists(path):
        if path.exists():
            return path.absolute()
    
    msg = 'file "' + fn + '" not found at search path list:' + os.linesep
    for p in spath:
        msg += ' '*4 + '"' + p + '"' + os.linesep
    
    raise SearchFileException(msg)

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
                
                
            if isinstance(cfg_dict[key], str):
                if cfg_dict[key] and cfg_dict[key][0] == '=':
                    expr = cfg_dict[key][1:];
                    try:
                        val = eval(expr)
                        if val and isinstance(val, str) and '\\' in val:
                            val = val.replace('\\', '\\\\')
                        cfg_dict[key] = val # eval(expr)            # evaluate new dict value
                    except Exception as e:
                        print_error('E: ' + str(e) + '. Got while evaluate parameter value')
                        print('expr: ', expr, ' expr type: ', type(expr))
                        print('result value: ', val, ' result value type:', type(val))
                        print_error('    File: ' + str(cfg_file_path) + ', line: ' + expr)
                        Exit(-1)

                    try:
                        if isinstance(cfg_dict[key], str):
                            exec(key + ' = "' + cfg_dict[key] + '"')       # update local variable
                            cfg_dict[key] = re.sub('`', '"', cfg_dict[key])
                        else:
                            exec(key + ' = ' + str(cfg_dict[key]))         # update local variable
                    except Exception as e:
                        print_error('E: ' + str(e) + '. Got while update local variable')
                        print_error('    File: ' + str(cfg_file_path) + ', line: ' + expr)
                        print_error('    key: ' + key + ', value: ' + str(cfg_dict[key]))
                        Exit(-1)
                
        except Exception as e:
            print_error('E: ' + str(e))
            print_error('    File: ' + str(cfg_file_path) + ', line: ' + var + ' : "' + cfg_dict[key] + '"')
            Exit(-1)

    return cfg_dict

#-------------------------------------------------------------------------------
def read_config(fn: str, param_sect='parameters', search_path=[]):

    path = search_file(fn, search_path)
    #path = search_file(fn)
    with open( path ) as f:
        cfg = yaml.safe_load(f)
        
    imps = {}
    if 'import' in cfg and cfg['import']:
        imports = cfg['import'].split()

        for i in imports:
            imp_fn = i + '.yml'                         # file name of imported data
            imps[i] = read_config(imp_fn, search_path=search_path)
                
    params = cfg[param_sect]
    params = eval_cfg_dict(path, params, imps)

    return params

#-------------------------------------------------------------------------------
def import_config(fn: str, search_path=[]):
    return ConfigDict( read_config(fn, 'parameters', search_path) )
#-------------------------------------------------------------------------------
def read_ip_config(fn, param_sect, search_path=[]):

    cfg_params = read_config(fn, param_sect, search_path)
    
    with open( search_file(fn) ) as f:
        cfg = yaml.safe_load(f)
        
    ip_cfg = {}
    ip_cfg['type']     = cfg['type']
    ip_cfg[param_sect] = cfg_params
        
    return ip_cfg

#-------------------------------------------------------------------------------
def read_src_list(fn: str, search_path=[]):

    path = search_file(fn, search_path)
    
    with open( path ) as f:
        cfg = yaml.safe_load(f)
    
    if 'parameters' in cfg:
        params = read_config(fn, 'parameters', search_path)
    
    if cfg:
        usedin = 'syn'
        if 'usedin' in cfg:
            usedin = cfg['usedin']
           
        flist = [] 
        for i in cfg['sources']:
            p = re.search('\$(\w+)', i)
            if p:
                fpath = p.group(1)
                if fpath in params:
                    if params[fpath]:
                        flist.append(i.replace('$' + fpath, params[fpath]))
                else:
                    print_error('E: undefined substitution parameter "' + fpath + '"')
                    print_error('    File: ' + path )
                    Exit(-2)
            else:
                flist.append(i)
                
        return flist, usedin, path
    else:
        return [], '', path
    
#-------------------------------------------------------------------------------
#
#    args[0] is always config file name (yaml)
#    args[1], if specified, forces return 'usedin' attribute
#
def read_sources(fn, search_path='', get_usedin = False):
    
    #prefix_path = [search_path, os.getcwd()] + get_search_path() + [os.path.abspath(str(Dir('#')))]
    spath = pathlist(search_path)
    prefix_path = spath + [Path.cwd()] + get_search_path() + [Path(str(Dir('#'))).absolute()]
    src, usedin, fn_path = read_src_list(fn, search_path)
    
    prefix_path =  list(dict.fromkeys(prefix_path))
    
#   print('--------> spath <-----------')
#   for ii in spath:
#       print('++++', ii)
#
#   print('--------> get_search_path() <-----------')
#   for ii in get_search_path():
#       print('====', ii)
#
#   print('--------> Dir(\'#\') <-----------')
#   print('#####', Path(str(Dir('#'))).absolute())
#
#   print('--------> prefix_path <-----------')

#   for ppp in prefix_path:
#       print(ppp)

#   print(os.linesep*2)
    
    path_list = []
    if src:
        for s in src:
            path_exists = False
            for pp in prefix_path:
                #path = os.path.abspath( os.path.join(pp, s) )
                path = pp.joinpath(s).absolute()
                #if os.path.exists(path):
                if path.exists():
                    path_list.append(str(path)) # convert to string list due to SCons.Node cannot correctly work with 'pathlib' objects
                    path_exists = True
                    break
            
            if not path_exists:
                ignore = False
                for exdir in check_exclude_path:
                    if exdir in s:
                        ignore = True
                        break
                    
                if not ignore:
                    print_error('E: file at relative path "' + s + '" does not exists')
                    print_error('    detected while processing "' + fn_path +'"')
                    #print(prefix_path)
                    Exit(-1)
            
    if get_usedin:
        return path_list, usedin  
    else:
        return path_list

#-------------------------------------------------------------------------------
def get_dirs(flist):
    #dset = set( [os.path.dirname(f) for f in flist] )
    dset = set( [str(Path(f).parent) for f in flist] )
    
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
    #return os.path.splitext(path)[1][1:]
    return Path(path).suffix[1:]

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
    #name = os.path.split(path)[1]
    #ip_name = name.replace(suffix, '')
    ip_name = Path(path).name.replace(suffix, '')
    
    return ip_name

#-------------------------------------------------------------------------------
def get_name(path):
    #return os.path.splitext( os.path.basename(path) )[0]
    return Path(path).stem
#-------------------------------------------------------------------------------
def drop_suffix(name):
    #return os.path.splitext(name)[0]
    return Path(name).stem
#-------------------------------------------------------------------------------
def create_dirs(dirs):
    for i in dirs:
        #if not os.path.exists(i):
        if not Path(i).exists():
            Execute( Mkdir(i) )
    
#-------------------------------------------------------------------------------

