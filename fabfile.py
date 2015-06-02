from fabric.api import local,parallel
from fabric.colors import blue, cyan, green, magenta, red, white, yellow
from paver.easy import path
from functools import partial
from coffeescript import compile as compile_coffee
from jsmin import jsmin
from uglipyjs import compile as _uglifyjs
import os
from bcrypt import hashpw, gensalt
import sqlalchemy as sa
from sqlalchemy.sql.expression import column,table

def _error(text):
    return red(text)

def _info(text):
    return white(text)

def _print(arg,*args,**kwargs):
    print arg
    print (args or '')
    print (kwargs or '')

_error = lambda text: red(text)
_info = lambda text: white(text)
_write = lambda data,name:open(name,'w').write(data)
_process_data = lambda func,data,write_out=None,filename=None,*args,**kwargs: _write(func(data,*args,**kwargs),filename) if write_out else func(data,*args,**kwargs)
_coffee = partial(_process_data,compile_coffee)
_jsmin = partial(_process_data,jsmin)
_uglify = partial(_process_data,_uglifyjs)
PATH_FUNC = lambda dirname,recurse=None: list(path(dirname).files()) if not recurse else list(path(dirname).walkfiles())
_clean = lambda dirname,ext,recurse=False: (map(lambda x: (os.remove(str(x)) or _error('deleted {}'.format(str(x)))),[x for x in PATH_FUNC(dirname,recurse) if (ext and x.endswith(ext))]))



@parallel
def clean(name,verbose=False):
    if verbose:
        print 'running clean'
    name = name if name.endswith('.js') else name + '.js'
    if os.path.exists(name):
        local('rm {}'.format(name))

@parallel
def get_file(name,ext,verbose=False):
    if verbose:
        print 'running get_file'
    name = name if name.endswith(ext) else '{}.{}'.format(name,ext)
    return open(name,'r').read()

def coffee(data,write_out=False,filename=None,verbose=False):
    if verbose:
        print 'compiliing coffeescript'
    c = compile_coffee(data,bare=True)
    if (not write_out and filename is None):
        return c
    else:
        with open(filename,'w') as f:
            f.write(c)

def minify(data,write_out=False,filename=None,verbose=False):
    if verbose:
        print 'running minify'
    data = jsmin(data)
    if write_out and filename:
        _write(data,filename)
        return True
    return data

def uglify(data,write_out=False,filename=None,verbose=False):
    if verbose:
        print 'running uglify'
    data = _uglify(data)
    if write_out and filename:
        _write(data,filename)
        return True
    return data

def ng_annotate(data,write_out=False,filename=None,verbose=False):
    if verbose:
        print 'running ng-annotate'
    with open('tmp.js','w') as f:
        f.write(data)
    local('ng-annotate -a tmp.js > {0}'.format(write_out and filename or 'tmp2.js'))
    local('rm tmp.js')
    if not (write_out and filename):
        data = open('tmp2.js','r').read()
        local('rm tmp2.js')
        return data
    else:
        print 'wrote {} to file'.format(filename)
    return True

BUILD_TYPES = dict(
        DEV='dev',
        PROD='prod',
)

def process_files(file_list,build=BUILD_TYPES['DEV'],verbose=False):
    ext = file_list[0].split('.')[-1]
    data_store = None
    if build == BUILD_TYPES['PROD']:
        data_store = []
    for name in map(lambda x: os.path.splitext(x)[0],file_list):
        clean(name,verbose)
        data = get_file(name,ext,verbose=verbose)
        data = coffee(data,verbose=verbose)
        if build == BUILD_TYPES['DEV']:
            data = ng_annotate(data,True,'{}.{}'.format(name,'js'),verbose=verbose)
        else:
            data = ng_annotate(data,verbose=verbose)
            data = minify(data,verbose=verbose)
            data = uglify(data,verbose=verbose)
            data_store.append(data)
    if data_store is not None:
        if verbose:
            print 'running concat'
        with open('main.min.js','w') as f:
            for d in data_store:
                f.write(d)

        print 'wrote all files to main.min.js'

def p_js(build='prod',verbose=False):
    file_list = [
        'new.coffee',
        'auth.coffee'
    ]
    process_files(file_list,build,verbose)
    local('honcho start')

@parallel
def process_js(name):
    local('coffee -p -b {0}.coffee | ng-annotate -a - > {0}.js'.format(name))
