#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pyparsing as pp

from pyparsing_ext import *

# helpers:
def enumeratedItems(baseExpr=None, form='[1]', **min_max):
    if form is None:
        form = '[1]'
    if '1' in form:
        no = pp.Regex(re.escape(form).replace('1','(?P<no>\\d+)')) #.setParseAction(lambda x:x.no)
    else:
        no = pp.Regex(re.escape(form))
    # no.suppress()
    if 'exact' in min_max and min_max['exact'] > 0:
        max_ = min_ = exact
    else:
        min_ = min_max.get('min', 0)
        max_ = min_max.get('max', None)
    if baseExpr is None:
        return (pp.Group(no + pp.SkipTo(pp.StringEnd() | no).setParseAction(_strip()))) * (min_, max_)
    else:
        return (pp.Group(no + baseExpr.setParseAction(_strip()))) * (min_, max_)

def _strip(ch=None):
    if ch is None:
        return lambda s, l, t: t[0].strip()
    else:
        return lambda s, l, t: t[0].strip(ch)


def delimitedMatrix(baseExpr=pp.Word(pp.alphanums), ch1=',', ch2=';'):
    r'''works like delimitedList
    exmpale:
    'a b\nc d' => [['a', 'b'], ['c', 'd']]
    '''
    if ch1 == ch2:
        raise Exception('make sure ch1 != ch2')
    if isinstance(ch1, str):
        if ch1 is '':
            raise Exception('make sure ch1 is not empty')
        if iswhite(ch1):
            ch1 = pp.Literal(ch1).leaveWhitespace()
        else:
            ch1 = pp.Literal(ch1)
    if isinstance(ch2, str):
        if ch2 is '':
            raise Exception('make sure ch2 is not empty')
        if iswhite(ch2):
            ch2 = pp.Literal(ch2).leaveWhitespace()
        else:
            ch2 = pp.Literal(ch2)
    return pp.delimitedList(pp.Group(pp.delimitedList(baseExpr, ch1.suppress())), ch2.suppress())


# need to be improved
class MixedExpression(pp.ParseElementEnhance):
    '''MixedExpression, oop verion of mixedExpression
    '''
    def __init__(self, baseExpr, opList=[], lpar=LPAREN, rpar=RPAREN, *args, **kwargs):
        super(MixedExpression, self).__init__(baseExpr, *args, **kwargs)
        self.baseExpr = baseExpr
        self.opList = opList
        self.lpar = lpar
        self.rpar = rpar
        self.expr = pp.infixNotation(baseExpr, opList, lpar, rpar)

    def enableIndex(self, action=IndexOpAction):
        # start:stop:step
        EXP = pp.Forward()
        SLICE = pp.Optional(EXP)('start') + COLON + pp.Optional(EXP)('stop') + pp.Optional(COLON + pp.Optional(EXP)('step'))
        indexop = LBRACK + (SLICE('slice') | EXP('index')) + RBRACK
        indexop.setParseAction(action)
        self.opList.insert(0, indexop)
        self.expr <<= pp.infixNotation(EXP, self.opList, self.lpar, self.rpar)

    def enableCall(self, action=CallOpAction):
        EXP = self.expr
        KWARG = IDEN + pp.Suppress('=') + EXP
        # STAR = pp.Suppress('*') + EXP, DBLSTAR = pp.Suppress('**') + EXP
        callop = LPAREN + pp.Optional(pp.delimitedList(EXP))('args') + pp.Optional(pp.delimitedList(KWARG))('kwargs') + RPAREN
        callop.setParseAction(action)
        self.opList.insert(0, callop)
        self.expr <<= pp.infixNotation(self.baseExpr, self.opList, self.lpar, self.rpar)

    def enableDot(self, action=DotOpAction):
        EXP = self.expr
        dotop = pp.Suppress('.') + IDEN('attr')
        dotop.setParseAction(action)
        self.opList.insert(0, dotop)
        self.expr <<= pp.infixNotation(self.baseExpr, self.opList, self.lpar, self.rpar)


    def enableAll(self, actions=None):
        self.enableIndex()
        self.enableCall()
        self.enableDot()


