import argparse
import glob
import logging
import os
import sys
import csv
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



    def loadSampledata(self,subject, samplexsd, sampleid, mandata,sampledata):
        """ Loads sample data from CANTAB data dump
        Check if already exists - don't overwrite (allows for cumulative data files to be uploaded)
        :param sampleid: ID for this row of CANTAB data
        :param i: row number of dataset
        :param row: row as pandas series with data
        :param subject: subject to add experiment to
        :return: msg for logging
        """
        expt = subject.experiment(sampleid)
        if not expt.exists():
            self.xnat.createExperiment(subject, samplexsd, sampleid, mandata,sampledata)
            msg = 'Experiment created:' + sampleid
        else:
            msg = 'Experiment already exists: ' + sampleid
        return msg


    def loadAMUNETdata(self,sampleid,i,row,subject, amparser):
        """ Loads AMUNET sample data from data dump
        Data is combined from two source files
        Check if expt already exists - don't overwrite (allows for cumulative data files to be uploaded)
        :param sampleid: ID for this row of data
        :param i: row number of dataset
        :param row: row as pandas series with data
        :param subject: subject to add experiment to
        :return: msg for logging
        """
        motid = sampleid
        motxsd = amparser.getxsd()
        expt = subject.experiment(motid)

        if not expt.exists():
            #two files with different columns merged to one
            if 'AEV_Average total error' in row:
                (mandata,motdata) = amparser.mapAEVdata(row,i)
            else:
                (mandata, motdata) = amparser.mapSCSdata(row,i)
            self.xnat.createExperiment(subject, motxsd, motid, mandata,motdata)
            msg = 'Amunet experiment created:' + motid

        elif (len(expt.xpath('opex:AEV')) > 0 and len(expt.xpath('opex:SCS')) == 0 and 'SCS_Average total error' in row):  # loaded AEV data but not SCS
            e1 = expt
            (mandata, motdata) = amparser.mapSCSdata(row,i)
            e1.attrs.mset(motdata)
            msg = 'Amunet experiment updated with SCS: '+ motid

        elif(len(expt.xpath('opex:SCS')) > 0 and len(expt.xpath('opex:AEV')) == 0 and 'AEV_Average total error' in row):  # loaded SCS data but not AEV
            e1 = expt
            (mandata, motdata) = amparser.mapAEVdata(row,i)
            e1.attrs.mset(motdata)
            msg = 'Amunet experiment updated with AEV: '+ motid
        else:
            msg = 'Amunet experiment already exists: ' + motid
        return msg


    def uploadData(self,project,dp):
        """
        Upload data via specific Data parser
        :param dp:
        :return: missing and matches
        """
        missing=[]
        matches=[]
        dp.sortSubjects()
        for sd in dp.subjects:
            print('ID:', sd)
            s = project.subject(sd)
            if not s.exists():
                if self.args.create is not None and self.args.create:
                    # create subject in database
                    skwargs = dp.getSubjectData(sd)
                    s = self.xnat.createSubject(projectcode, sd, skwargs)
                    logging.info('Subject created: ' + sd)
                    print('Subject created: ' + sd)
                else:
                    missing.append({"ID": sd, "rows": dp.subjects[sd]})
                    logging.warning('Subject does not exist - skipping:' + sd)
                    continue
            # Load data PER ROW
            matches.append(sd)
            if self.args.checks is None or not self.args.checks: #Don't upload if checks
                for i, row in dp.subjects[sd].iterrows():
                    if self.args.skiprows is not None and self.args.skiprows and \
                            (('NOT RUN' in row.values) or ('ABORT' in row.values)):
                        print("Skipping due to ABORT or NOT RUN")
                        continue
                    row.replace(np.nan, '', inplace=True)
                    sampleid = dp.getSampleid(sd, row)

                    # Sample
                    xsdtypes = dp.getxsd()
                    if ('amunet' in xsdtypes):
                        msg = self.loadAMUNETdata(sampleid, i, row, s, dp)
                        logging.info(msg)
                        print(msg)
                    else: #cantab and ACER
                        for type in xsdtypes.keys():
                            (mandata, data) = dp.mapData(row, i, type)
                            xsd = xsdtypes[type]
                            msg = self.loadSampledata(s, xsd, type + "_" + sampleid, mandata, data)
                            logging.info(msg)
                            print(msg)
        return (missing,matches)


    def outputChecks(self,projectcode,matches, missing, inputdir,f2):
        """
        Test run without actual uploading
        :param matches: List of matched participant IDs
        :param missing: Data rows for missing participants
        :param inputdir: Data directory
        :param filename: Report filename
        :return: report filenames of missing and matched files
        """
        reportdir = join(inputdir, "report")
        if not os.path.exists(reportdir):
            os.mkdir(reportdir)
        filename = os.path.basename(f2)
        match_filename = join(reportdir,filename + "_matched.csv" )
        missing_filename= join(reportdir,filename + "_missing.csv" )
        with open(match_filename, 'wb') as csvfile:
            spamwriter = csv.writer(csvfile, delimiter=',')
            spamwriter.writerow(['Matched ID'])
            for m in sorted(matches):
                spamwriter.writerow([m])

        #Missing subjects
        with open(missing_filename, 'wb') as csvfile:
            spamwriter = csv.writer(csvfile, delimiter=',')
            spamwriter.writerow(['Missing participants in XNAT'])
            sids = self.xnat.get_subjects(projectcode)
            for m in missing:
                rootid = m['ID'][0:4]
                guess = [s.label() for s in sids if rootid in s.label()]
                if len(guess) <= 0:
                    guess=""
                else:
                    guess="Possible ID: " + ",".join(guess)
                spamwriter.writerow([m['ID'], guess])
                for i, row in m['rows'].iterrows():
                    spamwriter.writerow(row)

        if self.args.checks is not None and self.args.checks:
            msg = "*******TEST RUN ONLY*******\n"
        else:
            msg = "*******XNAT UPLOADED*******\n"

        msg = "%sMatched participants: %d\nMissing participants: %d\n" % (
            msg, len(matches), len(missing))
        logging.info(msg)
        print(msg)

        return (match_filename,missing_filename)

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
    parser.add_argument('--config', action='store', help='database configuration file (overrides ~/.xnat.cfg)')
    parser.add_argument('--cantab', action='store', help='Upload CANTAB data from directory')
    parser.add_argument('--fields', action='store', help='CANTAB fields to extract',
                        default="cantab_fields.csv")
    parser.add_argument('--checks', action='store_true', help='Test run with output to files')
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
            #Test run
            missing = []
            matches = []
            if (not p.exists()):
                msg = "This project [%s] does not exist in this database [%s]" % (projectcode, uploader.args.database)
                raise ConnectionError(msg)
            # List available subjects in project
            if (uploader.args.subjects is not None and uploader.args.subjects):
                logging.info("Calling List Subjects")
                uploader.xnat.list_subjects_all(projectcode)
            # List available projects
            if (uploader.args.projects is not None and uploader.args.projects):
                logging.info("Calling List Projects")
                projlist = uploader.xnat.list_projects()
                for p in projlist:
                    print("Project: ", p.id())
            # Upload MRI scans from directory
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
            # Upload CANTAB data from directory
            if (uploader.args.cantab is not None and uploader.args.cantab):
                sheet = "RowBySession_HealthyBrains"
                inputdir = uploader.args.cantab
                cantabfields = os.path.join("resources",uploader.args.fields)

                print("Input:", inputdir)
                if access(inputdir, R_OK):
                    seriespattern = '*.*'
                    try:
                        files = glob.glob(join(inputdir, seriespattern))
                        print("Files:", len(files))
                        project = uploader.xnat.get_project(projectcode)
                        for f2 in files:
                            print("Loading", f2)
                            dp = CantabParser(cantabfields,f2, sheet)
                            (missing,matches) = uploader.uploadData(project,dp)
                            # Output matches and missing
                            if len(matches) > 0 or len(missing) > 0:
                                (out1, out2) = uploader.outputChecks(projectcode, matches, missing, inputdir, f2)
                                msg = "Reports created: \n\t%s\n\t%s" % (out1, out2)
                                print(msg)
                                logging.info(msg)

                    except:
                        e = sys.exc_info()[0]
                        raise ValueError(e)

                else:
                    msg = "Access to data directory is denied: %s" % inputdir
                    raise ConnectionError(msg)
            ### Upload Amunet data from directory
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
                            dp = AmunetParser(f2, sheet)
                            (missing, matches) = uploader.uploadData(project, dp)
                            # Output matches and missing
                            if len(matches) > 0 or len(missing) > 0:
                                (out1, out2) = uploader.outputChecks(projectcode, matches, missing, inputdir, f2)
                                msg = "Reports created: \n\t%s\n\t%s" % (out1, out2)
                                print(msg)
                                logging.info(msg)

                    except:
                        e = sys.exc_info()[0]
                        raise ValueError(e)
                else:
                    raise IOError("Input dir error")
            ### Upload ACE-R data from directory
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
                            dp = AcerParser(f2, sheet)
                            (missing, matches) = uploader.uploadData(project, dp)
                            # Output matches and missing
                            if len(matches) > 0 or len(missing) > 0:
                                (out1, out2) = uploader.outputChecks(projectcode, matches, missing, inputdir, f2)
                                msg = "Reports created: \n\t%s\n\t%s" % (out1,out2)
                                print(msg)
                                logging.info(msg)

                    except:
                        e = sys.exc_info()[0]
                        raise ValueError(e)
                else:
                    raise IOError("Input dir error")

        else:
            raise ConnectionError("Connection failed - check config")
    except IOError as e:
        logging.error(e)
        print "Failed IO:", e
    except ConnectionError as e:
        logging.error(e)
        print "Failed connection:", e
    except ValueError as e:
        logging.error(e)
        print "ERROR:", e
    finally:
        #Processing complete
        uploader.xnatdisconnect()
        logging.info("FINISHED")
        print("FINISHED - see xnatupload.log for details")

