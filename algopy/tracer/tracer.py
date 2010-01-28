import numpy

from algopy.base_type import Algebra

class NotSet:
    def __init__(self, descr=None):
        if descr == None:
            descr = ''
        self.descr = descr
    def __str__(self):
        return 'not set!'
        
def is_set(o):
    return not isinstance(o, NotSet)
        
class CGraph:
    """
    The CGraph (short for Computational Graph) represents a computational
    procedure of elementary functions.
    It is a Directed Acylic Graph (DAG).
    
    The data structure is a list of vertices and each vertex knows its parents.
    
    Example:
    
        The Graph of y = x1(x2+x3) looks like
    
        OP    ID ARGS     VALUE
        -----------------------------------------------------------
        Id     1 [1]         x1            set independent variable
        Id     2 [2]         x2            set independent variable
        Id     3 [3]         x3            set independent variable
        +      4 [2,3]   (v2.x + v3.x)
        *      5 [1,4]   (v1.x * v4.x)
        
        --- independent variables
        [1,2,3]
        
        --- dependent variables
        [5]
        
        
    One can perform to actions with a computational graph:
    
        1)  push forward
        2)  pullback of the differential of the dependent variables
        
    The push forward can propagate any data structure.
    For instance:
        * univariate Taylor polynomials over scalars (e.g. implemented in algopy.utp.utps)
        * univariate Taylor polynomials over matrices (e.g. implemented in algopy.utp.utpm)
        * cross Taylor polynomials over scalars (e.g. implemented in algopy.utp.ctps_c)
        * multivariate Taylor polynomials (not implemented)
        
    Relaxing the definition of the push forward one could also supply:
        * intervals arithmetic
        * slopes
        * etc.
        
        
    The pullback is specifically the pullback of an element of the cotangent space that linearizes
    the computational procedure.
        
    
    """

    def __init__(self):
        self.functionCount = 0
        self.functionList = []
        self.dependentFunctionList = []
        self.independentFunctionList = []
        Function.cgraph = self
        
    def append(self, func):
        self.functionCount += 1
        self.functionList.append(func)
        
    def __str__(self):
        retval = '\n'
        for f in self.functionList:
            arg_IDS = [ af.ID for af in f.args]
            retval += '%s: IDs: %s <- %s\n'%(str(f.func.__name__), str(f.ID), str(arg_IDS))
            retval += 'funcargs:%s\n'%(str(f.funcargs))
            retval += 'x:\n    %s \n'%( str(f.x))
            if is_set(f.xbar):
                retval += 'xbar:\n %s \n'%(str(f.xbar))
        
        retval += '\nIndependent Function List:\n'
        retval += str([f.ID for f in self.independentFunctionList])
        
        retval += '\n\nDependent Function List:\n'
        retval += str([f.ID for f in self.dependentFunctionList])
        retval += '\n'
        return retval
        
    def push_forward(self,x_list):
        """
        Apply a global push forward of the computational procedure defined by
        the computational graph saved in this CGraph instance.
        
        At first, the arguments of the global functions are read into the independent functions.
        Then the computational graph is walked and at each function node
        """
        # populate independent arguments with new values
        for nf,f in enumerate(self.independentFunctionList):
            f.args[0].x = x_list[nf]

        # traverse the computational tree
        for f in self.functionList:
            f.__class__.push_forward(f.func, f.args, Fout = f, funcargs = f.funcargs)


    def pullback(self, xbar_list):
        """
        Apply the pullback of the cotangent element, 
        
        e.g. for::
        
            y = y(x)
        
        compute::
        
            ybar dy(x) = xbar dx
            
        """
        
        if len(self.dependentFunctionList) == 0:
            raise Exception('You forgot to specify which variables are dependent!\n e.g. with cg.dependentFunctionList = [F1,F2]')

        # initial all xbar to zero
        for f in self.functionList:
            f.xbar_from_x()

        for nf,f in enumerate(self.dependentFunctionList):
            f.xbar[...] = xbar_list[nf]
            
        # print self
        for f in self.functionList[::-1]:
            # print 'pullback of f=',f.func.__name__
            f.__class__.pullback(f)
            # print self

        

