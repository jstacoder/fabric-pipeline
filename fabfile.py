from fabric.api import local,parallel
from coffeescript import compile as compile_coffee
from jsmin import jsmin
from uglipyjs import compile as _uglify
import os
from bcrypt import hashpw, gensalt
import sqlalchemy as sa
from sqlalchemy.sql.expression import column,table
from appdb import Model,User,Email,Project,Document

pw = lambda data: hashpw(data,gensalt())

def _print(arg,*args,**kwargs):
    print arg
    print (args or '')
    print (kwargs or '')

_id_by_name = lambda name: User.query.filter(
                                User.username == name
                            ).first().id

def seed_db():
    Model.metadata.bind = Model.engine
    Model.metadata.bind.execute(
            User.__table__.insert().values([
                dict(
                    username='jstacoder',_password_hash=pw('jstacoder')
                ),
                dict(
                    username='jessicarrr',_password_hash=pw('jessicarrr')
                ),
            ])
    )
    users = [
        _id_by_name('jstacoder'),
        _id_by_name('jessicarrr')
    ]
    Project(name='projA',users=users).save()
    Project(name='projB',users=users).save()
    Project(name='projC',users=[users[0]]).save()
    Project(name='projD',users=[users[1]]).save()
    Email(address='jstacoder@gmail.com',user_id=_id_by_name('jstacoder')).save()
    Email(address='jessicarrr@gmail.com',user_id=_id_by_name('jessicarrr')).save()



def _write(data,name):
    with open(name,'w') as f:
        f.write(data)
    return True

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
    return True

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
