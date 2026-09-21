"""Small, offline HTML report helpers shared across equity research projects."""
import base64
from html import escape
from pathlib import Path
import pandas as pd

def table(columns, rows, caption=None):
    frame=pd.DataFrame(rows,columns=columns)
    out='<div class="table-wrap">'+frame.to_html(index=False,escape=True,border=0,classes='research-table')+'</div>'
    if caption: out+='<p class="caption">'+escape(caption)+'</p>'
    return out

def embedded_chart(path,description):
    encoded=base64.b64encode(Path(path).read_bytes()).decode()
    return '<figure><img src="data:image/png;base64,'+encoded+'" alt="'+escape(description)+'"><figcaption>'+escape(description)+'</figcaption></figure>'

def number(value,decimals=1,suffix=''):
    if pd.isna(value): return '—'
    return f'{value:,.{decimals}f}{suffix}'

def percent(value,decimals=1): return number(100*value,decimals,'%')
