'''
    QBI OPEX XNAT Uploader APP: setup.py (Windows 64bit MSI)
    *******************************************************************************
    Copyright (C) 2017  QBI Software, The University of Queensland

    This program is free software; you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation; either version 2 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.
'''
#
# Step 1. Build first
#   python setup.py build
# View build dir contents
# Step 2. Create MSI distribution (Windows)
#   python setup.py bdist_msi
# View dist dir contents
####
# Issues with scipy and cx-freeze -> https://stackoverflow.com/questions/32432887/cx-freeze-importerror-no-module-named-scipy
# 1. changed cx_Freeze/hooks.py scipy.lib to scipy._lib (line 560)
#then run setup.py build
# 2. changed scipy/spatial cKDTree.cp35-win_amd64.pyd to ckdtree.cp35-win_amd64.pyd

# test with exe
# then run bdist_msi

application_title = 'QBI OPEX XNAT Uploader'
main_python_file = 'OPEXUploaderGUI.py'

import os
import sys
import shutil
from os.path import join

from cx_Freeze import setup, Executable


venvpython = 'D:\\Projects\\XNAT\\scripts\\xnatpyenv\\Lib\\site-packages'
mainpython = 'D:\\Programs\\Python27\\python-2.7.10.amd64'

os.environ['TCL_LIBRARY'] = join(mainpython, 'tcl', 'tcl8.5')
os.environ['TK_LIBRARY'] = join(mainpython, 'tcl', 'tk8.5')
base = None
if sys.platform == 'win32':
    base = 'Win32GUI'

build_exe_options = {
    'includes': ['idna.idnadata', "numpy", "pkg_resources"],
    'excludes': ['PyQt4', 'PyQt5'],
    'packages': ['numpy.core._methods', 'numpy.lib.format'],
    'include_files': [join(os.getcwd(),'qbixnat','gui','noname.py'), 'resources/',
                      join(mainpython, 'DLLs', 'tcl85.dll'),
                      join(mainpython, 'DLLs', 'tk85.dll')],
    'include_msvcr': 1
}
# [Bad fix but only thing that works] NB To add Shortcut working dir - change cx_freeze/windist.py Line 61 : last None - > 'TARGETDIR'
setup(
    name=application_title,
    version='1.1.5',
    description='QBI OPEX XNAT Uploader',
    long_description=open('README.md').read(),
    author='Liz Cooper-Williams, QBI',
    author_email='e.cooperwilliams@uq.edu.au',
    maintainer='QBI Custom Software, UQ',
    maintainer_email='qbi-dev-admin@uq.edu.au',
    url='http://github.com/QBI-Software/XNATConnect',
    license='GNU General Public License (GPL)',
    options={'build_exe': build_exe_options, },
    executables=[Executable(main_python_file, base=base, targetName='opexuploader.exe', icon='resources/upload_logo.ico',
                            shortcutName=application_title, shortcutDir='DesktopFolder')]
)

#Rename ckdtree
# shutil.move('build\\exe.win-amd64-3.5\\scipy\\spatial\\cKDTree.cp35-win_amd64.pyd', 'build\\exe.win-amd64-3.5\\scipy\\spatial\\ckdtree.pyd')
# shutil.copyfile('build\\exe.win-amd64-3.5\\scipy\\spatial\\ckdtree.pyd', 'build\\exe.win-amd64-3.5\\scipy\\spatial\\ckdtree.cp35-win_amd64.pyd')