def mixedExpression(baseExpr, func=None, flag=False, opList=[], lpar=LPAREN, rpar=RPAREN):
    """Mixed expression, more powerful then operatorPrecedence

    It calls operatorPrecedence.
    
    Arguments:
        func: function of baseExpr (can be distincted by first token)
        flag: for parsing the expressions: a(x) a[x] a.x
        others are same with infixedNotation

    Return:
        ParserElementEnhance

    
    Example:
    ------
    integer = pyparsing_common.signed_integer
    varname = pyparsing_common.identifier

    arith_expr = infixNotation(integer | varname,
        [
        ('-', 1, opAssoc.RIGHT),
        (oneOf('* /'), 2, opAssoc.LEFT),
        (oneOf('+ -'), 2, opAssoc.LEFT),
        ])

    arith_expr.runTests('''
        5+3*6
        (5+3)*6
        -2--11
        ''', fullDump=False)
    def func(EXP):
        return pp.Group('<' + EXP + ',' + EXP +'>')| pp.Group('||' + EXP + '||') | pp.Group('|' + EXP + '|') | pp.Group(IDEN + '(' + pp.delimitedList(EXP) + ')')
    baseExpr = interger | varname
    EXP = mixedExpression(baseExpr, func, arithOplist)

    """
    
    EXP = pp.Forward()
    if flag:
        # expression as a[d].b(c)
        SLICE = pp.Optional(EXP)('start') + COLON + pp.Optional(EXP)('stop') + pp.Optional(COLON + pp.Optional(EXP)('step'))
        indexop = LBRACK + (SLICE('slice') | EXP('index')) + RBRACK
        indexop.setParseAction(IndexOpAction) # handle with x[y]
        KWARG = IDEN + pp.Suppress('=') + EXP
        # STAR = pp.Suppress('*') + EXP; DBLSTAR = pp.Suppress('**') + EXP
        callop = LPAREN + pp.Optional(pp.delimitedList(EXP))('args') + pp.Optional(pp.delimitedList(KWARG))('kwargs') + RPAREN
        callop.setParseAction(CallOpAction)  # handle with f(x)
        dotop = pp.Suppress('.') + IDEN('attr')
        dotop.setParseAction(DotOpAction)    # handle with x.y
        opList.insert(0, (indexop | callop | dotop, 1, pp.opAssoc.LEFT, ICDAction))
    
    if func:
        if isinstance(func, pp.ParserElement):
            f = pp.Group(func + LPAREN + pp.delimitedList(EXP) + RPAREN)
            block = f | baseExpr
        else:  # func is callable
            block = func(EXP) | baseExpr
        EXP <<= pp.infixNotation(block, opList, lpar, rpar)
    else:
        EXP <<= pp.infixNotation(baseExpr, opList, lpar, rpar)
    return EXP



def logicterm(constant=DIGIT, variable=IDEN, function=IDEN, lambdaterm=False):
    # f(x,y...) | const | x
    if lambdaterm:
        function = function | lambdaterm(variable, lambdaKeyword='lambda')
    t = pp.Forward()
    t <<= (function('function') + LPAREN + pp.delimitedList(t)('args') + RPAREN).setParseAction(FunctionAction) | (constant | variable).setParseAction(AtomAction)
    return t


def lambdaterm(variable=IDEN, lambdaKeyword='lambda'):
    # lambda variable: expression
    t = pp.Forward()
    t <<= pp.Suppress(lambdaKeyword) + pp.delimitedList(variable)('args') + (t | logicterm(constant=DIGIT, variable=IDEN, function=None))('term')
    t.setParseAction(LambdaAction)
    return t

integer = pp.pyparsing_common.signed_integer
varname = pp.pyparsing_common.identifier

arithOplist = [('-', 1, pp.opAssoc.RIGHT),
    (pp.oneOf('* /'), 2, pp.opAssoc.LEFT),
    (pp.oneOf('+ -'), 2, pp.opAssoc.LEFT)]

def func(EXP):
    return pp.Group('<' + EXP + pp.Suppress(',') + EXP +'>')| pp.Group('||' + EXP + '||') | pp.Group('|' + EXP + '|') | pp.Group(IDEN + '(' + pp.delimitedList(EXP) + ')')
baseExpr = integer | varname
EXP = mixedExpression(baseExpr, func=func, opList=arithOplist)

a = EXP.parseString('5*5+<4,5>')
print(a)
