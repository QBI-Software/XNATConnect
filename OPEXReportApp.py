import dash
import dash_core_components as dcc
import dash_html_components as html
import pandas as pd
from os.path import expanduser, join
from qbixnat.XnatConnector import XnatConnector  # Only for testing
from qbixnat.OPEXReport import OPEXReport

""" 
From https://plot.ly/dash/getting-started
"""
class OPEXReportApp(object):

    def __init__(self):
        self.app = dash.Dash()

    def colors(self):
        colors = {
        'background': '#111111',
        'text': '#7FDBFF'
        }
        return colors

    def participants_layout(self, df):
        colors = self.colors()
        title = 'OPEX XNAT participants [Total=' + str(sum(df['All'])) + ']'
        self.app.css.append_css({"external_url": "https://codepen.io/chriddyp/pen/bWLwgP.css"})
        return html.Div(className='container',
                                   style={'backgroundColor': colors['background']},
                                   children=[
        html.H1(children='OPEX Report',
                style={
                    'textAlign': 'center',
                    'color': colors['text']
                }
                ),

        html.Div(children=title,
                 style={
            'textAlign': 'center',
            'color': colors['text']
        }),

        dcc.Graph(
            id='participants',
            figure={
                'data': [
                    {'x': df['Group'], 'y': df['Male'], 'type': 'bar', 'name': 'Male'},
                    {'x': df['Group'], 'y': df['Female'], 'type': 'bar', 'name': 'Female'},
                ],
                'layout': {
                    'barmode':'stack',
                    'plot_bgcolor': colors['background'],
                    'paper_bgcolor': colors['background'],
                    'font': {
                        'color': colors['text']
                    }
                }
            }
        )
    ])




#####################################################################

if __name__ == '__main__':

    home = expanduser("~")
    configfile = join(home, '.xnat.cfg')
    database = 'xnat-dev'
    projectcode = 'TEST_PJ00'
    xnat = XnatConnector(configfile, database)
    print "Connecting to URL=", xnat.url
    xnat.connect()
    if xnat.testconnection():
        print "...Connected"
        subjects = xnat.get_subjects(projectcode)
        if (subjects.fetchone() is not None):
            report = OPEXReport(subjects)
            op = OPEXReportApp()
            df = report.getParticipants()
            print('Data loaded:', df)
            op.app.layout = op.participants_layout(df) #reactive loading
            proj = xnat.get_project(projectcode)
            expts = proj.experiments("MOT")
            teste = expts.fetchone()
            teste.attrs.get('label')
            teste.attrs.get('status')
            atts = teste.attrs
            df1 = report.getMultivariate(expts)
            op.app.run_server(debug=True, port=8089)
        else:
            print "No subjects found - Check PROJECT CODE is correct"
        xnat.conn.disconnect()
        print("FINISHED")

    else:
        print "Failed to connect"
