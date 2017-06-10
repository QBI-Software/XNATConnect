import sys
import logging
import os
import pyforms
from subprocess import check_output
from   pyforms          import BaseWidget
from   pyforms.Controls import ControlText, ControlDir, ControlCheckBox, ControlCombo
from   pyforms.Controls import ControlButton

class OPEXUploaderGUI(BaseWidget):

    def __init__(self):
        super(OPEXUploaderGUI,self).__init__('OPEX Bulk Data Uploader')

        #Definition of the forms fields
        self._inputdir = ControlDir('Choose a directory containing input files')
        self._dataset = ControlCombo('Select dataset')
        self._dataset.add_item('Test Connection', '--help')
        self._dataset.add_item('CANTAB', '--cantab')
        self._dataset.add_item('AMUNET', '--amunet')
        self._dataset.add_item('MRIscans', '--u')
        self._cbCreateSubject = ControlCheckBox('Create Subjects from data')
        self._cbSkiprows = ControlCheckBox('Skip rows with ABORTED or NOT_RUN')
        self._database = ControlText('Database config')
        self._project = ControlText('Project code')
        self._submit = ControlButton('Run')
        self._cancel = ControlButton('Cancel')

        self._formset = ['_dataset',('_database','_project'),('_cbCreateSubject','_cbSkiprows'),'_inputdir','_status',('_submit','_cancel'),'']
        # Define the button action
        self._submit.value = self.__submitAction
        self._cancel.value = self.__cancelAction

    def __submitAction(self):
        """Button action event"""
        options = [self._dataset.value, self._database.value, self._project.value]
        if (self._cbCreateSubject.value):
            options.append('--create')
        if (self._cbSkiprows.value):
            options.append('--skiprows')
        print options
        #check_output("dir C:", shell=True)
        s =" "
        cmd = 'D:\\Programs\\Anaconda2\\python.exe D:\\lizcw\\Projects\\XNATConnect\\OPEXUploader.py --help'
        print(cmd)
        #os.system(cmd)
        check_output(cmd, shell=True)



    def __cancelAction(self):
        logging.info('Cancelled by request')
        sys.exit(0)

#Execute the application
if __name__ == "__main__":
    #pyforms.startApp( SimpleExample )
    pyforms.start_app( OPEXUploaderGUI)