import theanoxcomp
import tensorlog
import declare
import testtensorlog
import matrixdb
import parser
import mutil

import unittest
import sys
import theano

TESTED_COMPILERS = [
#  theanoxcomp.DenseMatDenseMsgCrossCompiler,
  theanoxcomp.SparseMatDenseMsgCrossCompiler,
]

class TestXCSmallProofs(testtensorlog.TestSmallProofs):

  def test_if(self):
    self.xcomp_check(['p(X,Y):-spouse(X,Y).'], 'p(i,o)', 'william', {'susan':1.0})

  def testFailure(self):
    self.xcomp_check(['p(X,Y):-spouse(X,Y).'], 'p(i,o)', 'lottie', {matrixdb.NULL_ENTITY_NAME:1.0})

  def test_reverse_if(self):
    self.xcomp_check(['p(X,Y):-sister(Y,X).'], 'p(i,o)', 'rachel', {'william':1.0})

  def test_or(self):
    self.xcomp_check(['p(X,Y):-spouse(X,Y).', 'p(X,Y):-sister(X,Y).'], 'p(i,o)', 'william',
            {'susan':1.0, 'rachel':1.0, 'lottie':1.0, 'sarah':1.0})

  def test_chain(self):
    self.xcomp_check(['p(X,Z):-spouse(X,Y),sister(Y,Z).'], 'p(i,o)', 'susan',
            {'rachel':1.0, 'lottie':1.0, 'sarah':1.0})
    self.xcomp_check(['p(X,Z):-sister(X,Y),child(Y,Z).'], 'p(i,o)', 'william',
            {'charlotte':1.0, 'lucas':1.0, 'poppy':1.0, 'caroline':1.0, 'elizabeth':1.0})

  def test_mid(self):
    self.xcomp_check(['p(X,Y):-sister(X,Y),child(Y,Z).'], 'p(i,o)', 'william',
            {'sarah': 1.0, 'rachel': 2.0, 'lottie': 2.0})

  def test_nest(self):
    self.xcomp_check(['s(X,Y):-spouse(X,Y).','t(X,Z):-spouse(X,Y),s(Y,Z).'], 't(i,o)', 'susan', {'susan': 1.0})

  def test_back1(self):
    self.xcomp_check(['p(X,Y):-spouse(X,Y),sister(X,Z).'], 'p(i,o)', 'william', {'susan': 3.0})

  def test_back2(self):
    self.xcomp_check(['p(X,Y):-spouse(X,Y),sister(X,Z1),sister(X,Z2).'],'p(i,o)','william',{'susan': 9.0})

  def test_rec1(self):
    tensorlog.DEFAULT_MAXDEPTH=4
    self.inference_check(['p(X,Y):-spouse(X,Y).','p(X,Y):-p(Y,X).'], 'p(i,o)','william',{'susan': 5.0})
    tensorlog.DEFAULT_MAXDEPTH=10
    self.inference_check(['p(X,Y):-spouse(X,Y).','p(X,Y):-p(Y,X).'], 'p(i,o)','william',{'susan': 11.0})

  def test_const_output(self):
    self.xcomp_check(['sis(X,W):-assign(W,william),child(X,Y).'], 'sis(i,o)', 'sarah', {'william': 1.0})
    self.xcomp_check(['sis(X,W):-assign(W,william),child(X,Y).'], 'sis(i,o)', 'lottie', {'william': 2.0})

  def test_const_chain1(self):
    self.xcomp_check(['p(X,S) :- assign(S,susan),sister(X,Y),child(Y,Z).'],'p(i,o)','william',{'susan': 5.0})

  def test_const_chain2(self):
    self.xcomp_check(['p(X,Pos) :- assign(Pos,pos),child(X,Y),young(Y).'],'p(i,o)','sarah',{'pos':1.0})
    self.xcomp_check(['p(X,Pos) :- assign(Pos,pos),child(X,Y),young(Y).'],'p(i,o)','lottie',{'pos':2.0})

  def test_alt_chain(self):
    self.xcomp_check(['p(X,W) :- spouse(X,W),sister(X,Y),child(Y,Z).'],'p(i,o)','william',{'susan': 5.0})
    pass

  def test_proppr1(self):
    w = 7*self.db.onehot('r1')+3*self.db.onehot('r2')
    self.proppr_xcomp_check(w,['p(X,Y):-sister(X,Y) {r1}.','p(X,Y):-spouse(X,Y) {r2}.'],'p(i,o)',
                'william', {'sarah': 7.0, 'rachel': 7.0, 'lottie': 7.0, 'susan': 3.0})

  def test_proppr2(self):
    w = 3*self.db.onehot('r2')
    self.proppr_xcomp_check(w,['p(X,Y):-spouse(Y,X) {r2}.'],'p(i,o)',
                'susan', {'william': 3.0})

  def test_reuse1(self):
    self.xcomp_check(['p(X,Y) :- r(X,Z),r(Z,Y).', 'r(X,Y):-spouse(X,Y).'], 'p(i,o)', 'william',
            {'william':1.0})


  def xcomp_check(self,ruleStrings,mode_string,input_symbol,expected_result_dict):
    self._xcomp_check('vanilla',None,ruleStrings,mode_string,input_symbol,expected_result_dict)

  def proppr_xcomp_check(self,weightVec,ruleStrings,mode_string,input_symbol,expected_result_dict):
    self._xcomp_check('proppr',weightVec,ruleStrings,mode_string,input_symbol,expected_result_dict)

  def _xcomp_check(self,progType,weightVec,ruleStrings,mode_string,input_symbol,expected_result_dict):
    # run the base class check to see that the inference is correct
    if progType=='proppr':
      self.proppr_inference_check(weightVec,ruleStrings,mode_string,input_symbol,expected_result_dict)
    else:
      self.inference_check(ruleStrings,mode_string,input_symbol,expected_result_dict)
    # setup the next round of tests by compiling a tensorlog
    # Program - this code is lifted from the testtensorlog
    # inference routines
    print 'xcomp inference for mode',mode_string,'on input',input_symbol
    testtensorlog.softmax_normalize(expected_result_dict)
    rules = parser.RuleCollection()
    for r in ruleStrings:
      rules.add(parser.Parser.parseRule(r))
    if progType=='proppr':
      prog = tensorlog.ProPPRProgram(db=self.db,rules=rules,weights=weightVec)
    else:
      prog = tensorlog.Program(db=self.db,rules=rules)
    mode = declare.ModeDeclaration(mode_string)
    tlogFun = prog.compile(mode)
    for compilerClass in TESTED_COMPILERS:
      #cross-compile the function
      xc = compilerClass(prog.db)
      xc.compile(tlogFun)
      # evaluate the theano function and get the output y
      xc.show()
      print '== performing theano eval with',compilerClass,'=='
      ys = xc.evalSymbols([input_symbol])
      y = ys[0]
      # theano output will a be (probably dense) message, so
      # just compare that maximal elements from these two dicts
      # are the same
      self.check_maxes_in_dicts(self.db.rowAsSymbolDict(y), expected_result_dict)
      print '== theano eval checks passed =='
