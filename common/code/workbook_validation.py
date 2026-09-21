"""Evaluate the small arithmetic formula subset used by our research workbooks.

Supports arithmetic, cell references, quoted sheet names and same-sheet SUM
ranges. This is an independent audit helper, not a general Excel replacement.
It rejects unknown functions instead of silently accepting cached results.
"""
import ast, math, operator, re
from functools import lru_cache
from openpyxl.utils.cell import range_boundaries, get_column_letter

OPS={ast.Add:operator.add,ast.Sub:operator.sub,ast.Mult:operator.mul,
     ast.Div:operator.truediv,ast.Pow:operator.pow}

def arithmetic(expr):
    def visit(node):
        if isinstance(node,ast.Expression): return visit(node.body)
        if isinstance(node,ast.Constant) and isinstance(node.value,(int,float)): return node.value
        if isinstance(node,ast.BinOp) and type(node.op) in OPS: return OPS[type(node.op)](visit(node.left),visit(node.right))
        if isinstance(node,ast.UnaryOp) and isinstance(node.op,(ast.UAdd,ast.USub)):
            return visit(node.operand)*(1 if isinstance(node.op,ast.UAdd) else -1)
        raise ValueError(f'Unsupported arithmetic node: {ast.dump(node)}')
    return visit(ast.parse(expr,mode='eval'))

def validate_formula_caches(formulas,cached):
    ref=re.compile(r"(?<![A-Za-z0-9_])(?:'([^']+)'!)?(\$?[A-Z]{1,3}\$?\d+)(?![A-Za-z0-9_])")
    @lru_cache(None)
    def cell(sheet,address):
        v=formulas[sheet][address].value
        if not isinstance(v,str) or not v.startswith('='):
            if not isinstance(v,(int,float)): raise ValueError(f'Non-numeric precedent {sheet}!{address}: {v}')
            return v
        expr=v[1:]
        def total(m):
            c1,r1,c2,r2=range_boundaries(m[1].replace('$',''))
            return str(sum(cell(sheet,f'{get_column_letter(c)}{r}') for c in range(c1,c2+1) for r in range(r1,r2+1)))
        expr=re.sub(r'SUM\((\$?[A-Z]+\$?\d+:\$?[A-Z]+\$?\d+)\)',total,expr)
        expr=ref.sub(lambda m:'('+repr(cell(m[1] or sheet,m[2].replace('$','')))+')',expr)
        return arithmetic(expr.replace('^','**'))
    checked=0
    for sheet in formulas:
        for row in sheet:
            for c in row:
                if c.data_type!='f': continue
                calculated=cell(sheet.title,c.coordinate);stored=cached[sheet.title][c.coordinate].value
                if not isinstance(stored,(int,float)) or not math.isclose(calculated,stored,rel_tol=1e-9,abs_tol=1e-8):
                    raise AssertionError(f'{sheet.title}!{c.coordinate}: formula {calculated} != cache {stored}')
                checked+=1
    return checked
