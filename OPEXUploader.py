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
from qbixnat.XnatConnector import XnatConnector


def genders():
    return {0:'male',1:'female'}

def formatDateString(orig):
    '''Reformats datetime string from yyyy.mm.dd hh:mm:ss to yyyy-mm-dd'''
    dt = datetime.strptime(orig, "%Y.%m.%d %H:%M:%S")
    return dt.strftime("%Y-%m-%d")

def getStringDateUTC(orig):
    '''Returns datetime string as a unique id'''
    dt = datetime.strptime(orig, "%Y.%m.%d %H:%M:%S UTC")
    return dt.strftime("%Y%m%d%H%M%S")

def formatDob(orig):
    """
    Reformats DOB string from yyyy-mm-dd 00:00:00 as returned by series obj to yyyy-mm-dd
    """
    #dt = datetime.strptime(orig,"%d-%b-%y") #if was 20-Oct-50
    #dt = datetime.strptime(orig, "%d/%m/%Y")
    dt = datetime.strptime(orig, "%Y-%m-%d %H:%M:%S")
    return dt.strftime("%Y-%m-%d")

def formatDobNumber(orig):
    """
    Reformats DOB string from float to yyyy-mm-dd
    """
    dateoffset = 693594
    dt = datetime.fromordinal(dateoffset + int(orig))
    return dt.strftime("%Y-%m-%d")

def getInterval(orig):
    """Parses string M-00 to 0 or M-01 to 1 etc"""
    interval = int(orig[2:])
    return interval


def loadMOTdata(cantabid,i,row,subject):
    """ Loads MOT sample data from CANTAB data dump
    Check if already exists - don't overwrite (allows for cumulative data files to be uploaded)
    :param cantabid: ID for this row of CANTAB data
    :param i: row number of dataset
    :param row: row with data
    :param subject: subject to add experiment to
    :return: msg for logging
    """
    motid = "MOT_" + cantabid
    expt = subject.experiment(motid)
    #experiments = [e.label() for e in subject.experiments() if e.label()== motid]
    if not expt.exists():
        motxsd = 'opex:cantabMOT'
        visit_date = formatDateString(row['Visit Start (Local)'])
        interval = getInterval(row['Visit Identifier'])
        comments = str(row['MOT Voice Comment'])
        if comments.lower() == 'nan':
            comments =''
        motdata = {
            motxsd + '/interval': str(interval),
            motxsd + '/date': row['Visit Start (Local)'],
            motxsd + '/date_analysed': visit_date,
            motxsd + '/sample_id': str(i),  # row number in this data file for reference
            motxsd + '/sample_num': '0',  # ie repeat runs - may need to fix later
            motxsd + '/sample_quality': 'Unknown',  # default - check later if an error
            motxsd + '/status': str(row['MOT Voice Status']),
            motxsd + '/comments': comments,
            motxsd + '/MOTML': str(row['MOTML']),
            motxsd + '/MOTSDL': str(row['MOTSDL'])}
        xnat.createExperiment(subject, motxsd, motid, motdata)
        msg = 'MOT experiment created:' + motid
    else:
        msg = 'MOT experiment already exists: ' + motid
    return msg

