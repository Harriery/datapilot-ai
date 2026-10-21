"""Bounded, non-executing interpretation of recorded pandas expressions.

No column semantics, data access, eval, or inference from notebook section names.
An unsupported expression is unknown, never silently treated as unfiltered df.
"""
from __future__ import annotations

import ast
import json
import math
import re


class UnsupportedObservation(ValueError):
    pass


def literal(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, (str, int, float, bool, type(None))):
        if isinstance(node.value, float) and not math.isfinite(node.value):
            raise UnsupportedObservation('nonfinite constant')
        return node.value
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.UAdd)):
        value = literal(node.operand)
        if type(value) not in (int, float):
            raise UnsupportedObservation('nonnumeric sign')
        return -value if isinstance(node.op, ast.USub) else value
    raise UnsupportedObservation('nonliteral argument')


def column(node):
    if isinstance(node, ast.Subscript) and isinstance(node.value, ast.Name) and node.value.id == 'df':
        value = literal(node.slice)
        if isinstance(value, str):
            return value
    raise UnsupportedObservation('column is not a direct df column')


def predicate(node):
    if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.BitAnd, ast.BitOr)):
        return {'op': 'and' if isinstance(node.op, ast.BitAnd) else 'or',
                'args': [predicate(node.left), predicate(node.right)]}
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Invert):
        return {'op': 'not', 'arg': predicate(node.operand)}
    if isinstance(node, ast.Compare) and len(node.ops) == len(node.comparators) == 1:
        operators = {ast.Eq:'eq', ast.NotEq:'ne', ast.Gt:'gt', ast.GtE:'ge', ast.Lt:'lt', ast.LtE:'le'}
        op = operators.get(type(node.ops[0]))
        if op:
            return {'op': op, 'column': column(node.left), 'value': literal(node.comparators[0])}
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and not node.args and not node.keywords:
        if node.func.attr in {'isna','isnull','notna','notnull'}:
            return {'op': 'missing' if node.func.attr in {'isna','isnull'} else 'present',
                    'column': column(node.func.value)}
    raise UnsupportedObservation('unsupported row predicate')


def selection(node):
    """Return the exact frame predicate and projection; never infer a population."""
    if isinstance(node, ast.Name) and node.id == 'df':
        return {'op':'all_current_df'}, None
    if not isinstance(node, ast.Subscript):
        raise UnsupportedObservation('unsupported frame or alias')
    key = node.slice
    if isinstance(node.value, ast.Attribute) and node.value.attr == 'loc':
        if not isinstance(node.value.value, ast.Name) or node.value.value.id != 'df':
            raise UnsupportedObservation('nested loc source')
        if isinstance(key, ast.Tuple) and len(key.elts) == 2:
            rows, cols = key.elts
            where = {'op':'all_current_df'} if isinstance(rows, ast.Slice) and rows.lower is rows.upper is rows.step is None else predicate(rows)
            return where, projection(cols)
        return predicate(key), None
    if isinstance(node.value, ast.Name) and node.value.id == 'df':
        if isinstance(key, (ast.Constant, ast.List, ast.Tuple)):
            return {'op':'all_current_df'}, projection(key)
        return predicate(key), None
    where, cols = selection(node.value)
    if cols is not None:
        raise UnsupportedObservation('nested series indexing')
    return where, projection(key)


def projection(node):
    nodes = node.elts if isinstance(node, (ast.List, ast.Tuple)) else [node]
    values = [literal(item) for item in nodes]
    if not values or not all(isinstance(item, str) for item in values):
        raise UnsupportedObservation('nonliteral projection')
    return values


def expression_contract(code: str) -> dict:
    try:
        tree = ast.parse(code)
        if len(list(ast.walk(tree))) > 160 or len(tree.body) != 1 or not isinstance(tree.body[0], ast.Expr):
            raise UnsupportedObservation('not one bounded expression')
        node = tree.body[0].value
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == 'print' and len(node.args) == 1 and not node.keywords:
            node = node.args[0]
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            raise UnsupportedObservation('unsupported terminal expression')
        operation = node.func.attr
        args = [literal(arg) for arg in node.args]
        kwargs = {item.arg: literal(item.value) for item in node.keywords}
        if None in kwargs or len(kwargs) != len(node.keywords):
            raise UnsupportedObservation('expanded arguments')
        base = node.func.value
        if operation == 'sum' and not args and not kwargs and isinstance(base, ast.Call) and isinstance(base.func, ast.Attribute) and base.func.attr in {'isna','isnull'} and not base.args and not base.keywords:
            operation = 'missing_count'; base = base.func.value
        elif operation == 'value_counts' and not args and set(kwargs) <= {'dropna','normalize','sort','ascending'} and all(type(value) is bool for value in kwargs.values()):
            operation = 'distribution'
        elif operation in {'head','tail'} and not kwargs and len(args) <= 1 and (not args or type(args[0]) is int and 0 < args[0] <= 100):
            kwargs['limit'] = args[0] if args else 5
            operation = 'preview_' + operation
        elif operation in {'max','min','mean','median','count','nunique'} and not args and not kwargs:
            pass
        else:
            raise UnsupportedObservation('unsupported aggregation')
        where, columns = selection(base)
        if not operation.startswith('preview_') and (columns is None or (operation != 'distribution' and len(columns) != 1)):
            raise UnsupportedObservation('measurement is not one literal column')
        return {'version':1, 'row_predicate':where, 'measured_columns':columns,
                'operation':operation, 'options':kwargs, 'frame':'current_notebook_df'}
    except (SyntaxError, ValueError, TypeError, RecursionError) as exc:
        return {'version':1, 'supported':False, 'reason':str(exc)[:120]}


