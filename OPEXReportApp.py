import dash
import dash_core_components as dcc
import dash_html_components as html
import plotly.graph_objs as go
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

    def participants_layout(self, df, df_expts):
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
        ),
        # Expts stacked bar
        dcc.Graph(
           id='expts',
           figure=go.Figure(
               data=[
                   go.Bar(
                       customdata=df_expts['Subject'],
                       y=df_expts[i],
                       name=i,
                   ) for i in df_expts.columns[2:]

               ],
               layout=go.Layout(
                       xaxis={'type': 'linear', 'title': 'Participants'},
                       yaxis={'title': 'Expts Count'},
                       margin={'l': 40, 'b': 40, 't': 10, 'r': 10},
                       legend={'x': 0, 'y': 1},
                       hovermode='closest'
                   )

           ),

        )
    ])




#####################################################################

if __name__ == '__main__':

    home = expanduser("~")
    configfile = join(home, '.xnat.cfg')
    database = 'opex'
    projectcode = 'P1'
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
            print('Participants loaded:', df)
            report_expts = OPEXReport(csvfile="sampledata\\mva\\MVA_Participants_Expts.csv")
            df_expts = report_expts.getExptCollection()
            print df_expts.head()
            # reactive loading to app
            op.app.layout = op.participants_layout(df, df_expts)
            op.app.run_server(debug=True, port=8089)
        else:
            print "No subjects found - Check PROJECT CODE is correct"
        xnat.conn.disconnect()
        print("FINISHED")

    else:
        print "Failed to connect"