def loadPALdata(cantabid,i,row,subject):
    """ Loads PAL sample data from CANTAB data dump
    Check if already exists - don't overwrite (allows for cumulative data files to be uploaded)
    :param cantabid: ID for this row of CANTAB data
    :param i: row number of dataset
    :param row: row with data
    :param subject: subject to add experiment to
    :return: msg for logging
    """
    motid = "PAL_" + cantabid
    expt = subject.experiment(motid)
    #experiments = [e.label() for e in subject.experiments() if e.label()== motid]
    if not expt.exists():
        motxsd = 'opex:cantabPAL'
        visit_date = formatDateString(row['Visit Start (Local)'])
        interval = getInterval(row['Visit Identifier'])
        comments = str(row['PAL Recommended Standard Comment'])
        if comments.lower() == 'nan':
            comments =''
        motdata = {
            motxsd + '/interval': str(interval),
            motxsd + '/date': row['Visit Start (Local)'], #PARSED in experiment load
            motxsd + '/date_analysed': visit_date,
            motxsd + '/sample_id': str(i),  # row number in this data file for reference
            motxsd + '/sample_num': '0',  # ie repeat runs - may need to fix later
            motxsd + '/sample_quality': 'Unknown',  # default - check later if an error
            motxsd + '/status': str(row['PAL Recommended Standard Status']),
            motxsd + '/comments': comments,
            motxsd + '/PALFAMS': str(row['PALFAMS']),
            motxsd + '/PALMETS': str(row['PALMETS']),
            motxsd + '/PALTA': str(row['PALTA']),
            motxsd + '/PALTE': str(row['PALTE']),
            motxsd + '/PALTEA': str(row['PALTEA']),
            motxsd + '/PALTEA6': str(row['PALTEA6']),
            motxsd + '/PALTEA8': str(row['PALTEA8'])
        }
        xnat.createExperiment(subject, motxsd, motid, motdata)
        msg = 'PAL experiment created:' + motid
    else:
        msg = 'PAL experiment already exists: ' + motid
    return msg

def loadDMSdata(cantabid,i,row,subject):
    """ Loads DMS sample data from CANTAB data dump
    Check if already exists - don't overwrite (allows for cumulative data files to be uploaded)
    :param cantabid: ID for this row of CANTAB data
    :param i: row number of dataset
    :param row: row with data
    :param subject: subject to add experiment to
    :return: msg for logging
    """
    motid = "DMS_" + cantabid
    expt = subject.experiment(motid)
    #experiments = [e.label() for e in subject.experiments() if e.label()== motid]
    if not expt.exists():
        motxsd = 'opex:cantabDMS'
        visit_date = formatDateString(row['Visit Start (Local)'])
        interval = getInterval(row['Visit Identifier'])
        comments = str(row['DMS Recommended Standard Comment'])
        if comments.lower() == 'nan':
            comments =''
        motdata = {
            motxsd + '/interval': str(interval),
            motxsd + '/date': row['Visit Start (Local)'], #PARSED in experiment load
            motxsd + '/date_analysed': visit_date,
            motxsd + '/sample_id': str(i),  # row number in this data file for reference
            motxsd + '/sample_num': '0',  # ie repeat runs - may need to fix later
            motxsd + '/sample_quality': 'Unknown',  # default - check later if an error
            motxsd + '/status': str(row['DMS Recommended Standard Status']),
            motxsd + '/comments': comments,
            motxsd + '/DMSCC': str(row['DMSCC']),
            motxsd + '/DMSML': str(row['DMSML']),
            motxsd + '/DMSML0': str(row['DMSML0']),
            motxsd + '/DMSML12': str(row['DMSML12']),
            motxsd + '/DMSMLAD': str(row['DMSMLAD']),
            motxsd + '/DMSPC': str(row['DMSPC']),
            motxsd + '/DMSPC0': str(row['DMSPC0']),
            motxsd + '/DMSPC12': str(row['DMSPC12']),
            motxsd + '/DMSPCAD': str(row['DMSPCAD']),
            motxsd + '/DMSTC0': str(row['DMSTC0']),
            motxsd + '/DMSTC12': str(row['DMSTC12']),
            motxsd + '/DMSTCAD': str(row['DMSTCAD']),
            motxsd + '/DMSTCS': str(row['DMSTCS']),
            motxsd + '/DMSTE': str(row['DMSTE']),
            motxsd + '/DMSTEAD': str(row['DMSTEAD'])
        }
        xnat.createExperiment(subject, motxsd, motid, motdata)
        msg = 'DMS experiment created:' + motid
    else:
        msg = 'DMS experiment already exists: ' + motid
    return msg

