import dash
import dash_core_components as dcc
import dash_html_components as html
import plotly.graph_objs as go
import pandas as pd
from os.path import expanduser, join, exists
from qbixnat.XnatConnector import XnatConnector  # Only for testing
from qbixnat.OPEXReport import OPEXReport
import time
import multiprocessing
from datetime import datetime
from matplotlib import colors as mcolors
import pandas as pd
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

    def tablecell(self,val):
        mycolors = list(mcolors.CSS4_COLORS.keys())

        if type(val) != str:
            if val == 0:
                return html.Td([html.Span(className="glyphicon glyphicon-ok")],
                               className="btn-success")
            else:
                return html.Td([html.Span(val)], style={'color':'black','background-color': mcolors.CSS4_COLORS[mycolors[val]]})
        else:
            return html.Td(val)

    def generate_table(self,dataframe, max_rows=10):
        colors = self.colors()
        return html.Table(
            # Header
            [html.Tr([html.Th(col) for col in dataframe.columns])] +

            # Body
            [html.Tr([
                self.tablecell(dataframe.iloc[i][col]) for col in dataframe.columns
            ]) for i in range(min(len(dataframe), max_rows))]
            ,
            className='table',
            style={
                    'textAlign': 'center',
                    'color': colors['text']
                })

    def participants_layout(self, df, df_expts, df_report):
        colors = self.colors()
        title = 'OPEX XNAT participants [Total=' + str(sum(df['All'])) + ']'
        #self.app.css.append_css({"external_url": "https://codepen.io/chriddyp/pen/bWLwgP.css"})
        self.app.css.append_css({"external_url": "https://maxcdn.bootstrapcdn.com/bootstrap/3.3.7/css/bootstrap.min.css"})
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
                       text=df_expts['Subject'],
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

        ),
        html.Div(id='missing',
                 children=[
           html.H3(children='Missing Data report',
                   style={
                       'textAlign': 'center',
                       'color': colors['text']
                   }),
            self.generate_table(df_report, max_rows=100)
            ])
    ])




#####################################################################

if __name__ == '__main__':
    import sys
    import argparse

    home = expanduser("~")
    configfile = join(home, '.xnat.cfg')
    parser = argparse.ArgumentParser(prog=sys.argv[0],
                                     description='''\
            Report App for data in QBI OPEX XNAT db
             ''')
    parser.add_argument('database', action='store', help='select database config from xnat.cfg to connect to')
    parser.add_argument('projectcode', action='store', help='select project by code')
    args = parser.parse_args()
    database = args.database
    projectcode = args.projectcode
    xnat = XnatConnector(configfile, database)
    print "Connecting to URL=", xnat.url
    xnat.connect()
    if xnat.testconnection():
        print "...Connected"
        subjects = xnat.get_subjects(projectcode)
        if (subjects.fetchone() is not None):
            op = OPEXReportApp()
            output = "ExptCounts_%s.csv" % datetime.today().strftime("%Y%m%d")
            outputfile = join("sampledata",output)
            if exists(outputfile):
                report = OPEXReport(csvfile=outputfile)
                cache = True
            else:
                report = OPEXReport(subjects)
                cache = False

            report.xnat = xnat

            df = report.getParticipants()
            print('Participants loaded:', df)
            #Get counts from database if not CSV
            if not cache:
                active_subjects = [s for s in subjects if s.attrs.get('group') != 'withdrawn']
                subjects = list(active_subjects)
                start = time.time()
                total_tasks = len(subjects)
                tasks = []
                mm = multiprocessing.Manager()
                q = mm.dict()
                for i in range(total_tasks):
                    p = multiprocessing.Process(target=report.processCounts, args=(subjects[i], q))
                    tasks.append(p)
                    p.start()

                for p in tasks:
                    p.join()

                print "Finished multiprocessing:", time.time() - start, 'secs'
                headers = ['Group','Subject', 'M/F'] + report.exptintervals.keys() + ['Stage']
                report.data = pd.DataFrame(q.values(), columns=headers)
                report.data.to_csv(outputfile, index=False) #cache
                print report.data
            df_report = report.printMissingExpts()
            df_report.sort_values(by='Progress', inplace=True, ascending=False)
            #Get expts
            df_expts = report.getExptCollection()
            print df_expts.head()

            # reactive loading to app
            op.app.layout = op.participants_layout(df, df_expts, df_report)
            op.app.run_server(debug=True, port=8089)
        else:
            print "No subjects found - Check PROJECT CODE is correct"
        xnat.conn.disconnect()
        print("FINISHED")

    else:
        print "Failed to connect"
