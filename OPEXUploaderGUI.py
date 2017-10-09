import sys
import logging
import os
import wx

import subprocess
from os.path import isdir, join, expanduser
from os import access, R_OK, walk, mkdir
from qbixnat.gui.noname import UploaderGUI
from configobj import ConfigObj


class OPEXUploaderGUI(UploaderGUI):
    def __init__(self, parent):
        """
        Load from userhome/.xnat.cfg
        :param parent:
        """
        super(OPEXUploaderGUI, self).__init__(parent)
        self.runoptions = ['Help']
        self.configfile = join(expanduser('~'), '.xnat.cfg')
        self.loaded = self.__loadConfig()
        if self.loaded:
            self.chOptions.SetItems(self.runoptions.keys())
        self.Show()

    def __loadConfig(self):
        if self.configfile is not None:
            try:
                if access(self.configfile, R_OK):
                    print("Loading config file")
                    config = ConfigObj(self.configfile, encoding='UTF-8')
                    self.runoptions = config['options']
                    return True

            except:
                raise IOError
        return False

    def __loadCommand(self, options):
        s = " "
        cwd = join(os.getcwd(), "OPEXUploader.py")
        if ('PYTHONEXE' in os.environ):
            pythoncmd = os.environ('PYTHONEXE')
        else:
            pythoncmd = sys.prefix + os.sep + "Scripts" + os.sep + "python.exe"

        cmd = pythoncmd + " " + cwd + " " + s.join(options)
        return cmd

    def __loadConnection(self):
        db = self.dbedit.GetValue()
        proj = self.projectedit.GetValue()
        if len(db) <= 0 and len(proj) <= 0:
            dlg = wx.MessageDialog(self, "Database or project configuration is empty or invalid", "Connection Config Error", wx.OK)
            dlg.ShowModal()
            dlg.Destroy()
            return (None, None)
        else:
            return (db,proj)

    def OnAbout(self, e):
        # A message dialog box with an OK button. wx.OK is a standard ID in wxWidgets.
        dlg = wx.MessageDialog(self, "Uploader for OPEX data to XNAT\n(c)2017 QBI Software", "About OPEX Uploader", wx.OK)
        dlg.ShowModal()  # Show it
        dlg.Destroy()  # finally destroy it when finished.

    def OnHelp(self,e):
        self.tcResults.Clear()
        cmd = self.__loadCommand(['-x'])
        try:
            output = subprocess.check_output(cmd, shell=True)
            self.tcResults.AppendText(output)
        except subprocess.CalledProcessError as e:
            msg = "Program Execution failed:" + e.message + "(" + str(e.returncode) + ")"
            print >> sys.stderr, msg
            self.tcResults.AppendText(msg)

    def OnTest(self,e):
        """
        Test connection is correctly configured
        :param e:
        :return:
        """
        self.tcResults.Clear()
        (db,proj) = self.__loadConnection()
        if db is None:
            return 0
        options = ['--projects', db, proj]
        cmd = self.__loadCommand(options)
        try:
            output = subprocess.check_output(cmd, shell=True)
            msg = "Connection to %s for project=%s\n" % (db,proj)
            self.tcResults.AppendText(msg)
            self.tcResults.AppendText(output)
        except subprocess.CalledProcessError as e:
            msg = "Program Execution failed:" + e.message + "(" + str(e.returncode) + ")"
            print >> sys.stderr, msg
            self.tcResults.AppendText(msg)

    def OnClose(self, e):
        self.Close(True)  # Close the frame.

    def OnOpen(self, e):
        """ Open a file"""
        #self.dirname = ''
        dlg = wx.DirDialog(self, "Choose a directory containing input files")
        if dlg.ShowModal() == wx.ID_OK:
            self.dirname = '"{0}"'.format(dlg.GetPath())
            #self.StatusBar.SetStatusText("Loaded: %s\n" % self.dirname)
            self.inputedit.SetValue(self.dirname)
        dlg.Destroy()

    def OnEditDirname(self, event):
        self.dirname = '"{0}"'.format(event.GetString())
        #self.StatusBar.SetStatusText("Input dir: %s\n" % self.dirname)


    def OnSubmit(self,event):
        """
        Run OPEX Uploader with args
        :return: return code shown in status
        """
        self.tcResults.Clear()
        runoption = self.runoptions.get(self.chOptions.GetValue())
        (db, proj) = self.__loadConnection()
        if db is None:
            return 0
        options = [runoption, db, proj]
        if self.dirname is None or len(self.dirname) <=0:
            dlg = wx.MessageDialog(self, "Data directory not specified", "About OPEX Uploader", wx.OK)
            dlg.ShowModal()  # Show it
            dlg.Destroy()
        else:
            options.pop(0)
            options.append(runoption + " " + self.dirname)

            if (self.cbCreateSubject.GetValue()):
                options.append('--create')
            if (self.cbSkiprows.GetValue()):
                options.append('--skiprows')
            if (self.cbChecks.GetValue()):
                options.append('--checks')
            if (self.cbUpdate.GetValue()):
                options.append('--update')
            print options

            cmd = self.__loadCommand(options)
            self.tcResults.AppendText(cmd)
            self.tcResults.AppendText("\n*******\n")

            try:
                output = subprocess.check_output(cmd, shell=True)
                self.tcResults.AppendText(output)

            except subprocess.CalledProcessError as e:
                retcode = e.returncode
                if retcode < 0:
                    msg = "Program was terminated by signal [" + str(retcode) + "]"
                    print >> sys.stderr, msg
                elif retcode == 1:
                    msg = "Program ran successfully [" + str(retcode) + "]"
                    print >> sys.stderr, msg
                else:
                    msg = "Program error [" + str(retcode) + "] - check output"
                    print >> sys.stderr, msg
                self.tcResults.AppendText(msg)


def main():
    app = wx.App(False)
    OPEXUploaderGUI(None)
    app.MainLoop()

#Execute the application
if __name__ == '__main__':
    main()