def loadSWMdata(cantabid,i,row,subject):
    """ Loads SWM sample data from CANTAB data dump
    Check if already exists - don't overwrite (allows for cumulative data files to be uploaded)
    :param cantabid: ID for this row of CANTAB data
    :param i: row number of dataset
    :param row: row with data
    :param subject: subject to add experiment to
    :return: msg for logging
    """
    motid = "SWM_" + cantabid
    expt = subject.experiment(motid)
    #experiments = [e.label() for e in subject.experiments() if e.label()== motid]
    if not expt.exists():
        motxsd = 'opex:cantabSWM'
        visit_date = formatDateString(row['Visit Start (Local)'])
        interval = getInterval(row['Visit Identifier'])
        comments = str(row['SWM Recommended standard Comment'])
        if comments.lower() == 'nan':
            comments =''
        motdata = {
            motxsd + '/interval': str(interval),
            motxsd + '/date': row['Visit Start (Local)'], #PARSED in experiment load
            motxsd + '/date_analysed': visit_date,
            motxsd + '/sample_id': str(i),  # row number in this data file for reference
            motxsd + '/sample_num': '0',  # ie repeat runs - may need to fix later
            motxsd + '/sample_quality': 'Unknown',  # default - check later if an error
            motxsd + '/status': str(row['SWM Recommended standard Status']),
            motxsd + '/comments': comments,
            motxsd + '/SWMBE': str(row['SWMBE']),
            motxsd + '/SWMBE6': str(row['SWMBE6']),
            motxsd + '/SWMBE8': str(row['SWMBE8']),
            motxsd + '/SWMDE8': str(row['SWMDE8']),
            motxsd + '/SWMTE': str(row['SWMTE']),
            motxsd + '/SWMTE6': str(row['SWMTE6']),
            motxsd + '/SWMTE8': str(row['SWMTE8']),
            motxsd + '/SWMWE': str(row['SWMWE'])
        }
        xnat.createExperiment(subject, motxsd, motid, motdata)
        msg = 'SWM experiment created:' + motid
    else:
        msg = 'SWM experiment already exists: ' + motid
    return msg