def observation_contract(code: str, run: dict) -> dict:
    contract = expression_contract(code)
    if contract.get('supported') is False:
        return contract
    if run.get('success') is not True:
        return {'version':1, 'supported':False, 'reason':'execution did not succeed'}
    output = str(run.get('output') if run.get('output') is not None else '').strip()
    if not output:
        return {'version':1, 'supported':False, 'reason':'no recorded output'}
    if contract['operation'] == 'missing_count':
        match = re.fullmatch(r'([0-9]+)',output)
        if not match:
            match = re.fullmatch(r'(?:np\.)?int(?:32|64)\(([0-9]+)\)',output)
        if not match:
            # Single-column DataFrame .sum() prints a labelled Series.
            field = re.escape(contract['measured_columns'][0])
            match = re.fullmatch(field+r'\s+([0-9]+)\s*\ndtype:\s*(?:u?int(?:32|64)|Int64)',output)
        if not match:
            return {'version':1,'supported':False,'reason':'missing count output is not an unambiguous integer'}
        contract['result'] = int(match[1])
    else:
        # Preserve printed text as an observation, not a population statistic.
        contract['recorded_output'] = output[:1000]
        contract['output_truncated'] = len(output) > 1000 or '...' in output or '…' in output
    contract['supported'] = True
    return contract


def field_label(value):
    # Column labels are data, never Markdown or instructions.
    return '`' + str(value).replace('`','').replace('\n',' ').replace('\r',' ')[:120] + '`'


def predicate_label(where: dict, language='tr') -> str:
    op = where['op']
    if op == 'all_current_df':
        return {'tr':'notebook’taki mevcut df satırları','en':'rows in the current notebook df','nl':'rijen in de huidige notebook-df'}[language]
    if op in {'and','or'}:
        join = {'tr':{'and':' VE ','or':' VEYA '},'en':{'and':' AND ','or':' OR '},'nl':{'and':' EN ','or':' OF '}}[language][op]
        return '(' + join.join(predicate_label(item,language) for item in where['args']) + ')'
    if op == 'not':
        return {'tr':'DEĞİL ','en':'NOT ','nl':'NIET '}[language] + '(' + predicate_label(where['arg'],language) + ')'
    field = field_label(where['column'])
    if op in {'missing','present'}:
        return field + {'tr':{'missing':' eksik','present':' dolu'},'en':{'missing':' is missing','present':' is not missing'},'nl':{'missing':' ontbreekt','present':' ontbreekt niet'}}[language][op]
    symbol = {'eq':'=','ne':'≠','gt':'>','ge':'≥','lt':'<','le':'≤'}[op]
    return field + ' ' + symbol + ' ' + field_label(json.dumps(where['value'],ensure_ascii=False))


def observation_text(contract: dict, language='tr') -> str:
    group = predicate_label(contract['row_predicate'],language)
    cols = ', '.join(field_label(x) for x in contract.get('measured_columns') or [])
    op = contract['operation']
    if op == 'missing_count':
        count = contract['result']
        return {
            'tr':f'Seçilen satırlar: {group}. Ölçülen sütun: {cols}. Bu gruptaki kayıtlı eksik değer sayısı: **{count}**.',
            'en':f'Selected rows: {group}. Measured column: {cols}. Recorded missing-value count in this group: **{count}**.',
            'nl':f'Geselecteerde rijen: {group}. Gemeten kolom: {cols}. Opgeslagen aantal ontbrekende waarden in deze groep: **{count}**.',
        }[language]
    name = {'distribution':{'tr':'değer dağılımı','en':'value distribution','nl':'waardeverdeling'},
            'preview_head':{'tr':'ilk satır örnekleri','en':'first-row examples','nl':'eerste voorbeeldrijen'},
            'preview_tail':{'tr':'son satır örnekleri','en':'last-row examples','nl':'laatste voorbeeldrijen'}}.get(op, {'tr':op,'en':op,'nl':op})[language]
    heading = {'tr':f'Seçilen satırlar: {group}. İncelenen sütunlar: {cols or "tüm sütunlar"}. Kayıtlı çıktı: {name}.',
            'en':f'Selected rows: {group}. Inspected columns: {cols or "all columns"}. Recorded output: {name}.',
            'nl':f'Geselecteerde rijen: {group}. Onderzochte kolommen: {cols or "alle kolommen"}. Opgeslagen resultaat: {name}.'}[language]
    output = contract.get('recorded_output','')
    lines = output.splitlines()
    shown = ' / '.join(field_label(line[:80]) for line in lines[:6])
    if shown:
        heading += {'tr':' Görünen çıktı: ','en':' Visible output: ','nl':' Zichtbaar resultaat: '}[language] + shown
    if len(lines)>6 or contract.get('output_truncated'):
        heading += {'tr':' (Gösterim kısaltıldı.)','en':' (Display shortened.)','nl':' (Weergave ingekort.)'}[language]
    if op=='distribution':
        heading += {'tr':' Eksikler dağılıma yalnız dropna=False kullanıldıysa dahildir.',
                    'en':' Missing values are included only with dropna=False.',
                    'nl':' Ontbrekende waarden tellen alleen mee bij dropna=False.'}[language]
    if op.startswith('preview_'):
        heading += {'tr':' Bu bir satır örneğidir; bütün grup hakkında hüküm vermez.',
                    'en':' This is a row preview, not proof about the whole group.',
                    'nl':' Dit is een rijvoorbeeld, geen bewijs over de hele groep.'}[language]
    return heading