class Function(Algebra):
    
    xbar = NotSet()
    
    def __init__(self, x = None):
        """
        Creates a new function node that is a variable.
        """
        
        if type(x) != type(None):
            # create a Function node with value x referring to itself, i.e.
            # returning x when called
            cls = self.__class__
            cls.create(x, (self,), cls.Id, self)    
    
    cgraph = None
    @classmethod
    def get_ID(cls):
        """
        return function ID
        
        Rationale:
            When code tracing is active, each Function is added to a Cgraph instance
            and it is given a unique ID.
        
        """
        if cls.cgraph != None:
            return cls.cgraph.functionCount
        else:
            return None
    
    @classmethod
    def create(cls, x, fargs, func, f = None, funcargs = ()):
        """
        Creates a new function node.
        
        INPUTS:
            x           anything                            current value
            args        tuple of Function objects           arguments of the new Function node
            func        callable                            the function that can evaluate func(x)
            
        OPTIONAL:
            f           Function instance
            funcargs    tuple                               additional arguments to the function func
        
        """
        if f == None:
            f = Function()
        f.x = x
        f.args = fargs
        f.func = func
        f.ID = cls.get_ID()
        f.funcargs = funcargs
        cls.cgraph.append(f)
        return f
    
    @classmethod
    def Id(cls, x):
        """
        The identity function:  x = Id(x)
        
        """
        return x


    def __repr__(self):
        return str(self)

    def __str__(self):
        return '%s'%str(self.x)

    def __getitem__(self, sl):
        return Function.push_forward(self.x.__class__.__getitem__,(self,), funcargs = (sl,))
        # if isinstance(self.x,tuple):
        #     tmp = self.x.__getitem__(sl)
        # else:
        #     if type(sl) == int or sl == Ellipsis:
        #         sl = (sl,)
                
        #     tmp = self.x.__getitem__((slice(None),slice(None)) + tuple(sl))
        # return self.__class__(tmp)

        
    @classmethod
    def push_forward(cls, func, Fargs, Fout = None, funcargs = ()):
        """
        Computes the push forward of func
        
        INPUTS:
            func            callable            func(Fargs[0].x,...,Fargs[-1].x)
            Fargs           tuple               tuple of Function nodes
        """
        if numpy.ndim(Fargs) > 0:
            args = tuple([ fa.x for fa in Fargs] + list(funcargs))
            out  = func(*args)
        else:
            arg = Fargs.x
            out  = func(arg)
        
        if Fout == None:
            retval = cls.create(out, Fargs, func, funcargs = funcargs)
            return retval
        
        else:
            Fout.x = out
            return Fout
            
            
    @classmethod
    def pullback(cls, F):
        """
        compute the pullback of the Function F
        
        e.g. if y = f(x)
        compute xbar as::
        
            ybar dy = ybar df(x) = ybar df/dx dx = xbar dx
            
        More specifically:
        
        (y1,y2) = f(x1,x2, funcargs = v)
        
        where v is a constant argument.
        
        Examples:

            1) (Q,R) = qr(A)
            2) Q = getitem(qr(A),0)
        
        This function assumes that for each function f there is a corresponding function::
        
            pb_f(y1bar,y2bar,x1,x2,y1,y2,out=(x1bar, x2bar), funcargs = v)
            
        The Function F contains information about its arguments, F.y and F.ybar.
        Thus, pullback(F) computes F.args[i].xbar
        """
        
        func_name = F.func.__name__
        
        if isinstance(F.x,tuple):
            # case if the function F has several outputs, e.g. (y1,y2) = F(x)
            args_list    = [Fa.x for Fa in F.args]
            argsbar_list = [Fa.xbar for Fa in F.args]            
            
            args = list(F.xbar) + args_list + list(F.x)
            args = tuple(args)
            
            kwargs = {'out': tuple(argsbar_list)}
            
            if len(F.funcargs):
                kwargs['funcargs'] = F.funcargs
                
            # print 'func_name=',func_name
            # print 'args=',args
            # print 'kwargs=',kwargs                
            # get the pullback function
            f = eval('__import__("algopy.utp.utpm.utpm").utp.utpm.utpm.'+F.x[0].__class__.__name__+'.pb_'+func_name)            

        else:
            # case if the function F has output, e.g. y1 = F(x)
            args_list    = [Fa.x for Fa in F.args]
            argsbar_list = [Fa.xbar for Fa in F.args]
            
            args = [F.xbar] + args_list + [F.x]
            args = tuple(args)
            kwargs = {'out': tuple(argsbar_list)}
            
            if len(F.funcargs):
                # add additional funcargs if they are set
                kwargs['funcargs'] = F.funcargs
                
            # get the pullback function
            f = eval('__import__("algopy.utp.utpm.utpm").utp.utpm.utpm.'+F.x.__class__.__name__+'.pb_'+func_name)

        
        # call the pullbck function
        f(*args, **kwargs )
        
        return F
        
        
    @classmethod
    def totype(cls, x):
        """
        tries to convert x to an object of the class
        """
            
        if isinstance(x, cls):
            return x
        
        else:
            return cls(x)
            
    def xbar_from_x(self):
        if numpy.isscalar(self.x):
            self.xbar = 0.
            
        elif isinstance(self.x, tuple):
            self.xbar = tuple( [xi.zeros_like() for xi in self.x])
        else:
            self.xbar = self.x.zeros_like()
    
    
    def __add__(self,rhs):
        return Function.push_forward(self.x.__class__.__add__,(self,rhs))

    def __sub__(self,rhs):
        return Function.push_forward(self.x.__class__.__sub__,(self,rhs))

    def __mul__(self,rhs):
        return Function.push_forward(self.x.__class__.__mul__,(self,rhs))

    def __div__(self,rhs):
        return Function.push_forward(self.x.__class__.__div__,(self,rhs))
        
    def __radd__(self,lhs):
        return self + lhs

    def __rsub__(self,lhs):
        return -self + lhs

    def __rmul__(self,lhs):
        return self * lhs

    def __rdiv__(self, lhs):
        lhs = lhs.__class__.totype(lhs)
        return lhs/self
        
    def dot(self,rhs):
        return Function.push_forward(self.x.__class__.dot, (self,rhs))
        
    def inv(self):
         return Function.push_forward(self.x.__class__.inv, (self,))
         
    def qr(self):
         return Function.push_forward(self.x.__class__.qr, (self,))

    def eigh(self):
         return Function.push_forward(self.x.__class__.eigh, (self,))

    def solve(self,rhs):
        return Function.push_forward(self.x.__class__.solve, (self,rhs))
        
    def transpose(self):
        return Function.push_forward(self.x.__class__.transpose, (self,))
        
    T = property(transpose)
    
    def get_shape(self):
        return self.x.shape
    shape = property(get_shape)
 