def loadAMUNETdata(cantabid,i,row,subject):
    """ Loads AMUNET sample data from CANTAB data dump
    Check if already exists - don't overwrite (allows for cumulative data files to be uploaded)
    :param cantabid: ID for this row of CANTAB data
    :param i: row number of dataset
    :param row: row with data
    :param subject: subject to add experiment to
    :return: msg for logging
    """
    motid = cantabid
    expt = subject.experiment(motid)
    #experiments = [e for e in subject.experiments() if e.label()== motid]
    motxsd = 'opex:amunet'
    #if len(experiments)==0: #new
    if not expt.exists():
        visit = re.search('Visit\s(\d{1,2})', str(row['S_Visit']))
        interval = int(visit.group(1)) - 1

        #two files with different columns
        if 'AEV_Average total error' in row:

            motdata = {
                motxsd + '/interval': str(interval),
                motxsd + '/AEVcomments': str(row['AEV_Lexical rating']),
                motxsd + '/AEV': str(row['AEV_Average total error']),
                motxsd + '/EV': str(row['EV_Average total error']),
                motxsd + '/AV': str(row['AV_Average total error']),
                motxsd + '/DV': str(row['DV_Average total error'])

            }
        else:
            motdata = {
                motxsd + '/interval': str(interval),
                motxsd + '/SCScomments': str(row['SCS_Lexical rating']),
                motxsd + '/SCS': str(row['SCS_Average total error']),
                motxsd + '/SCD': str(row['SCD_Average total error']),
                motxsd + '/SAS': str(row['SAS_Average total error']),
                motxsd + '/SAD': str(row['SAD_Average total error']),
                motxsd + '/SES': str(row['SES_Average total error']),
                motxsd + '/SED': str(row['SED_Average total error'])
            }
        xnat.createExperiment(subject, motxsd, motid, motdata)
        msg = 'Amunet experiment created:' + motid
    #elif(len(experiments[0].xpath('opex:AEV')) > 0 and len(experiments[0].xpath('opex:SCS')) == 0 and 'SCS_Average total error' in row): #loaded AEV data but not SCS
    elif (len(expt.xpath('opex:AEV')) > 0 and len(expt.xpath('opex:SCS')) == 0 and 'SCS_Average total error' in row):  # loaded AEV data but not SCS

        e1 = expt
        motdata = {
            motxsd + '/SCScomments': str(row['SCS_Lexical rating']),
            motxsd + '/SCS': str(row['SCS_Average total error']),
            motxsd + '/SCD': str(row['SCD_Average total error']),
            motxsd + '/SAS': str(row['SAS_Average total error']),
            motxsd + '/SAD': str(row['SAD_Average total error']),
            motxsd + '/SES': str(row['SES_Average total error']),
            motxsd + '/SED': str(row['SED_Average total error'])
        }
        e1.attrs.mset(motdata)
        msg = 'Amunet experiment updated with SCS: '+ motid

    elif(len(expt.xpath('opex:SCS')) > 0 and len(expt.xpath('opex:AEV')) == 0 and 'AEV_Average total error' in row):  # loaded SCS data but not AEV
        e1 = expt
        motdata = {
            motxsd + '/AEVcomments': str(row['AEV_Lexical rating']),
            motxsd + '/AEV': str(row['AEV_Average total error']),
            motxsd + '/EV': str(row['EV_Average total error']),
            motxsd + '/AV': str(row['AV_Average total error']),
            motxsd + '/DV': str(row['DV_Average total error'])
        }
        e1.attrs.mset(motdata)
        msg = 'Amunet experiment updated with AEV: '+ motid
    else:
        msg = 'Amunet experiment already exists: ' + motid
    return msg



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
    parser.add_argument('--u', action='store',
                        help='Upload MRI scans from directory with data/subject_label/scans/session_label/[*.dcm|*.IMA]')

    args = parser.parse_args()

    # get current user's login details (linux) or local file (windows)
    home = expanduser("~")
    configfile = join(home, '.xnat.cfg')
    if args.config is not None:
        try:
            os.access(args.config, os.R_OK)
            configfile = args.config
        except:
            raise IOError
    try:
        os.access(configfile, os.R_OK)
    except:
        raise os.error
        sys.exit(1)

    logging.basicConfig(filename='xnatupload.log', level=logging.INFO, format='%(asctime)s %(message)s', datefmt='%d-%m-%Y %I:%M:%S %p')
    logging.info('Connected to Server:%s Project:%s', args.database, args.projectcode)
    xnat = XnatConnector(configfile, args.database)
    xnat.connect()
    try:
        testconn = xnat.conn.inspect.datatypes('xnat:subjectData')
        if len(testconn) > 0:
            logging.info("...Connected")
            print("Connected")

            projectcode = args.projectcode
            if (args.subjects is not None and args.subjects):
                logging.info("Calling List Subjects")
                xnat.list_subjects_all(projectcode)

            if (args.projects is not None and args.projects):
                logging.info("Calling List Projects")
                projlist = xnat.list_projects()
                for p in projlist:
                    print("Project: ", p.id())
            if (args.g is not None and args.g):
                subjectid = args.g
                sid = xnat.get_subjectid_bylabel(projectcode, subjectid)
                print("XNAT ID=%s for subject ID=%s" % (sid, subjectid))
            if (args.u is not None and args.u):
                uploaddir = args.u  # Top level DIR FOR SCANS
                # Directory structure data/subject_label/scans/session_id/*.dcm
                if isdir(uploaddir):
                    fid = xnat.upload_MRIscans(projectcode, uploaddir)
                    if fid == 0:
                        logging.warning('Upload not successful - 0 sessions uploaded')
                    else:
                        logging.info("Subject sessions uploaded: %d", fid)
                else:
                    logging.warning("Directory path cannot be found: %s", uploaddir)
            if (args.cantab is not None and args.cantab):
                sheet = "RowBySession_HealthyBrains"
                inputdir = args.cantab
                print("Input:", inputdir)
                if access(inputdir, R_OK):
                    seriespattern = '*.*'
                    try:
                        files = glob.glob(join(inputdir, seriespattern))
                        print("Files:", len(files))
                        project = xnat.get_project(projectcode)
                        for f2 in files:
                            print("Loading", f2)
                            cantab = CantabParser(f2, sheet)
                            cantab.sortSubjects()

                            for sd in cantab.subjects:

                                print('ID:', sd)
                                sjs = [s for s in project.subjects() if s.label() == sd]
                                s = project.subject(sd)

                                if not s.exists():
                                    #create subject in database
                                    dob = formatDob(str(cantab.subjects[sd]['Date of Birth'].iloc[0]))
                                    gender = genders()[cantab.subjects[sd]['Gender'].iloc[0]]
                                    group = str(cantab.subjects[sd]['Group'].iloc[0])
                                    skwargs = {'dob': dob, 'gender':gender, 'group':group}
                                    s = xnat.createSubject(projectcode,sd, skwargs)
                                    logging.info('Subject created: ' + sd)
                                    print('Subject created: ' + sd)
                                #else:
                                #   s = sjs[0]
                                #Load data PER ROW
                                for i, row in cantab.subjects[sd].iterrows():
                                    if args.skiprows and str(row['DMS Recommended Standard Status']) in ['NOT_RUN', 'ABORTED']:
                                        continue
                                    cantabid = sd + '_' + getStringDateUTC(row['Visit Start (GMT)'])
                                    print(i, 'Visit:', row['Visit Identifier'], 'EXPT ID', cantabid)
                                    row.replace(np.nan,'', inplace=True)
                                    #Sample
                                    msg = loadMOTdata(cantabid,i,row,s)
                                    logging.info(msg)
                                    print(msg)
                                    msg = loadPALdata(cantabid, i, row, s)
                                    logging.info(msg)
                                    print(msg)
                                    msg = loadDMSdata(cantabid, i, row, s)
                                    logging.info(msg)
                                    print(msg)
                                    msg = loadSWMdata(cantabid, i, row, s)
                                    logging.info(msg)
                                    print(msg)

                    except:
                        e = sys.exc_info()[0]
                        logging.error("Unable to process:", e)
                else:
                    logging.error("Access to data directory is denied: %s" % inputdir)
            ###Amunet data
            if (args.amunet is not None and args.amunet):
                sheet = "1"
                inputdir = args.amunet
                print("Input:", inputdir)
                if access(inputdir, R_OK):
                    seriespattern = '*.*'
                    try:
                        files = glob.glob(join(inputdir, seriespattern))
                        print("Files:", len(files))
                        project = xnat.get_project(projectcode)
                        for f2 in files:
                            print("Loading", f2)
                            cantab = AmunetParser(f2, sheet)
                            cantab.sortSubjects()

                            for sd in cantab.subjects:
                                print('ID:', sd)
                                #sjs = [s for s in project.subjects() if s.label() == sd]
                                s = project.subject(sd)
                                if not s.exists():
                                    #create subject in database
                                    dob = formatDobNumber(cantab.subjects[sd]['S_Date of birth'].iloc[0])
                                    gender = str(cantab.subjects[sd]['S_Sex'].iloc[0]).lower()
                                    hand = str(cantab.subjects[sd]['S_Hand'].iloc[0])
                                    skwargs = {'dob': dob}
                                    if gender in ['female','male']:
                                        skwargs['gender']=gender
                                    if hand in ['Right','Left','Ambidextrous']:
                                        skwargs['handedness'] = hand
                                    s = xnat.createSubject(projectcode,sd, skwargs)
                                    logging.info('Subject created: ' + sd)
                                    print('Subject created: ' + sd)
                                #else:
                                #    s = sjs[0]
                                #Load data PER ROW
                                for i, row in cantab.subjects[sd].iterrows():
                                    visit = re.search('Visit\s(\d{1,2})', str(row['S_Visit']))
                                    cantabid = "AM_" + sd + "_" + visit.group(1)
                                    print(i, 'Visit:', row['S_Visit'], 'EXPT ID', cantabid)
                                    row.replace(np.nan,'', inplace=True)
                                    #Sample

                                    msg = loadAMUNETdata(cantabid,i,row,s)
                                    logging.info(msg)
                                    print(msg)


                    except:
                        e = sys.exc_info()[0]
                        logging.error("Unable to process:", e)
                else:
                    logging.error("Access to data directory is denied: %s" % inputdir)

            xnat.conn.disconnect()
            logging.info("FINISHED")
            print("FINISHED - see xnatupload.log for details")

    except ConnectionError as e:
        xnat.conn.disconnect()
        logging.error("Failed to connect:", e)
        print e
