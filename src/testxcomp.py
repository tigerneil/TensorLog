import theanoxcomp 
import tensorlog
import declare
import testtensorlog
import learnxcomp as learnxc
import learn
import matrixdb
import parser
import mutil

import unittest
import sys
import theano

import funs
import ops

class TestXCGrad(testtensorlog.TestGrad):
    
    def testIf(self):
        rules = ['p(X,Y):-sister(X,Y).']
        mode = 'p(i,o)'  
        params = [('sister',2)] 
        self.xcGradCheck(rules, mode, params,
                       [('william',['rachel','sarah'])], 
                       {'sister(william,rachel)': +1,'sister(william,sarah)': +1,'sister(william,lottie)': -1})
        self.xcGradCheck(rules, mode, params, 
                       [('william',['lottie'])], 
                       {'sister(william,rachel)': -1,'sister(william,lottie)': +1})
    
    def xcGradCheck(self,ruleStrings,modeString,params,xyPairs,expected):
        """
        expected - dict mapping strings encoding facts to expected sign of the gradient
        """
        mode = declare.ModeDeclaration(modeString)
        
        #(prog,updates) = self.gradUpdates(ruleStrings,mode,params,xyPairs)
        # expanding:
        
                #build program
        rules = parser.RuleCollection()
        for r in ruleStrings:
            rules.add(parser.Parser.parseRule(r))
        prog = tensorlog.Program(db=self.db,rules=rules)
        #build dataset
        data = testtensorlog.DataBuffer(self.db)
        for x,ys in xyPairs:
            data.addDataSymbols(x,ys)
        #mark params: should be pairs (functor,arity)
        prog.db.clearParamMarkings()
        for functor,arity in params:
            prog.db.markAsParam(functor,arity)
        #compute gradient
        learner = learnxc.XLearner(prog)
        P = learner.predict(mode,data.getX())
        print "Y\n",data.getY()
        print "Pth\n",type(P),P
        PTL=learn.OnePredFixedRateGDLearner(prog,epochs=5).predict(mode,data.getX())
        print "PTL\n",type(PTL),PTL
        
        updates = learner.crossEntropyGrad(mode,data.getX(),data.getY())
        
        #put the gradient into a single fact-string-indexed dictionary
        updatesWithStringKeys = {}
        for (functor,arity),up in updates.items():
            #print 'up for',functor,arity,'is',up
            upDict = prog.db.matrixAsPredicateFacts(functor,arity,up)
            #print 'upDict',upDict,'updates keys',updates.keys()
            for fact,gradOfFact in upDict.items():
                updatesWithStringKeys[str(fact)] = gradOfFact
        self.checkDirections(updatesWithStringKeys,expected)
    

class TestXCSmallProofs(testtensorlog.TestSmallProofs):
    
    def testIf(self):
        self.xcompCheck(['p(X,Y):-spouse(X,Y).'], 'p(i,o)', 'william', {'susan':1.0})
        pass

    def testFailure(self):
        self.xcompCheck(['p(X,Y):-spouse(X,Y).'], 'p(i,o)', 'lottie', {matrixdb.NULL_ENTITY_NAME:1.0})
        pass

    def testRevIf(self):
        self.xcompCheck(['p(X,Y):-sister(Y,X).'], 'p(i,o)', 'rachel', {'william':1.0})
        pass

    def testOr(self):
        self.xcompCheck(['p(X,Y):-spouse(X,Y).', 'p(X,Y):-sister(X,Y).'], 'p(i,o)', 'william', 
                        {'susan':1.0, 'rachel':1.0, 'lottie':1.0, 'sarah':1.0})
        pass

    def testChain(self):
        self.xcompCheck(['p(X,Z):-spouse(X,Y),sister(Y,Z).'], 'p(i,o)', 'susan', 
                        {'rachel':1.0, 'lottie':1.0, 'sarah':1.0})
        self.xcompCheck(['p(X,Z):-sister(X,Y),child(Y,Z).'], 'p(i,o)', 'william', 
                        {'charlotte':1.0, 'lucas':1.0, 'poppy':1.0, 'caroline':1.0, 'elizabeth':1.0})
        pass

    def testMid(self):
        self.xcompCheck(['p(X,Y):-sister(X,Y),child(Y,Z).'], 'p(i,o)', 'william', 
                        {'sarah': 1.0, 'rachel': 2.0, 'lottie': 2.0})
        pass

    def testNest(self):
        self.xcompCheck(['s(X,Y):-spouse(X,Y).','t(X,Z):-spouse(X,Y),s(Y,Z).'], 't(i,o)', 'susan', {'susan': 1.0}) 
        pass

    def testBack1(self):
        self.xcompCheck(['p(X,Y):-spouse(X,Y),sister(X,Z).'], 'p(i,o)', 'william', {'susan': 3.0})
        pass

    def testBack2(self):
        self.xcompCheck(['p(X,Y):-spouse(X,Y),sister(X,Z1),sister(X,Z2).'],'p(i,o)','william',{'susan': 9.0})
        pass

    def testRec1(self):
