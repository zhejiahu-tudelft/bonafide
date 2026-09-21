"""Consistent standalone research chart styling."""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
NAVY='#142b45'; TEAL='#087f8c'; GOLD='#dd9a27'; RED='#b54847'
def configure():
    plt.rcParams.update({'figure.dpi':150,'savefig.dpi':180,'font.family':'DejaVu Sans','font.size':10,
        'axes.spines.top':False,'axes.spines.right':False,'axes.labelcolor':NAVY,'text.color':NAVY,
        'axes.titleweight':'bold','axes.titlesize':13,'axes.grid':True,'grid.alpha':.16,
        'axes.axisbelow':True,'figure.facecolor':'white'})
def save(fig,path):
    fig.tight_layout();fig.savefig(path,bbox_inches='tight');plt.close(fig)
