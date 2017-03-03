#Instructions for manual use of QBI XNAT scripts.

## Installation (first time use)

1. Create separate python environment with Python v2.7
In your home directory (~/.) type the following commands:


>mkdir dev

>cd dev

>virtualenv --python=/usr/bin/python2 py2venv

>source py2venv/bin/activate

>pip install pyxnat

>pip install pydicom

## Activate your python environment before running the scripts

>source py2venv/bin/activate

2. Download the scripts - these are under version control on Github


>git clone https://github.com/QBI-Software/XNATConnect.git

>cd XNATConnect

3. Set up your connection to the XNAT server

>nano xnat.cfg (or any other text editor)
 
 - Replace XXXX with your username and password for XNAT 
 
 - ensure the URL is also correct
 
 - logins for other XNAT servers can be added
 
 **Save this file as ~/.xnat.cfg and change the permissions to prevent others from seeing your login details
 

 ie -rw------- .xnat.cfg
 
## Test

>python XnatUploadScripts.py --help


If problems, check your script has execute permission (+x) and that the python libraries have been installed as above

3. Updating scripts - ensure you have the latest version with:

>git pull

## Organizing input files

Input directory structure must be of the following format:

data/SUBJECTID/scans/series/*.IMA (or *.DCM)

If not, they can be reorganized with the XnatOrganizeFiles.py script which expects the following format:

SUBJECTID/group/*.IMA (or *.DCM) 


where the files are mixed series

>python XnatOrganizeFiles.py SUBJECTID

(where SUBJECTID is the foldername of the top level directory - don't include the end slash)

- this should create a folder called "sortedscans" which can be used in the upload script

## Uploading scans

>python XnatUploadScans.py [config-server] [project-id] --u <inputdir>

where config-server corresponds to the login config in ~/.xnat.cfg
and project-id is the ID of your XNAT project (which you have owner permissions for)

eg python XnatUploadScans.py myxnat TEST_PJ00 --u <fullpath>/sortedscans

If all goes well - you should see some output indicating the files have been moved to a new directory called "done".  

There is also a log file called "xnatuploadscans.log"

Login to XNAT and check that all is OK.

You may also get an email from XNAT.

## If there are errors:

1. check the input directory structure as above
2. check that all the files are MR scans (DICOM or Siemens IMA)
3. check permissions for everything
4. contact Liz (e.cooperwilliams@uq.edu.au)