#      # cycle through the possible things to differentiate against
#      # TODO move into gradient check
#      for x in xc.subexprCacheVarBindings:
#        #print '== grad with',compilerClass,'wrt',x,'=='
#        pseudo_cost = xc.expr.sum()
#        gx, = theano.grad(pseudo_cost,[x])
#        #print 'grad pseudo_cost wrt',x,theano.pp(gx)
#        train = theano.function(inputs=xc.exprArgs, outputs=[pseudo_cost,xc.expr],updates=[(x, (x - 0.1*gx))])
#        #print '== update function =='
#        #theano.printing.debugprint(train)
#      print '== theano gradients computed =='


  def check_maxes_in_dicts(self,actual,expected):
    def maximalElements(d):
      m = max(d.values())
      return set(k for k in d if d[k]==m)
    actualMaxes = maximalElements(actual)
    expectedMaxes = maximalElements(expected)
    print 'actual',actualMaxes,'expected',expectedMaxes
    for a in actualMaxes:
      self.assertTrue(a in expectedMaxes)
    for a in expectedMaxes:
      self.assertTrue(a in actualMaxes)


class TestXCGrad(testtensorlog.TestGrad):

  def setUp(self):
    self.db = matrixdb.MatrixDB.loadFile('test/fam.cfacts')

  def test_if(self):
    rules = ['p(X,Y):-sister(X,Y).']
    mode = 'p(i,o)'
    params = [('sister',2)]
    self.xgrad_check(rules, mode, params,
                     [('william',['rachel','sarah'])],
                     {'sister(william,rachel)': +1,'sister(william,sarah)': +1,'sister(william,lottie)': -1})
#    self.xgrad_check(rules, mode, params,
#                     [('william',['lottie'])],
#                     {'sister(william,rachel)': -1,'sister(william,lottie)': +1})

  def test_if2(self):
    pass
