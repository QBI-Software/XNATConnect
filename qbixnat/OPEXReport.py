# -*- coding: utf-8 -*-
"""
Utility script: OPEXReport

run from console/terminal with (example):
>python OPEXReport.py --filedir "data" --sheet "Sheetname_to_extract"

Created on Thu Mar 2 2017

@author: Liz Cooper-Williams, QBI
"""

import argparse
import glob
import re
from datetime import datetime
from os import R_OK, access
from os.path import join, basename, splitext

import pandas
import numpy as np
import matplotlib.mlab as mlab
import matplotlib.pyplot as plt
from os.path import expanduser


class OPEXReport(object):

    def __init__(self, subjects):
        self.subjects = subjects #collection from pyxnat
        self.participants = None #dataframe of participant data

    def showParticipants(self):
        ids = [(s.label(), s.attrs.get('gender'), s.attrs.get('dob'), s.attrs.get('group')) for s in self.subjects]
        self.participants = pandas.DataFrame(ids, columns=['ID', 'GENDER', 'DOB', 'Group'])

    def validateSubjectIDs(self):

        if self.participants is None:
            ids = [s.label() for s in self.subjects]
        else:
            ids = self.participants['ID']
        #check for duplicate numbers
        pattern = '(\d{4})'
        for sid in ids:
            m = re.match(pattern, sid)
            strippedids = int(m.group(0))

    def formatDobNumber(self,orig):
        """
        Reformats DOB string from Excel data float to yyyy-mm-dd
        """
        dateoffset = 693594
        dt = datetime.fromordinal(dateoffset + int(orig))
        return dt.strftime("%Y-%m-%d")

########################################################################

if __name__ == "__main__":
    from qbixnat.XnatConnector import XnatConnector #Only for testing
    home = expanduser("~")
    configfile = join(home, '.xnat.cfg')
    database = 'xnat-dev'
    projectcode = 'TESTPJ00'
    xnat = XnatConnector(configfile, database)
    print "Connecting to URL=", xnat.url
    xnat.connect()
    if (xnat.conn):
        print "...Connected"
        subjects = xnat.get_subjects(projectcode)
        op = OPEXReport(subjects)
        op.showParticipants()
        op.validateSubjects()

        xnat.conn.disconnect()
        print("FINISHED")

    else:
        print "Failed to connect"
