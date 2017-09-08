import sys

path = '/mypath/site'
if path not in sys.path:
   sys.path.append(path)

from OPEXReportApp import OPEXReportApp.main as application