#  rules = ['p(X,Y):-sister(X,Y).']
#  mode = 'p(i,o)'
#  params = [('sister',2)]
#  self.xgrad_check(rules, mode, params,
#       [('william',['rachel','sarah']), ('william',['rachel','sarah'])],
#       {'sister(william,rachel)': +1,'sister(william,sarah)': +1,'sister(william,lottie)': -1})
#  self.xgrad_check(rules, mode, params,
#       [('william',['lottie']), ('william',['lottie'])],
#       {'sister(william,rachel)': -1,'sister(william,lottie)': +1})
#
  def test_reverse_if(self):
    pass
#  rules = ['p(X,Y):-parent(Y,X).']
#  mode = 'p(i,o)'
#  params = [('parent',2)]
#  self.xgrad_check(rules, mode, params,
#       [('lottie',['charlotte'])],
#       {'parent(charlotte,lottie)': +1,'parent(lucas,lottie)': -1})
#
  def test_chain1(self):
    pass
#  rules = ['p(X,Z):-sister(X,Y),child(Y,Z).']
#  mode = 'p(i,o)'
#  self.xgrad_check(rules,mode,
#       [('sister',2)],
#       [('william',['caroline','elizabeth'])],
#       {'sister(william,rachel)': +1,'sister(william,lottie)': -1})
#  self.xgrad_check(rules,mode,
#       [('child',2)],
#       [('william',['caroline','elizabeth'])],
#       {'child(rachel,elizabeth)': +1,'child(lottie,lucas)': -1})
#
#  self.xgrad_check(rules,mode,
#       [('child',2),('sister',2)],
#       [('william',['caroline','elizabeth'])],
#       {'child(rachel,elizabeth)': +1,'child(lottie,lucas)': -1, 'sister(william,rachel)': +1,'sister(william,lottie)': -1})
#
  def test_chain2(self):
    pass
#  rules =  = ['p(X,Z):-spouse(X,Y),sister(Y,Z).']
#  mode = 'p(i,o)'
#  self.xgrad_check(rules,mode,
#       [('sister',2)],
#       [('susan',['rachel'])],
#       {'sister(william,rachel)': +1,'sister(william,lottie)': -1})
#
#
  def test_printf(self):
    pass
#    rules = ['p(X,Z1):-printf(X,X1),spouse(X1,Y),printf(Y,Y1),sister(Y1,Z),printf(Z,Z1).']
#    mode = 'p(i,o)'
#    self.grad_check(rules,mode,
#             [('sister',2)],
#             [('susan',['rachel'])],
#             {'sister(william,rachel)': +1,'sister(william,lottie)': -1})
#

  def test_call1(self):
    pass
#  rules = ['q(X,Y):-sister(X,Y).','p(Z,W):-q(Z,W).']
#  mode = 'p(i,o)'
#  params = [('sister',2)]
#  self.xgrad_check(rules, mode, params,
#       [('william',['rachel','sarah'])],
#       {'sister(william,rachel)': +1,'sister(william,sarah)': +1,'sister(william,lottie)': -1})
#  self.xgrad_check(rules, mode, params,
#       [('william',['lottie'])],
#       {'sister(william,rachel)': -1,'sister(william,lottie)': +1})
#
  def test_call2(self):
    pass
#  rules = ['q(X,Y):-sister(X,Y).','p(Z,W):-r(Z,W).','r(Z,W):-q(Z,W).']
#  mode = 'p(i,o)'
#  params = [('sister',2)]
#  self.xgrad_check(rules, mode, params,
#       [('william',['rachel','sarah'])],
#       {'sister(william,rachel)': +1,'sister(william,sarah)': +1,'sister(william,lottie)': -1})
#  self.xgrad_check(rules, mode, params,
#       [('william',['lottie'])],
#       {'sister(william,rachel)': -1,'sister(william,lottie)': +1})
#
#
  def test_split(self):
    pass
#  rules = ['p(X,Y):-sister(X,Y),child(Y,Z),young(Z).']
#  mode = 'p(i,o)'
#  params = [('child',2)]
#  self.xgrad_check(rules, mode, params,
#       [('william',['lottie'])],
#       {'child(lottie,lucas)': +1,'child(lottie,charlotte)': +1,'child(sarah,poppy)': -1})
#  params = [('sister',2)]
#  self.xgrad_check(rules, mode, params,
#       [('william',['lottie'])],
#       {'sister(william,lottie)': +1,'sister(william,sarah)': -1})
#
  def test_or(self):
    pass