#        tensorlog.DEFAULT_MAXDEPTH=4
#        self.inferenceCheck(['p(X,Y):-spouse(X,Y).','p(X,Y):-p(Y,X).'], 'p(i,o)','william',{'susan': 5.0})
#        tensorlog.DEFAULT_MAXDEPTH=10
#        self.inferenceCheck(['p(X,Y):-spouse(X,Y).','p(X,Y):-p(Y,X).'], 'p(i,o)','william',{'susan': 11.0})
        pass

    def testConstOutput(self):
        self.xcompCheck(['sis(X,W):-assign(W,william),child(X,Y).'], 'sis(i,o)', 'sarah', {'william': 1.0})
        self.xcompCheck(['sis(X,W):-assign(W,william),child(X,Y).'], 'sis(i,o)', 'lottie', {'william': 2.0})
        pass

    def testConstChain1(self):
        self.xcompCheck(['p(X,S) :- assign(S,susan),sister(X,Y),child(Y,Z).'],'p(i,o)','william',{'susan': 5.0})
        pass

    def testConstChain2(self):
        # need AssignVectorToVar
#        self.xcompCheck(['p(X,Pos) :- assign(Pos,pos),child(X,Y),young(Y).'],'p(i,o)','sarah',{'pos':1.0})
#        self.xcompCheck(['p(X,Pos) :- assign(Pos,pos),child(X,Y),young(Y).'],'p(i,o)','lottie',{'pos':2.0})
        pass

    def testAltChain(self):
        # raises AttributeError: 'SparseTensorSharedVariable' object has no attribute 'transpose'
#        self.xcompCheck(['p(X,W) :- spouse(X,W),sister(X,Y),child(Y,Z).'],'p(i,o)','william',{'susan': 5.0})
        pass

    def testProppr1(self):
#        w = 7*self.db.onehot('r1')+3*self.db.onehot('r2')        
#        self.propprInferenceCheck(w,['p(X,Y):-sister(X,Y) {r1}.','p(X,Y):-spouse(X,Y) {r2}.'],'p(i,o)',
#                                  'william', {'sarah': 7.0, 'rachel': 7.0, 'lottie': 7.0, 'susan': 3.0})
        pass

    def testProppr2(self):
#        w = 3*self.db.onehot('r2')
#        self.propprInferenceCheck(w,['p(X,Y):-spouse(Y,X) {r2}.'],'p(i,o)',
#                                  'susan', {'william': 3.0})
        pass

    def testReuse1(self):
        self.xcompCheck(['p(X,Y) :- r(X,Z),r(Z,Y).', 'r(X,Y):-spouse(X,Y).'], 'p(i,o)', 'william', 
                        {'william':1.0})
        pass

    def _removeZeros(self, sdict):
        return dict([ (k,v) for (k,v) in sdict.items() if v != 0])
    def xcompCheck(self,ruleStrings,modeString,inputSymbol,expectedResultDict,compare=False):
        self.inferenceCheck(ruleStrings,modeString,inputSymbol,expectedResultDict)
        print 'xcomp inference for mode',modeString,'on input',inputSymbol
        #testtensorlog.softmaxNormalize(expectedResultDict)
        rules = parser.RuleCollection()
        for r in ruleStrings:
            rules.add(parser.Parser.parseRule(r))
        prog = tensorlog.Program(db=self.db,rules=rules)
        mode = declare.ModeDeclaration(modeString)
        tlogFun = prog.compile(mode)
        ytl=None
        if compare: ytl=prog.evalSymbols(mode,[inputSymbol])
        for compilerClass in [theanoxcomp.DenseMatDenseMsgCrossCompiler, theanoxcomp.SparseMatDenseMsgCrossCompiler]:
            xc = compilerClass(prog.db)
            xc.compile(tlogFun)
            #xc.show()
            print '== performing theano eval with',compilerClass,'=='
            ys = xc.evalSymbols([inputSymbol])
            y = ys[0]
            actual = self.db.rowAsSymbolDict(y)
            print 'expected',expectedResultDict
            print 'actual',self._removeZeros(actual)
            if compare: print 'actualTL',self.db.rowAsSymbolDict(ytl)
            self.checkMaxesInDicts(actual, expectedResultDict)
            print '== theano eval checks passed =='
            for x in xc.exprArgs:
                print '== performing theano gradient computation with',compilerClass,'for',x,'=='
                # using sum() to make result a scalar...
                gx = theano.grad(xc.expr.sum(),x)
                print theano.pp(gx)
            print '== theano gradients computed =='

    def checkMaxesInDicts(self,actual,expected):
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

#        print "\n".join(fun.pprint())
#        y1 = prog.evalSymbols(mode,[inputSymbol]) 
#        self.checkDicts(self.db.rowAsSymbolDict(y1), expectedResultDict)
    



if __name__ == "__main__":
    if len(sys.argv)==1:
        unittest.main()
    else:
        foo=TestXCSmallProofs('testIf')
        foo.setUp()
        bar=foo.testIf()
    

