"""
Module responsible for the creation of the json files containing the default configuration for each available compiler.
This module only needs to be imported once. Once the json files have been generated they can be used directly thus
avoiding the need for a large number of imports
"""
import json
import os
import sys
import sysconfig
from itertools import chain
from numpy import get_include as get_numpy_include
from pyccel import __version__ as pyccel_version

gfort_info = {'exec' : 'gfortran',
              'mpi_exec' : 'mpif90',
              'language': 'fortran',
              'module_output_flag': '-J',
              'debug_flags': ("-fcheck=bounds",),
              'release_flags': ("-O3",),
              'general_flags' : ('-fPIC',),
              'standard_flags' : ('-std=f2003',),
              'mpi': {
                  },
              'openmp': {
                  'flags' : ('-fopenmp',),
                  'libs'  : ('gomp',),
                  },
              'openacc': {
                  'flags' : ("-ta=multicore", "-Minfo=accel"),
                  },
              'family': 'GNU',
              }
if sys.platform == "win32":
    gfort_info['mpi']['flags'] = ('-D','USE_MPI_MODULE')
    gfort_info['mpi']['includes'] = (os.environ["MSMPI_INC"].rstrip('\\'),)
    gfort_info['mpi']['libs'] = (os.environ["MSMPI_LIB64"].rstrip('\\'),)
    gfort_info['mpi']['dependencies'] = (os.path.join(os.environ["MSMPI_LIB64"], 'libmsmpi.a'),)

#------------------------------------------------------------
ifort_info = {'exec' : 'ifort',
              'mpi_exec' : 'mpiifort',
              'language': 'fortran',
              'module_output_flag': '-module',
              'debug_flags': ("-check=bounds",),
              'release_flags': ("-O3",),
              'general_flags' : ('-fPIC',),
              'standard_flags' : ('-std=f2003',),
              'openmp': {
                  'flags' : ('-fopenmp','-nostandard-realloc-lhs'),
                  'libs'  : ('iomp5',),
                  },
              'openacc': {
                  'flags' : ("-ta=multicore", "-Minfo=accel"),
                  },
              'family': 'intel',
              }
#------------------------------------------------------------
gcc_info = {'exec' : 'gcc',
            'mpi_exec' : 'mpicc',
            'language': 'c',
            'debug_flags': ("-g",),
            'release_flags': ("-O3",),
            'general_flags' : ('-fPIC',),
            'standard_flags' : ('-std=c99',),
            'openmp': {
                'flags' : ('-fopenmp',),
                'libs'  : ('gomp',),
                },
            'openacc': {
                'flags' : ("-ta=multicore", "-Minfo=accel"),
                },
            'family': 'GNU',
            }
if sys.platform == "darwin":
    gcc_info['openmp']['flags'] = ("-Xpreprocessor",'fopenmp')
    gcc_info['openmp']['libs'] = ('omp',)

#------------------------------------------------------------
icc_info = {'exec' : 'icc',
            'mpi_exec' : 'mpiicc',
            'language': 'c',
            'debug_flags': ("-g",),
            'release_flags': ("-O3",),
            'general_flags' : ('-fPIC',),
            'standard_flags' : ('-std=c99',),
            'openmp': {
                'flags' : ('-fopenmp',),
                },
            'openacc': {
                'flags' : ("-ta=multicore", "-Minfo=accel"),
                },
            'family': 'intel',
            }
#------------------------------------------------------------
config_vars = sysconfig.get_config_vars()
print(json.dumps(config_vars, indent=4))
linker_flags = config_vars.get("BLDLIBRARY","").split()+config_vars.get("LDSHARED","").split()
python_info = {
        "libs" : config_vars.get("LIBM","").split(), # Strip -l from beginning
        "libdirs" : config_vars.get("LIBDIR","").split(),
        'python': {
            'flags' : config_vars.get("CFLAGS","").split()\
                + config_vars.get("CC","").split()[1:],
            'includes' : [*config_vars.get("INCLUDEPY","").split(), get_numpy_include()],
            'libs' : [l for l in linker_flags if l.startswith('-l')],
            'libdirs' : [l for l in linker_flags if l.startswith('-L')]+config_vars.get("LIBPL","").split(),
            "linker_flags" : [l for l in linker_flags if not l.startswith('-l') and not l.startswith('-L')],
            "shared_suffix" : config_vars.get("EXT_SUFFIX",".so"),
            }
        }
if sys.platform == "win32":
    python_info['python']['linker_flags'].append('-shared')
    python_info['python']['libs'].append('python{}'.format(config_vars["VERSION"]))
    python_info['python']['libdirs'].extend(config_vars.get("installed_base","").split())

#------------------------------------------------------------
save_folder = os.path.dirname(os.path.abspath(__file__))

#------------------------------------------------------------
def print_json(filename, info):
    """
    Print the json file described by info into the specied file

    Parameters
    ----------
    filename : str
               The name of the json file where the configuration information
               will be saved
    info     : dict
               A dictionary containing information about the flags, libraries, etc
               associated with a given compiler
    """
    print(json.dumps(dict(chain(info.items(),
                                python_info.items(),
                                [('pyccel_version', pyccel_version)])),
                     indent=4))
    print(json.dumps(dict(chain(info.items(),
                                python_info.items(),
                                [('pyccel_version', pyccel_version)])),
                     indent=4),
          file=open(os.path.join(save_folder, filename),'w'))

#------------------------------------------------------------
def generate_default():
    """
    Generate the json files containing the default configurations for the
    available compilers
    """
    files = {
            'gfortran.json' : gfort_info,
            'gcc.json'      : gcc_info,
            'ifort.json'    : ifort_info,
            'icc.json'      : icc_info
            }
    for f, d in files.items():
        print_json(f,d)
    return files.keys()
