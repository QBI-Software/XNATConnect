import argparse
import glob
import logging
import os
import sys
import re
import numpy as np
from datetime import datetime
from os import R_OK, access
from os.path import expanduser
from os.path import isdir, join
from requests.exceptions import ConnectionError
from qbixnat.CantabParser import CantabParser
from qbixnat.AmunetParser import AmunetParser
from qbixnat.AcerParser import AcerParser
from qbixnat.XnatConnector import XnatConnector


class OPEXUploader():
    def __init__(self, args):
        logging.basicConfig(filename='xnatupload.log', level=logging.INFO, format='%(asctime)s %(message)s',
                            datefmt='%d-%m-%Y %I:%M:%S %p')
        self.args = args
        self.configfile = None
        self.xnat = None

    def config(self):
        # get current user's login details (linux) or local file (windows)
        home = expanduser("~")
        configfile = join(home, '.xnat.cfg')
        if self.args.config is not None:
            try:
                os.access(self.args.config, os.R_OK)
                configfile = self.args.config
            except:
                raise IOError
        try:
            os.access(configfile, os.R_OK)
            self.configfile = configfile
        except:
            raise os.error
            sys.exit(1)

    def xnatconnect(self):
        self.xnat = XnatConnector(self.configfile, self.args.database)
        self.xnat.connect()

    def xnatdisconnect(self):
        self.xnat.conn.disconnect()

    def loadSampledata(self,subject, samplexsd, sampleid, sampledata):
        """ Loads sample data from CANTAB data dump
        Check if already exists - don't overwrite (allows for cumulative data files to be uploaded)
        :param cantabid: ID for this row of CANTAB data
        :param i: row number of dataset
        :param row: row as pandas series with data
        :param subject: subject to add experiment to
        :return: msg for logging
        """
        expt = subject.experiment(sampleid)
        if not expt.exists():
            self.xnat.createExperiment(subject, samplexsd, sampleid, sampledata)
            msg = 'Experiment created:' + sampleid
        else:
            msg = 'Experiment already exists: ' + sampleid
        return msg


    def loadAMUNETdata(self,cantabid,row,subject, amparser):
        """ Loads AMUNET sample data from data dump
        Check if already exists - don't overwrite (allows for cumulative data files to be uploaded)
        :param cantabid: ID for this row of data
        :param i: row number of dataset
        :param row: row as pandas series with data
        :param subject: subject to add experiment to
        :return: msg for logging
        """
        motid = cantabid
        expt = subject.experiment(motid)
        motxsd = amparser.getXsd()

        if not expt.exists():

            #two files with different columns merged to one
            if 'AEV_Average total error' in row:
                motdata = amparser.mapAEVdata(row)
            else:
                motdata = amparser.mapSCSdata(row)
            self.xnat.createExperiment(subject, motxsd, motid, motdata)
            msg = 'Amunet experiment created:' + motid

        elif (len(expt.xpath('opex:AEV')) > 0 and len(expt.xpath('opex:SCS')) == 0 and 'SCS_Average total error' in row):  # loaded AEV data but not SCS

            e1 = expt
            motdata = amparser.mapSCSdata(row)
            e1.attrs.mset(motdata)
            msg = 'Amunet experiment updated with SCS: '+ motid

        elif(len(expt.xpath('opex:SCS')) > 0 and len(expt.xpath('opex:AEV')) == 0 and 'AEV_Average total error' in row):  # loaded SCS data but not AEV
            e1 = expt
            motdata = amparser.mapAEVdata(row)
            e1.attrs.mset(motdata)
            msg = 'Amunet experiment updated with AEV: '+ motid
        else:
            msg = 'Amunet experiment already exists: ' + motid
        return msg


