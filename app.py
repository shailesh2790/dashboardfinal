import dash
from dash import dcc, html, dash_table
from dash.dependencies import Input, Output, State
import pandas as pd
import plotly.express as px
import base64
import io
import fitz  # PyMuPDF for reading PDF files
import sqlite3

# Initialize the Dash app
app = dash.Dash(__name__)
app.title = "Interactive Dashboard"

# Expose the Flask server instance for WSGI
server = app.server

# Set up the SQLite database
conn = sqlite3.connect('uploaded_files.db')
c = conn.cursor()
c.execute('''
          CREATE TABLE IF NOT EXISTS files
          (id INTEGER PRIMARY KEY AUTOINCREMENT,
          filename TEXT,
          content BLOB)
          ''')
conn.commit()
conn.close()

app.layout = html.Div([
    html.H1("Interactive Dashboard", style={'text-align': 'center'}),

    dcc.Upload(
        id='upload-data',
        children=html.Div([
            'Drag and Drop or ',
            html.A('Select Files')
        ]),
        style={
            'width': '100%',
            'height': '60px',
            'lineHeight': '60px',
            'borderWidth': '1px',
            'borderStyle': 'dashed',
            'borderRadius': '5px',
            'textAlign': 'center',
            'margin': '10px'
        },
        multiple=False
    ),

    html.Div(id='output-data-upload'),

    html.H2("Statistics", style={'text-align': 'center'}),
    html.Div(id='stats', style={'display': 'flex', 'flexWrap': 'wrap', 'justify-content': 'space-around'}),

    html.H2("Data Table", style={'text-align': 'center'}),
    dash_table.DataTable(id='data-table', style_table={'overflowX': 'auto'}),

    html.H2("Visualizations", style={'text-align': 'center'}),
    html.Div([
        html.Label("X-axis Column"),
        dcc.Dropdown(id='xaxis-column', placeholder="Select X-axis Column"),
    ], style={'width': '48%', 'display': 'inline-block', 'padding': '0 20px'}),
    html.Div([
        html.Label("Y-axis Column"),
        dcc.Dropdown(id='yaxis-column', placeholder="Select Y-axis Column"),
    ], style={'width': '48%', 'display': 'inline-block', 'padding': '0 20px'}),
    html.Div([
        html.Label("Visualization Type"),
        dcc.Dropdown(id='visualization-type', options=[
            {'label': 'Bar Plot', 'value': 'bar'},
            {'label': 'Line Plot', 'value': 'line'},
            {'label': 'Scatter Plot', 'value': 'scatter'},
            {'label': 'Histogram', 'value': 'histogram'},
        ], value='bar'),
    ], style={'width': '48%', 'display': 'inline-block', 'padding': '20px'}),

    dcc.Graph(id='data-visualization')
])

def parse_contents(contents, filename):
    content_type, content_string = contents.split(',')
    decoded = base64.b64decode(content_string)
    try:
        if 'xls' in filename:
            df = pd.read_excel(io.BytesIO(decoded))
        elif 'csv' in filename:
            df = pd.read_csv(io.BytesIO(decoded))
        elif 'pdf' in filename:
            text = ''
            with fitz.open(stream=io.BytesIO(decoded), filetype="pdf") as doc:
                for page in doc:
                    text += page.get_text()
            df = pd.DataFrame({'Content': [text]})
        else:
            return None
    except Exception as e:
        print(e)
        return None
    return df

@app.callback(
    [Output('data-table', 'data'),
     Output('data-table', 'columns'),
     Output('xaxis-column', 'options'),
     Output('yaxis-column', 'options'),
     Output('stats', 'children')],
    [Input('upload-data', 'contents')],
    [State('upload-data', 'filename')]
)
def update_table(contents, filename):
    if contents is not None:
        df = parse_contents(contents, filename)
        if df is None:
            return [], [], [], [], ""

        # Store file in the database
        conn = sqlite3.connect('uploaded_files.db')
        c = conn.cursor()
        c.execute('INSERT INTO files (filename, content) VALUES (?, ?)', (filename, contents))
        conn.commit()
        conn.close()

        # Filter out unnamed columns and irrelevant columns
        df = df.loc[:, ~df.columns.str.contains('^Unnamed')]

        columns = [{'name': col, 'id': col} for col in df.columns]
        data = df.to_dict('records')
        options = [{'label': col, 'value': col} for col in df.columns]

        # Define irrelevant columns
        irrelevant_columns = ['Sr No', 'Serial No', 'ID']  # add other irrelevant column names if needed

        # Calculate statistics for relevant columns only
        stats = []
        relevant_columns = [col for col in df.columns if col not in irrelevant_columns]

        for col in relevant_columns:
            if df[col].dtype in ['int64', 'float64']:
                stats.append(html.Div([
                    html.Div(f"Mean of {col}", style={'font-weight': 'bold', 'text-align': 'center'}),
                    html.Div(f"{df[col].mean():.2f}", style={'color': 'blue', 'font-size': '20px', 'text-align': 'center'})
                ], style={'padding': '10px', 'border': '1px solid #ccc', 'border-radius': '5px', 'width': '200px', 'margin': '10px'}))
                
                stats.append(html.Div([
                    html.Div(f"Max of {col}", style={'font-weight': 'bold', 'text-align': 'center'}),
                    html.Div(f"{df[col].max():.2f}", style={'color': 'green', 'font-size': '20px', 'text-align': 'center'})
                ], style={'padding': '10px', 'border': '1px solid #ccc', 'border-radius': '5px', 'width': '200px', 'margin': '10px'}))

                stats.append(html.Div([
                    html.Div(f"Min of {col}", style={'font-weight': 'bold', 'text-align': 'center'}),
                    html.Div(f"{df[col].min():.2f}", style={'color': 'red', 'font-size': '20px', 'text-align': 'center'})
                ], style={'padding': '10px', 'border': '1px solid #ccc', 'border-radius': '5px', 'width': '200px', 'margin': '10px'}))

                stats.append(html.Div([
                    html.Div(f"Sum of {col}", style={'font-weight': 'bold', 'text-align': 'center'}),
                    html.Div(f"{df[col].sum():.2f}", style={'color': 'purple', 'font-size': '20px', 'text-align': 'center'})
                ], style={'padding': '10px', 'border': '1px solid #ccc', 'border-radius': '5px', 'width': '200px', 'margin': '10px'}))

        return data, columns, options, options, stats

    return [], [], [], [], ""

@app.callback(
    Output('data-visualization', 'figure'),
    [Input('visualization-type', 'value'),
     Input('xaxis-column', 'value'),
     Input('yaxis-column', 'value')],
    [State('upload-data', 'contents'),
     State('upload-data', 'filename')]
)
def update_graph(visualization_type, xaxis_column, yaxis_column, contents, filename):
    if contents is not None and xaxis_column is not None and yaxis_column is not None:
        df = parse_contents(contents, filename)
        if df is None:
            return {}

        if visualization_type == 'bar':
            fig = px.bar(df, x=xaxis_column, y=yaxis_column, color=xaxis_column)
        elif visualization_type == 'line':
            fig = px.line(df, x=xaxis_column, y=yaxis_column, color=xaxis_column)
        elif visualization_type == 'scatter':
            fig = px.scatter(df, x=xaxis_column, y=yaxis_column, color=xaxis_column)
        elif visualization_type == 'histogram':
            fig = px.histogram(df, x=xaxis_column)
        else:
            fig = {}

        return fig

    return {}

if __name__ == '__main__':
    app.run_server(debug=True)