#  rules = ['p(X,Y):-child(X,Y).', 'p(X,Y):-sister(X,Y).']
#  mode = 'p(i,o)'
#  params = [('sister',2)]
#  self.xgrad_check(rules, mode, params,
#       [('william',['charlie','rachel'])],
#       {'sister(william,rachel)': +1,'sister(william,sarah)': -1,'sister(william,lottie)': -1})
#  params = [('child',2)]
#  self.xgrad_check(rules, mode, params,
#       [('william',['charlie','rachel'])],
#       {'child(william,charlie)': +1,'child(william,josh)': -1})
#  params = [('child',2),('sister',2)]
#  self.xgrad_check(rules, mode, params,
#       [('william',['charlie','rachel'])],
#       {'child(william,charlie)': +1,'child(william,josh)': -1,'sister(william,rachel)': +1,'sister(william,sarah)': -1})
#
#
  def test_weighted_vec(self):
    pass
#  rules = ['p(X,Y):-sister(X,Y),assign(R,r1),feat(R).','p(X,Y):-child(X,Y),assign(R,r2),feat(R).']
#  mode = 'p(i,o)'
#  params = [('sister',2)]
#  self.xgrad_check(rules, mode, params,
#       [('william',['rachel','charlie'])],
#       {'sister(william,rachel)': +1,'sister(william,sarah)': -1})
#  params = [('child',2)]
#  self.xgrad_check(rules, mode, params,
#       [('william',['rachel','charlie'])],
#       {'child(william,charlie)': +1,'child(william,josh)': -1})
#  params = [('feat',1)]
#  self.xgrad_check(rules, mode, params,
#       [('william',['josh','charlie'])],
#       {'feat(r1)': -1,'feat(r2)': +1})
#  self.xgrad_check(rules, mode, params,
#       [('william',['rachel','sarah','lottie'])],
#       {'feat(r1)': +1,'feat(r2)': -1})

  def xgrad_check(self,rule_strings,mode_string,params,xyPairs,expected):
    rules = testtensorlog.rules_from_strings(rule_strings)
    prog = tensorlog.Program(db=self.db,rules=rules)

    x,y = xyPairs[0]
    data = testtensorlog.DataBuffer(self.db)
    for x,ys in xyPairs:
      data.add_data_symbols(x,ys)
    print 'data.x =',data.get_x()
    print 'data.y =',data.get_y()
    mode = declare.ModeDeclaration(mode_string)
    tlogFun = prog.compile(mode)
    for compilerClass in TESTED_COMPILERS:
      xc = compilerClass(prog.db)
      xc.compile(tlogFun)
      loss = xc.evalLoss([data.get_x()],data.get_y(),params)
      print 'loss',loss

#    (prog,updates) = self.xgrad_updates(rule_strings,mode,params,xyPairs)
#    #put the gradients into a single fact-string-indexed dictionary
#    updates_with_string_keys = {}
#    for (functor,arity),up in updates.items():
#      #print 'up for',functor,arity,'is',up
#      up_dict = prog.db.matrixAsPredicateFacts(functor,arity,up)
#      #print 'up_dict',up_dict,'updates keys',updates.keys()
#      for fact,grad_of_fact in up_dict.items():
#        updates_with_string_keys[str(fact)] = grad_of_fact
#        self.check_directions(updates_with_string_keys,expected)

def xgrad_updates(self,rule_strings,mode,params,xyPairs):
  """
  rule_strings - a list of tensorlog rules to use with the db.
  mode_string - mode for the data.
  params - list of (functor,arity) pairs that gradients will be computed for
  xyPairs - list of pairs (x,[y1,..,yk]) such that the desired result for x is uniform dist over y's

  return (program,updates)
  """
  #build program
  rules = testtensorlog.rules_from_strings(rule_strings)
  prog = tensorlog.Program(db=self.db,rules=rules)
  #build dataset
  data = DataBuffer(self.db)
  for x,ys in xyPairs:
    data.add_data_symbols(x,ys)
  #mark params: should be pairs (functor,arity)
  prog.db.clearParamMarkings()
  for functor,arity in params:
    prog.db.markAsParam(functor,arity)
  #compute gradient
  learner = learn.OnePredFixedRateGDLearner(prog)
  updates = learner.crossEntropyGrad(mode,data.get_x(),data.get_y())
  return prog,updates


if __name__ == "__main__":
  unittest.main()
