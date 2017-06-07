import argparse
import glob
import logging
import os
from os import R_OK, access
from os.path import expanduser
from os.path import isdir, join

from qbixnat.CantabParser import CantabParser
from qbixnat.XnatConnector import XnatConnector

if __name__ == "__main__":

    parser = argparse.ArgumentParser(prog='OPEX Upload Samples',
                                     description='''\
        Script for uploading data to QBI OPEX XNAT db
         ''')
    parser.add_argument('database', action='store', help='select database config from xnat.cfg to connect to')
    parser.add_argument('projectcode', action='store', help='select project by code')
    parser.add_argument('--projects', action='store_true', help='list projects')
    parser.add_argument('--subjects', action='store_true', help='list subjects')
    parser.add_argument('--g', action='store', help='get XNAT ID for subject ID')
    parser.add_argument('--config', action='store', help='database configuration file (overrides ~/.xnat.cfg)')
    parser.add_argument('--cantab', action='store', help='Upload CANTAB data from directory')
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
    if (xnat.conn):
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
                seriespattern = '*.xls*'
                try:
                    files = glob.glob(join(inputdir, seriespattern))
                    print("Files:", len(files))
                    for f2 in files:
                        print("Loading", f2)
                        cantab = CantabParser(f2, sheet)
                        cantab.sortSubjects()
                        print('Subject summary')
                        for sd in cantab.subjects:
                            print('ID:', sd)
                            # TODO: Load MOTdata etc with individual functions
                            for i, row in cantab.subjects[sd].iterrows():
                                print(i, 'Visit:', row['Visit Identifier'], 'MOTML', row['MOTML'], 'MOTSDL', row['MOTSDL'])


                except ValueError as e:
                    print("Sheet not found: ", e)

                except:
                    raise OSError
            else:
                logging.error("Access to data directory is denied: %s" % inputdir)

        xnat.conn.disconnect()
        logging.info("Complete")
        print("FINISHED - see xnatupload.log for details")

    else:
        logging.warning("Failed to connect")