########################################################################
if __name__ == "__main__":

    parser = argparse.ArgumentParser(prog='OPEX Uploader',
                                     description='''\
        Script for uploading scans and sample data to QBI OPEX XNAT db
         ''')
    parser.add_argument('database', action='store', help='select database config from xnat.cfg to connect to')
    parser.add_argument('projectcode', action='store', help='select project by code')
    parser.add_argument('--projects', action='store_true', help='list projects')
    parser.add_argument('--subjects', action='store_true', help='list subjects')
    parser.add_argument('--g', action='store', help='get XNAT ID for subject ID')
    parser.add_argument('--config', action='store', help='database configuration file (overrides ~/.xnat.cfg)')
    parser.add_argument('--cantab', action='store', help='Upload CANTAB data from directory')
    parser.add_argument('--skiprows', action='store_true', help='Skip rows in CANTAB data if NOT_RUN or ABORTED')
    parser.add_argument('--amunet', action='store', help='Upload Water Maze (Amunet) data from directory')
    parser.add_argument('--acer', action='store', help='Upload ACER data from directory')
    parser.add_argument('--create', action='store_true', help='Create Subject from input data if not exists')
    parser.add_argument('--u', action='store',
                        help='Upload MRI scans from directory with data/subject_label/scans/session_label/[*.dcm|*.IMA]')
    args = parser.parse_args()
    uploader = OPEXUploader(args)
    uploader.config()
    uploader.xnatconnect()
    logging.info('Connecting to Server:%s Project:%s', uploader.args.database, uploader.args.projectcode)

    try:
        testconn = uploader.xnat.conn.inspect.datatypes('xnat:subjectData')
        if len(testconn) > 0:
            logging.info("...Connected")
            print("Connected")
            #Check project code is correct
            projectcode = uploader.args.projectcode
            p = uploader.xnat.get_project(projectcode)
            if (not p.exists()):
                msg = "This project [%s] does not exist in this database [%s]" % (projectcode, uploader.args.database)
                raise ConnectionError(msg)
            if (uploader.args.subjects is not None and uploader.args.subjects):
                logging.info("Calling List Subjects")
                uploader.xnat.list_subjects_all(projectcode)
            if (uploader.args.projects is not None and uploader.args.projects):
                logging.info("Calling List Projects")
                projlist = uploader.xnat.list_projects()
                for p in projlist:
                    print("Project: ", p.id())
            if (uploader.args.g is not None and uploader.args.g):
                subjectid = uploader.args.g
                sid = uploader.xnat.get_subjectid_bylabel(projectcode, subjectid)
                print("XNAT ID=%s for subject ID=%s" % (sid, subjectid))
            if (uploader.args.u is not None and uploader.args.u):
                uploaddir = uploader.args.u  # Top level DIR FOR SCANS
                # Directory structure data/subject_label/scans/session_id/*.dcm
                if isdir(uploaddir):
                    fid = uploader.xnat.upload_MRIscans(projectcode, uploaddir)
                    if fid == 0:
                        msg = 'Upload not successful - 0 sessions uploaded'
                        raise ValueError(msg)
                    else:
                        logging.info("Subject sessions uploaded: %d", fid)
                else:
                    msg = "Directory path cannot be found: %s" % uploaddir
                    raise IOError(msg)
            if (uploader.args.cantab is not None and uploader.args.cantab):
                sheet = "RowBySession_HealthyBrains"
                inputdir = uploader.args.cantab
                print("Input:", inputdir)
                if access(inputdir, R_OK):
                    seriespattern = '*.*'
                    try:
                        files = glob.glob(join(inputdir, seriespattern))
                        print("Files:", len(files))
                        project = uploader.xnat.get_project(projectcode)
                        for f2 in files:
                            print("Loading", f2)
                            cantab = CantabParser(f2, sheet)
                            cantab.sortSubjects()

                            for sd in cantab.subjects:
                                print('ID:', sd)
                                s = project.subject(sd)
                                if not s.exists():
                                    if uploader.args.create is not None and uploader.args.create:
                                        #create subject in database
                                        skwargs = cantab.getSubjectData(sd)
                                        s = uploader.xnat.createSubject(projectcode,sd, skwargs)
                                        logging.info('Subject created: ' + sd)
                                        print('Subject created: ' + sd)
                                    else:
                                        logging.warning('Subject does not exist - skipping:' + sd)
                                        continue
                                #Load data PER ROW
                                for i, row in cantab.subjects[sd].iterrows():
                                    if uploader.args.skiprows is not None and uploader.args.skiprows and str(row['DMS Recommended Standard Status']) in ['NOT_RUN', 'ABORTED']:
                                        continue
                                    row.replace(np.nan, '', inplace=True)
                                    cantabid = cantab.getSampleid(sd, row)
                                    print(i, 'Visit:', row['Visit Identifier'], 'EXPT ID', cantabid)
                                    #Sample
                                    data = cantab.mapMOTdata(row, i)
                                    xsd = cantab.getMOTxsd()
                                    msg = uploader.loadSampledata(s, xsd, "MOT_" + cantabid, data)
                                    logging.info(msg)
                                    print(msg)
                                    data = cantab.mapPALdata(row, i)
                                    xsd = cantab.getPALxsd()
                                    msg = uploader.loadSampledata(s, xsd, "PAL_" + cantabid, data)
                                    logging.info(msg)
                                    print(msg)
                                    data = cantab.mapDMSdata(row, i)
                                    xsd = cantab.getDMSxsd()
                                    msg = uploader.loadSampledata(s, xsd, "DMS_" + cantabid, data)
                                    logging.info(msg)
                                    print(msg)
                                    data = cantab.mapSWMdata(row, i)
                                    xsd = cantab.getSWMxsd()
                                    msg = uploader.loadSampledata(s, xsd, "SWM_" + cantabid, data)
                                    logging.info(msg)
                                    print(msg)

                    except:
                        e = sys.exc_info()[0]
                        raise ValueError(e)

                else:
                    msg = "Access to data directory is denied: %s" % inputdir
                    raise ConnectionError(msg)
            ###Amunet data
            if (uploader.args.amunet is not None and uploader.args.amunet):
                sheet = "1"
                inputdir = uploader.args.amunet
                print("Input:", inputdir)
                if access(inputdir, R_OK):
                    seriespattern = '*.*'
                    try:
                        files = glob.glob(join(inputdir, seriespattern))
                        print("Files:", len(files))
                        project = uploader.xnat.get_project(projectcode)
                        for f2 in files:
                            print("Loading", f2)
                            cantab = AmunetParser(f2, sheet)
                            cantab.sortSubjects()

                            for sd in cantab.subjects:
                                print('ID:', sd)
                                s = project.subject(sd)
                                if not s.exists():
                                    if uploader.args.create is not None and uploader.args.create:
                                        #create subject in database
                                        skwargs = cantab.getSubjectData(sd)
                                        s = uploader.xnat.createSubject(projectcode,sd, skwargs)
                                        logging.info('Subject created: ' + sd)
                                        print('Subject created: ' + sd)
                                    else:
                                        logging.warning('Subject does not exist - skipping:' + sd)
                                        continue
                                #Load data PER ROW
                                for i, row in cantab.subjects[sd].iterrows():
                                    cantabid = cantab.getSampleid(sd,row)
                                    print(i, 'Visit:', row['S_Visit'], 'EXPT ID', cantabid)
                                    row.replace(np.nan,'', inplace=True)
                                    msg = uploader.loadAMUNETdata(cantabid,row,s,cantab)
                                    logging.info(msg)
                                    print(msg)

                    except:
                        e = sys.exc_info()[0]
                        raise ValueError(e)
                else:
                    raise IOError(msg)

            ###ACE-R data
            if (uploader.args.acer is not None and uploader.args.acer):
                sheet = "1"
                inputdir = uploader.args.acer
                print("Input:", inputdir)
                if access(inputdir, R_OK):
                    seriespattern = '*.*'
                    try:
                        files = glob.glob(join(inputdir, seriespattern))
                        print("Files:", len(files))
                        project = uploader.xnat.get_project(projectcode)
                        for f2 in files:
                            print("Loading", f2)
                            cantab = AcerParser(f2, sheet)
                            cantab.sortSubjects()

                            for sd in cantab.subjects:
                                print('ID:', sd)
                                s = project.subject(sd)
                                if not s.exists():
                                    if uploader.args.create is not None and uploader.args.create:
                                        # create subject in database
                                        skwargs = cantab.getSubjectData(sd)
                                        s = uploader.xnat.createSubject(projectcode, sd, skwargs)
                                        logging.info('Subject created: ' + sd)
                                        print('Subject created: ' + sd)
                                    else:
                                        logging.warning('Subject does not exist - skipping:' + sd)
                                        continue
                                # Load data PER ROW
                                for i, row in cantab.subjects[sd].iterrows():
                                    cantabid = cantab.getSampleid(sd, row)
                                    print(i, 'EXPT ID', cantabid)
                                    row.replace(np.nan, '', inplace=True)
                                    data = cantab.mapData(row, i)
                                    xsd = cantab.getXsd()
                                    msg = uploader.loadSampledata(s, xsd, "AC_" + cantabid, data)
                                    logging.info(msg)
                                    print(msg)

                    except:
                        e = sys.exc_info()[0]
                        raise ValueError(e)
                else:
                    raise IOError(msg)

        else:
            raise ConnectionError("Connection failed - check config")
    except IOError as e:
        logging.error("Failed IO:"+ e.message)
        print "Failed IO:", e.message
    except ConnectionError as e:
        logging.error("Failed connection:"+ e.message)
        print "Failed connection:", e.message
    except ValueError as e:
        logging.error("Failed processing:"+ e.message)
        print "Failed connection:", e.message
    finally:
        #Processing complete
        uploader.xnatdisconnect()
        logging.info("FINISHED")
        print("FINISHED - see xnatupload.log for details")

