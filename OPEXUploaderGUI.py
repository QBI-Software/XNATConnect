import sys
import logging
import os
import pyforms
import subprocess
from subprocess import check_output,STDOUT
from   pyforms          import BaseWidget
from   pyforms.Controls import ControlText, ControlDir, ControlCheckBox, ControlCombo
from   pyforms.Controls import ControlButton, ControlLabel

class OPEXUploaderGUI(BaseWidget):

    def __init__(self):
        super(OPEXUploaderGUI,self).__init__('OPEX Bulk Data Uploader')

        #Definition of the forms fields
        self._inputdir = ControlDir('Choose a directory containing input files')
        self._dataset = ControlCombo('Select dataset')
        self._dataset.add_item('Help', '--help')
        self._dataset.add_item('Test Connection', '--projects')
        self._dataset.add_item('CANTAB', '--cantab')
        self._dataset.add_item('AMUNET', '--amunet')
        self._dataset.add_item('MRIscans', '--u')
        self._cbCreateSubject = ControlCheckBox('Create Subjects from data')
        self._cbSkiprows = ControlCheckBox('Skip rows with ABORTED or NOT_RUN')
        self._database = ControlText('Database config')
        self._project = ControlText('Project code')
        self._status = ControlLabel('Status')
        self._submit = ControlButton('Run')
        self._cancel = ControlButton('Cancel')
        # Layout
        self._formset = ['_dataset',('_database','_project'),('_cbCreateSubject','_cbSkiprows'),'_inputdir','_status',('_submit','_cancel'),'']
        #Styling
        self._status.__format__('background-color:white')
        # Define the button actions
        self._submit.value = self.__submitAction
        self._cancel.value = self.__cancelAction

    def __submitAction(self):
        """
        Run OPEX Uploader with args
        :return: return code shown in status
        """
        options = [self._dataset.value, self._database.value, self._project.value]

        if self._dataset.value != "--help":
            if (len(self._database.value)<=0 and len(self._project.value) <=0):
                self._status.value ="Program requires database and project values to proceed"
                return 1
            if self._dataset.value != "--projects":
                if len(self._inputdir.value) <=0:
                    self._status.value ="Please provide data directory to load from"
                    return 1
                else:
                    options.pop(0)
                    options.append(self._dataset.value + " " + self._inputdir.value)

                if (self._cbCreateSubject.value):
                    options.append('--create')
                if (self._cbSkiprows.value):
                    options.append('--skiprows')
        print options
        s =" "
        cmd = "D:\\Programs\\Anaconda2\\python.exe D:\\lizcw\\Projects\\XNATConnect\\OPEXUploader.py "
        cmd = cmd + s.join(options)
        print(cmd)
        msg=""
        try:
            retcode = subprocess.call(cmd, shell=True)
            if retcode < 0:
                msg = "Program was terminated by signal [" + str(retcode) + "]"
                self._status.value = msg
                print >> sys.stderr, msg
            else:
                msg = "Program ran successfully [" + str(retcode) + "]"
                self._status.value = msg
                print >> sys.stderr, msg
        except OSError as e:
            msg = "Program Execution failed:" + e.message
            print >> sys.stderr, msg

    def __cancelAction(self):
        logging.info('Cancelled by request')
        sys.exit(0)

#Execute the application
if __name__ == "__main__":
    #pyforms.startApp( SimpleExample )
    pyforms.start_app( OPEXUploaderGUI, geometry=(200,200,400,400))