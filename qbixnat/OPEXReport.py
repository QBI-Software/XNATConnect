# -*- coding: utf-8 -*-
"""
Utility script: OPEXReport

run from console/terminal with (example):
>python OPEXReport.py --filedir "data" --sheet "Sheetname_to_extract"

Created on Thu Mar 2 2017

@author: Liz Cooper-Williams, QBI
"""

from datetime import datetime
from os.path import expanduser
from os.path import join

import numpy as np
import pandas

from qbixnat.CantabParser import CantabParser


class OPEXReport(object):

    def __init__(self, subjects):
        """
        List of subjects from XNAT as collection
        :param subjects:
        """
        self.subjects = subjects


    def getParticipants(self):
        """
        Get Number of participants grouped by Group and Gender
        :return:
        """
        groups = pandas.DataFrame([(s.attrs.get('group'), s.attrs.get('gender')) for s in self.subjects], columns=['group','gender'])
        #Set up frequency histogram
        df = groups.groupby('group').count()
        df_male = groups.groupby(['gender']).get_group('male')
        df_female = groups.groupby(['gender']).get_group('female')
        df['Male'] = df_male.groupby('group').count()
        df['Female'] = df_female.groupby('group').count()
        df = df.rename(columns={'gender': 'All'})
        dg = df['All']._construct_axes_dict() #workaround
        df['Group'] = dg['index']
        df.replace(to_replace=np.nan, value=0, inplace=True)
        return df


    def getMultivariate(self, expts):
        """
        List of expts from XNAT as collection
        :param expts:
        :return:
        """
        expts = pandas.DataFrame([e for e in expts])
        expts

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
    projectcode = 'TEST_PJ00'
    xnat = XnatConnector(configfile, database)
    print "Connecting to URL=", xnat.url
    xnat.connect()
    if (xnat.conn):
        print "...Connected"
        subjects = xnat.get_subjects(projectcode)
        op = OPEXReport(subjects)
       # df = op.getParticipants()
        proj = xnat.get_project(projectcode)
        cantab = CantabParser("resources\\cantab_fields.csv", None)
        for xsd in cantab.getxsd():
            expts = proj.experiments(xsd + "*")  # prefix of labels/ids
            teste = expts.fetchone()
            if (teste is not None):
                df_baseline = cantab.getDFExpts(expts, '0',xsd)
                print(df_baseline)
            else:
                print('No expts found for:', xsd)


        xnat.conn.disconnect()
        print("FINISHED")

    else:
        print "Failed to connect"
