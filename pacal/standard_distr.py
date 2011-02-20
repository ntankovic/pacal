"""Standard distributions."""

from numpy import Inf
from numpy import isscalar, zeros_like, asfarray, zeros
from numpy import pi, sqrt, exp, log, log1p, cos, floor
from numpy.random import normal, uniform, chisquare, exponential, gamma, beta, pareto, laplace, standard_t, weibull
from numpy.random import f as f_rand


import params
from utils import lgamma
from distr import Distr
from segments import PiecewiseDistribution, Segment
from segments import ConstSegment, PInfSegment, MInfSegment, SegmentWithPole, DiracSegment
from compiler.ast import Raise


class FunDistr(Distr):
    """General distribution defined as function with
    singularities at given breakPoints."""
    def __init__(self, fun, breakPoints = None, **kvargs):
        super(FunDistr, self).__init__()
        self.fun = fun
        self.breakPoints = breakPoints
        self.kvargs = kvargs
    def pdf(self, x):
        return self.fun(x)
    def getName(self):
        return "USER_FUN({0},{1})".format(self.breakPoints[0], self.breakPoints[-1])
    def init_piecewise_pdf(self):
        self.piecewise_pdf = PiecewiseDistribution(fun = self.fun, breakPoints = self.breakPoints, **self.kvargs)
    def rand_raw(self, n = 1):
        return self.rand_invcdf(n)
    
class PDistr(Distr):
    """General distribution defined as piecewise function."""
    def __init__(self, segs = None, **kvargs):
        super(PDistr, self).__init__()
        self.segs = segs
        
    def init_piecewise_pdf(self):
        if isinstance(self.segs, PiecewiseDistribution):
            self.piecewise_pdf = self.segs
        else:
            self.piecewise_pdf = PiecewiseDistribution();
            for seg in self.segs:
                self.piecewise_pdf.addSegment(seg)
    def getName(self):
        return "USER_PDISTR({0})".format(self.get_piecewise_pdf())
    def rand_raw(self, n = 1):
        return self.rand_invcdf(n)

class MixDistr(Distr):
    """Mixture of distributions"""
    def __init__(self, probs, distrs):
        """Keyword arguments:
        probs -- list of pi's
        distrs -- list of distributions        
        """
        super(MixDistr, self).__init__()
        assert len(probs) == len(distrs)
        self.nmix = len(probs)
        self.probs = probs
        self.distrs = distrs
    def init_piecewise_pdf(self):   
        mixdistr = ConstDistr(1, self.probs[0]) * self.distrs[0]
        for i in range(1,len(self.probs)):
            mixi = ConstDistr(1,self.probs[i]) * self.distrs[i]
            mixdistr.piecewise_pdf =  mixdistr.get_piecewise_pdf() + mixi.get_piecewise_pdf()  
        self.piecewise_pdf = mixdistr.piecewise_pdf        
    def getName(self):
        return "MIX()".format()
    
    #def pdf(self, x):
    #    return self.fun(x)
    #def init_piecewise_pdf(self):
    #    self.piecewise_pdf = PiecewiseDistribution(fun = self.fun, breakPoints = self.breakPoints)

class NormalDistr(Distr):
    def __init__(self, mu=0.0, sigma=1.0):
        super(NormalDistr, self).__init__()
        self.mu = mu
        self.sigma = sigma
        self.one_over_twosigma2 = 0.5 / (sigma * sigma)
        self.nrm = 1.0 / (self.sigma * sqrt(2*pi))
    def init_piecewise_pdf(self):
        # put breaks at inflection points
        b1 = self.mu - self.sigma
        b2 = self.mu + self.sigma
        self.piecewise_pdf = PiecewiseDistribution([])
        self.piecewise_pdf.addSegment(MInfSegment(b1, self.pdf))
        self.piecewise_pdf.addSegment(Segment(b1, b2, self.pdf))
        self.piecewise_pdf.addSegment(PInfSegment(b2, self.pdf))
    def pdf(self, x):
        q = (x-self.mu)**2 * self.one_over_twosigma2
        f = self.nrm * exp(-q)
        return f
    def rand_raw(self, n = None):  # None means return scalar
        return normal(self.mu, self.sigma, n)
    def __str__(self):
        return "Normal({0},{1})#{2}".format(self.mu, self.sigma, id(self))
    def getName(self):
        return "N({0},{1})".format(self.mu, self.sigma)
    
class UniformDistr(Distr):
    def __init__(self, a = 0.0, b = 1.0):
        super(UniformDistr, self).__init__()
        self.a = a
        self.b = b
        self.p = 1.0 / float(b-a)
    def init_piecewise_pdf(self):
        self.piecewise_pdf = PiecewiseDistribution([])
        self.piecewise_pdf.addSegment(ConstSegment(self.a, self.b, self.p))
    def rand_raw(self, n = None):
        return uniform(self.a, self.b, n)
    def __str__(self):
        return "Uniform({0},{1})#{2}".format(self.a, self.b, id(self))
    def getName(self):
        return "U({0},{1})".format(self.a, self.b)

class CauchyDistr(Distr):
    def __init__(self, gamma = 1.0, center = 0.0):
        super(CauchyDistr, self).__init__()
        self.gamma = gamma
        self.center = center
    def pdf(self, x):
        return self.gamma / (pi * (self.gamma*self.gamma + (x - self.center)*(x - self.center)))
    def init_piecewise_pdf(self):
        b1 = self.center - self.gamma
        b2 = self.center + self.gamma
        self.piecewise_pdf = PiecewiseDistribution([])
        self.piecewise_pdf.addSegment(MInfSegment(b1, self.pdf))
        self.piecewise_pdf.addSegment(Segment(b1, b2, self.pdf))
        self.piecewise_pdf.addSegment(PInfSegment(b2, self.pdf))
        #self.piecewise_pdf = self.piecewise_pdf.toInterpolated()
    def rand_raw(self, n = None):
        return self.center + normal(0, 1, n) / normal(0, 1, n) * self.gamma
    def __str__(self):
        if self.gamma == 1 and self.center == 0:
            return "Cauchy#{0}".format(id(self))
        else:
            return "Cauchy(gamma={0}, center={1})#{2}".format(self.gamma, self.center, id(self))
    def getName(self):
        return "Cauchy({0},{1})".format(self.center, self.gamma)    

class ChiSquareDistr(Distr):
    def __init__(self, df = 1):
        super(ChiSquareDistr, self).__init__()
        self.df = df
        self.df2 = df / 2.0
        self.lg_norm = lgamma(self.df2) + self.df2 * log(2)
        if self.df == 1:
            self.pdf_at_0 = Inf
            self.lpdf_at_0 = Inf
        elif self.df == 2:
            self.pdf_at_0 = 0.5
            self.lpdf_at_0 = log(0.5)
        else:
            self.pdf_at_0 = 0
            self.lpdf_at_0 = -Inf
    def log_pdf(self, x):
        lpdf = (self.df2 - 1) * log(x) - x/2.0 - self.lg_norm
        return lpdf
    def pdf(self, x):
        if isscalar(x):
            if x < 0:
                y = 0
            elif x == 0:
                y = self.pdf_at_0
            else:
                y = exp(self.log_pdf(x))
        else:
            y = zeros_like(asfarray(x))
            mask = (x > 0)
            y[mask] = exp(self.log_pdf(x[mask]))
            mask_zero = (x == 0)
            y[mask_zero] = self.pdf_at_0
        return y
    def init_piecewise_pdf(self):
        if 1 <= self.df <= 20:
            self.piecewise_pdf = PiecewiseDistribution(fun = self.pdf,  
                                                   breakPoints = [0.0, self.df/2.0, self.df*2.0, Inf],
                                                   lpoles=[True, False, False, False])
        elif 20 < self.df:            
            mean = self.df
            std = sqrt(2 * self.df)
            self.piecewise_pdf = PiecewiseDistribution(fun = self.pdf,
                                                        breakPoints =[0.0, self.df*0.75, self.df*4.0/3.0,  Inf],
                                                        lpoles=[True, False, False, False])
            
        else:
            print "unexeepted df=", self.df            
        #if self.df == 1 or self.df == 3:
        #    self.piecewise_pdf.addSegment(SegmentWithPole(0, 1, self.pdf, left_pole = True))
        #else:
        #    self.piecewise_pdf.addSegment(Segment(0, 1, self.pdf))
        #if self.df <= 3:
        #    self.piecewise_pdf.addSegment(PInfSegment(1, self.pdf))
        #elif self.df <= 6:
        #    mode = self.df - 2
        #    self.piecewise_pdf.addSegment(Segment(1, mode, self.pdf))
        #    self.piecewise_pdf.addSegment(Segment(mode, 2*mode, self.pdf))
        #    self.piecewise_pdf.addSegment(PInfSegment(2*mode, self.pdf))
        #else:
        #    mean = self.df
        #    std = sqrt(2 * self.df)
        #    self.piecewise_pdf.addSegment(Segment(1, mean - std, self.pdf))
        #    self.piecewise_pdf.addSegment(Segment(mean - std, mean + std, self.pdf))
        #    self.piecewise_pdf.addSegment(PInfSegment(mean + std, self.pdf))
    def rand_raw(self, n = None):
        return chisquare(self.df, n)
    def __str__(self):
        return "ChiSquare(df={0})#{1}".format(self.df, id(self))
    def getName(self):
        return "Chi2({0})".format(self.df)

class ExponentialDistr(Distr):
    def __init__(self, lmbda = 1):
        super(ExponentialDistr, self).__init__()
        self.lmbda = lmbda
    def pdf(self, x):
        if isscalar(x):
            if x < 0:
                y = 0
            else:
                y = self.lmbda * exp(-self.lmbda * x)
        else:
            y = zeros_like(asfarray(x))
            mask = (x >= 0)
            y[mask] = self.lmbda * exp(-self.lmbda * x)
        return y
    def init_piecewise_pdf(self):
        self.piecewise_pdf = PiecewiseDistribution([])
        self.piecewise_pdf.addSegment(Segment(0, 1, self.pdf))
        self.piecewise_pdf.addSegment(PInfSegment(1, self.pdf))
    def rand_raw(self, n = None):
        return exponential(1.0/self.lmbda, n)
    def __str__(self):
        return "Exponential(lambda={0})#{1}".format(self.lmbda, id(self))
    def getName(self):
        return "Ex({0})".format(self.lmbda)

class GammaDistr(Distr):
    def __init__(self, k = 2, theta = 2):
        super(GammaDistr, self).__init__()
        assert k > 0
        assert theta > 0
        self.k = k
        self.theta = theta
        self.lg_norm = lgamma(self.k) + self.k * log(self.theta)
        if self.k < 1:
            self.pdf_at_0 = Inf
            self.lpdf_at_0 = Inf
        elif self.k == 1:
            self.pdf_at_0 = 1.0 / self.theta
            self.lpdf_at_0 = -log(self.theta)
        else:
            self.pdf_at_0 = 0
            self.lpdf_at_0 = -Inf
    def log_pdf(self, x):
        lpdf = (self.k - 1) * log(x) - x / self.theta - self.lg_norm
        return lpdf
    def pdf(self, x):
        if isscalar(x):
            if x < 0:
                y = 0
            elif x == 0:
                y = self.pdf_at_0
            else:
                y = exp(self.log_pdf(x))
        else:
            y = zeros_like(asfarray(x))
            mask = (x > 0)
            y[mask] = exp(self.log_pdf(x[mask]))
            mask_zero = (x == 0)
            y[mask_zero] = self.pdf_at_0
        return y
    def init_piecewise_pdf(self):
        self.piecewise_pdf = PiecewiseDistribution([])
        if self.k < 1:
            self.piecewise_pdf.addSegment(SegmentWithPole(0, 1, self.pdf, left_pole = True))
            self.piecewise_pdf.addSegment(PInfSegment(1, self.pdf))
        elif self.k == 1:
            self.piecewise_pdf.addSegment(Segment(0, 1, self.pdf))
            self.piecewise_pdf.addSegment(PInfSegment(1, self.pdf))
        else:
            mode = (self.k - 1) * self.theta
            self.piecewise_pdf.addSegment(Segment(0, mode / 2, self.pdf))
            self.piecewise_pdf.addSegment(Segment(mode / 2, mode, self.pdf))
            self.piecewise_pdf.addSegment(Segment(mode, 2 * mode, self.pdf))
            self.piecewise_pdf.addSegment(PInfSegment(2*mode, self.pdf))
    def rand_raw(self, n = None):
        return gamma(self.k, self.theta, n)
    def __str__(self):
        return "Gamma(k={0},theta={1})#{2}".format(self.k, self.theta, id(self))
    def getName(self):
        return "Gamma({0},{1})".format(self.k, self.theta)

class BetaDistr(Distr):
    def __init__(self, alpha = 1, beta = 1):
        super(BetaDistr, self).__init__()
        self.alpha = alpha
        self.beta = beta
        self.norm = exp(lgamma(self.alpha + self.beta) - lgamma(self.alpha) - lgamma(self.beta))
    def pdf(self, x):
        if isscalar(x):
            if x < 0 or x > 1:
                y = 0
            else:
                y = self.norm * x**(self.alpha - 1) * (1-x)**(self.beta - 1)
        else:
            y = zeros_like(asfarray(x))
            mask = (x >= 0) & (x <= 1)
            y[mask] = self.norm * x[mask]**(self.alpha - 1) * (1-x[mask])**(self.beta - 1)
        return y
    def init_piecewise_pdf(self):
        if self.alpha > 1 and self.beta > 1:
            m = float(self.alpha - 1) / (self.alpha + self.beta - 2) # mode
        else:
            m = 0.5
        m = 0.5 # TODO check this, but it seems better
        self.piecewise_pdf = PiecewiseDistribution([])
        poleL = self.alpha < 2 and abs(self.alpha - 1) > params.pole_detection.max_pole_exponent
        poleR = self.beta < 2  and abs(self.beta - 1) > params.pole_detection.max_pole_exponent
        if poleL and poleR:
            self.piecewise_pdf.addSegment(SegmentWithPole(0, m, self.pdf, left_pole = True))
            self.piecewise_pdf.addSegment(SegmentWithPole(m, 1, self.pdf, left_pole = False))
        elif poleL:
            self.piecewise_pdf.addSegment(SegmentWithPole(0, m, self.pdf, left_pole = True))
            self.piecewise_pdf.addSegment(Segment(m, 1, self.pdf))
        elif poleR:
            self.piecewise_pdf.addSegment(Segment(0, m, self.pdf))
            self.piecewise_pdf.addSegment(SegmentWithPole(m, 1, self.pdf, left_pole = False))
        else:
            self.piecewise_pdf.addSegment(Segment(0, m, self.pdf))
            self.piecewise_pdf.addSegment(Segment(m, 1, self.pdf))
    def rand_raw(self, n = None):
        return beta(self.alpha, self.beta, n)
    def __str__(self):
        return "Beta(alpha={0},beta={1})#{2}".format(self.alpha, self.beta, id(self))
    def getName(self):
        return "Beta({0},{1})".format(self.alpha, self.beta)

class ParetoDistr(Distr):
    def __init__(self, alpha = 1, xmin = 1):
        assert alpha > 0
        assert xmin > 0
        super(ParetoDistr, self).__init__()
        self.alpha = alpha
        self.xmin = xmin
        self.nrm = float(alpha * xmin ** alpha)
    def pdf(self, x):
        if isscalar(x):
            if x < self.xmin:
                y = 0
            else:
                y = self.nrm / x ** (self.alpha + 1)
        else:
            y = zeros_like(asfarray(x))
            mask = (x >= self.xmin)
            y[mask] = self.nrm / x[mask] ** (self.alpha + 1)
        return y
    def init_piecewise_pdf(self):
        self.piecewise_pdf = PiecewiseDistribution([])
        self.piecewise_pdf.addSegment(Segment(self.xmin, self.xmin + 1, self.pdf))
        self.piecewise_pdf.addSegment(PInfSegment(self.xmin + 1, self.pdf))
    def rand_raw(self, n = None):
        return self.xmin + pareto(self.alpha, n) * self.xmin
    def __str__(self):
        return "ParetoDistr(alpha={0},xmin={1})#{2}".format(self.alpha, self.xmin, id(self))
    def getName(self):
        return "Pareto({0},{1})".format(self.alpha, self.xmin)

class LevyDistr(Distr):
    def __init__(self, c = 1.0, xmin = 0.0):
        assert c > 0
        super(LevyDistr, self).__init__()
        self.c = c
        self.xmin = xmin
        self.nrm = sqrt(c/(2*pi))
    def pdf(self, x):
        if isscalar(x):
            if x <= self.xmin:
                y = 0
            else:
                y = self.nrm / (x - self.xmin)**1.5 * exp(-0.5 * self.c / (x - self.xmin))
        else:
            y = zeros_like(asfarray(x))
            mask = (x > self.xmin)
            y[mask] = self.nrm / (x[mask] - self.xmin)**1.5 * exp(-0.5 * self.c / (x[mask] - self.xmin))
        return y
    def init_piecewise_pdf(self):
        self.piecewise_pdf = PiecewiseDistribution([])
        self.piecewise_pdf.addSegment(Segment(self.xmin, self.xmin + self.c, self.pdf))
        self.piecewise_pdf.addSegment(PInfSegment(self.xmin + self.c, self.pdf))
    def rand_raw(self, n = None):
        sigma = 1.0 / sqrt(self.c)
        return self.xmin + 1.0 / normal(0, sigma, n) ** 2
    def __str__(self):
        return "LevyDistr(c={0},xmin={1})#{2}".format(self.c, self.xmin, id(self))
    def getName(self):
        return "Levy({0},{1})".format(self.c, self.xmin)

class LaplaceDistr(Distr):
    def __init__(self, lmbda = 1.0, mu = 0.0):
        assert lmbda > 0
        super(LaplaceDistr, self).__init__()
        self.lmbda = lmbda
        self.mu = mu
        self.nrm = 0.5 / self.lmbda
    def pdf(self, x):
        y = self.nrm * exp(-abs(x - self.mu))
        return y
    def init_piecewise_pdf(self):
        self.piecewise_pdf = PiecewiseDistribution([])
        self.piecewise_pdf.addSegment(MInfSegment(self.mu - 2 * self.lmbda, self.pdf))
        self.piecewise_pdf.addSegment(Segment(self.mu - 2 * self.lmbda, 0, self.pdf))
        self.piecewise_pdf.addSegment(Segment(0, self.mu + 2 * self.lmbda, self.pdf))
        self.piecewise_pdf.addSegment(PInfSegment(self.mu + 2 * self.lmbda, self.pdf))
    def rand_raw(self, n = None):
        return laplace(self.mu, self.lmbda, n)
    def __str__(self):
        return "LaplaceDistr(lambda={0},mu={1})#{2}".format(self.lmbda, self.mu, id(self))
    def getName(self):
        return "Laplace({0},{1})".format(self.lmbda, self.mu)

class StudentTDistr(Distr):
    def __init__(self, df = 2):
        assert df > 0
        super(StudentTDistr, self).__init__()
        self.df = df
        self.lg_norm = lgamma(float(self.df + 1) / 2) - lgamma(float(self.df) / 2) - 0.5 * (log(self.df) + log(pi))
    def pdf(self, x):
        lgy = self.lg_norm - (float(self.df + 1) / 2) * log1p(x**2 / self.df)
        return exp(lgy)
    def init_piecewise_pdf(self):
        # split at inflection points
        infl = sqrt(float(self.df) / (self.df + 2))
        self.piecewise_pdf = PiecewiseDistribution([])
        self.piecewise_pdf.addSegment(MInfSegment(-infl, self.pdf))
        self.piecewise_pdf.addSegment(Segment(-infl, infl, self.pdf))
        self.piecewise_pdf.addSegment(PInfSegment(infl, self.pdf))
    def rand_raw(self, n = None):
        return standard_t(self.df, n)
    def __str__(self):
        return "StudentTDistr(df={0})#{1}".format(self.df, id(self))
    def getName(self):
        return "StudentT({0})".format(self.df)

class SemicircleDistr(Distr):
    def __init__(self, R = 1.0):
        assert R > 0
        super(SemicircleDistr, self).__init__()
        self.R = R
        self.norm = 2.0 / (pi * R * R)
    def pdf(self, x):
        if isscalar(x):
            if -self.R <= x <= self.R:
                y = self.norm * sqrt(self.R*self.R - x*x)
        else:
            mask = (-self.R <= x) & (x <= self.R)
            y = zeros_like(asfarray(x))
            y[mask] = self.norm * sqrt(self.R*self.R - x*x)
        return y
    def init_piecewise_pdf(self):
        # split at inflection points
        self.piecewise_pdf = PiecewiseDistribution([])
        self.piecewise_pdf.addSegment(SegmentWithPole(-self.R, -float(self.R) / 2, self.pdf, left_pole = True))
        self.piecewise_pdf.addSegment(Segment(-float(self.R) / 2, float(self.R) / 2, self.pdf))
        self.piecewise_pdf.addSegment(SegmentWithPole(float(self.R) / 2, self.R, self.pdf, left_pole = False))
    def rand_raw(self, n = None):
        return self.R * sqrt(uniform(0, 1, n)) * cos(uniform(0, 1, n) * pi)
    def __str__(self):
        return "Semicircle(R={0})#{1}".format(self.R, id(self))
    def getName(self):
        return "Semicircle({0})".format(self.R)

class FDistr(Distr):
    def __init__(self, df1 = 1, df2 = 1):
        super(FDistr, self).__init__()
        self.df1 = float(df1)
        self.df2 = float(df2)
        self.lg_norm = self.df2 / 2 * log(self.df2) + lgamma((self.df1 + self.df2) / 2) - lgamma(self.df1 / 2) - lgamma(self.df2 / 2)
        if self.df1 < 2:
            self.pdf_at_0 = Inf
        elif self.df1 == 2:
            self.pdf_at_0 = 1
        else:
            self.pdf_at_0 = 0
    def pdf(self, x):
        if isscalar(x):
            if x < 0:
                y = 0
            elif x == 0:
                y = self.pdf_at_0
            else:
                lgy = self.lg_norm + 0.5 * (self.df1 * log(self.df1*x) - (self.df1 + self.df2) * log(self.df1 * x + self.df2)) - log(x)
                y = exp(lgy)
        else:
            y = zeros_like(asfarray(x))
            y[x==0] = self.pdf_at_0
            mask = (x > 0)
            lgy = self.lg_norm + 0.5 * (self.df1 * log(self.df1*x[mask]) - (self.df1 + self.df2) * log(self.df1 * x[mask] + self.df2)) - log(x[mask])
            y[mask] = exp(lgy)
        return y
    def init_piecewise_pdf(self):
        self.piecewise_pdf = PiecewiseDistribution([])
        if self.df1 < 2:
            self.piecewise_pdf.addSegment(SegmentWithPole(0, 1, self.pdf, left_pole = True))
            self.piecewise_pdf.addSegment(PInfSegment(1, self.pdf))
        elif self.df1 == 2:
            self.piecewise_pdf.addSegment(Segment(0, 1, self.pdf))
            self.piecewise_pdf.addSegment(PInfSegment(1, self.pdf))
        else:
            mode = float(self.df1 - 2) / self.df1 * float(self.df2) / (self.df2 + 2)
            self.piecewise_pdf.addSegment(SegmentWithPole(0, mode, self.pdf, left_pole = True))
            self.piecewise_pdf.addSegment(Segment(mode, mode + 1, self.pdf))
            self.piecewise_pdf.addSegment(PInfSegment(mode + 1, self.pdf))
    def rand_raw(self, n = None):
        return f_rand(self.df1, self.df2, n)
    def __str__(self):
        return "F(df1={0},df2={1})#{2}".format(self.df1, self.df2, id(self))
    def getName(self):
        return "F({0},{1})".format(self.df1, self.df2)

class WeibullDistr(Distr):
    def __init__(self, k = 3, lmbda = 1):
        super(WeibullDistr, self).__init__()
        assert k > 0
        assert lmbda > 0
        self.k = k
        self.lmbda = lmbda
        self.nrm = float(self.k) / self.lmbda
        if self.k < 1:
            self.pdf_at_0 = Inf
        elif self.k == 1:
            self.pdf_at_0 = 1
        else:
            self.pdf_at_0 = 0
    def pdf(self, x):
        if isscalar(x):
            if x < 0:
                y = 0
            elif x == 0:
                y = self.pdf_at_0
            else:
                y = self.nrm * (x / self.lmbda)**(self.k-1) * exp(-(x / self.lmbda)**self.k)
        else:
            y = zeros_like(asfarray(x))
            mask = (x > 0)
            y[mask] = self.nrm * (x[mask] / self.lmbda)**(self.k-1) * exp(-(x[mask] / self.lmbda)**self.k)
            mask_zero = (x == 0)
            y[mask_zero] = self.pdf_at_0
        return y
    def init_piecewise_pdf(self):
        if self.k <= 1:
            self.piecewise_pdf = PiecewiseDistribution(fun = self.pdf,  
                                                       breakPoints = [0.0, self.k, Inf],
                                                       lpoles=[True, False, False])
        else:
            mode = self.lmbda * (float(self.k - 1) / self.k)**(1.0/self.k)
            if self.k == floor(self.k):
                self.piecewise_pdf = PiecewiseDistribution(fun = self.pdf,  
                                                           breakPoints = [0.0, mode, Inf],
                                                           lpoles=[False, False, False])
            else:
                self.piecewise_pdf = PiecewiseDistribution(fun = self.pdf,  
                                                           breakPoints = [0.0, mode, Inf],
                                                           lpoles=[True, False, False])
    def rand_raw(self, n = None):
        return self.lmbda * weibull(self.k, n)
    def __str__(self):
        return "Weibull(k={0},lambda={1})#{2}".format(self.k, self.lmbda, id(self))
    def getName(self):
        return "Weibull({0},{1})".format(self.k, self.lmbda)


### Discrete distributions

class DiscreteDistr(Distr):
    """Discrete distribution"""
    def __init__(self, xi=[0.0, 1.0], pi=[0.5, 0.5]):
        super(DiscreteDistr, self).__init__([])
        assert(len(xi) == len(pi))
        self.xi = xi
        self.pi = pi
        self.px = {}
        for i in range(len(xi)):
            self.px[xi[i]]=pi[i]
    def init_piecewise_pdf(self):
        self.piecewise_pdf = PiecewiseDistribution([])        
        for i in range(len(self.xi)):
            self.piecewise_pdf.addSegment(DiracSegment(self.xi[i], self.pi[i]))
        for i in range(len(self.xi)-1):
            self.piecewise_pdf.addSegment(ConstSegment(self.xi[i], self.xi[i+1], 0))
    def rand_raw(self, n):
        return self.rand_invcdf(n)
    def __str__(self):
        return "Discrete({0})#{1}".format(self.px, id(self))
    def getName(self):
        return "Di({0})".format(len(self.xi))
    
class ConstDistr(DiscreteDistr):
    def __init__(self, c = 0.0, p = 1.0):
        super(ConstDistr, self).__init__([c], [p])
        self.c = c
    def rand_raw(self, n = None):
        r = zeros(n)
        r.fill(self.c)
        return r
    def __str__(self):
        return str(self.c)
    def getName(self):
        return str(self.c)

class OneDistr(ConstDistr):
    """One point distribution at point one"""
    def __init__(self):
        super(OneDistr, self).__init__(c = 1.0)
class ZeroDistr(ConstDistr):
    """One point distribution at point zero"""
    def __init__(self):
        super(ZeroDistr, self).__init__(c = 0.0)




if __name__ == "__main__":
    from pylab import figure, show
    from distr import demo_distr, log, exp, max, min, sqrt
    from plotfun import plotdistr, histdistr

    import numpy
    from numpy import ceil, log1p


    M = MixDistr([0.5, 0.25, 0.125, 0.0625, 0.03125], 
                 [UniformDistr(-0.5,0.5)+4**0,
                  UniformDistr(-0.5,0.5)+4**1,
                  UniformDistr(-0.5,0.5)+4**2,
                  UniformDistr(-0.5,0.5)+4**3,
                  UniformDistr(-0.5,0.5)+4**4,
                  ])
    #M.plot()
    (M/M).plot()
    show()
    0/0
    
    mix = MixDistr([0.25, 0.75], [NormalDistr(-1,0.5), NormalDistr(1,2)])
    print "======", mix.get_piecewise_pdf()
    mix.summary()
    mix.plot()
    d = mix/mix
    d.plot()
    figure()
    M = MixDistr([0.5, 0.25, 0.125, 0.0625, 0.03125], 
                 [UniformDistr(-1,1)/4+1, 
                 UniformDistr(-1,1)/8+2,
                 UniformDistr(-1,1)/16+4,
                 UniformDistr(-1,1)/32+8, 
                 UniformDistr(-1,1)/64+16])
    M.summary()
    M.plot()
    M.get_piecewise_cdf().plot()
    d= M/M
    d.summary()
    d.plot()
    


    #Ua = UniformDistr(1,2); #plotdistr(Ua)
    #Ub = UniformDistr(0.25,2);
    #Uc = UniformDistr(0.25,2);
    #A = Ua + Ub
    #B = Ua - Ub
    #C = Ua * Ub
    #D = Ua / Ub
    #E = min(Ub, Uc)
    #print min(1,2)
    #F = max(Ub, Uc)
    #G = max(UniformDistr(0,3), UniformDistr(1,2))
    #H = min(UniformDistr(0,3), UniformDistr(1,2))
    #I = max(UniformDistr(0,0.1), UniformDistr(1,2))
    #J = min(UniformDistr(0,0.1), UniformDistr(1,2))
    #K = min(UniformDistr(0,1), NormalDistr(1,2))
    #A.plot()
    #B.plot()
    #C.plot()
    #D.plot()
    #E.plot()
    #F.plot()
    #G.plot()
    #H.plot()
    #I.plot()
    #J.plot()
    #K.plot()
    #histdistr(A)
    #histdistr(B)
    #histdistr(C)
    #histdistr(D)
    #histdistr(E)
    #histdistr(F)
    #histdistr(G)
    #histdistr(H)
    #histdistr(I)
    #histdistr(J)
    #histdistr(K)
    #A.summary()
    #B.summary()
    #C.summary()
    #D.summary()
    #E.summary()
    #F.summary()

    # n = 4
    # T10 = (NormalDistr() / ChiSquareDistr(n)**0.5 ) * sqrt(n)
    # figure()
    # demo_distr(T10, theoretical = StudentTDistr(n), xmin = -1e10, xmax=1e10)
    # 
    # N1 = NormalDistr()
    # num  = (N1 + N1 + N1 + N1+ N1) #/ 5**0.5
    # C1 = ChiSquareDistr(1)
    # #C1 = N1**2
    
    # den = (C1 + C1 + C1 + C1 + C1) 
    # T5 = num / den**0.5 #* 5 ** 0.5
    # figure()
    # demo_distr(T5, theoretical = StudentTDistr(5), xmin = -1e2, xmax=1e2)
    # figure()
    # demo_distr(num, theoretical = NormalDistr(0, 5**0.5), xmin = -1e1, xmax=1e1)
    # figure()
    # demo_distr(den, theoretical = ChiSquareDistr(5), xmin = -1e1, xmax=1e1)
    
    #N1 = NormalDistr(0,1); demo_distr(N1, theoretical = N1, title = "Normal test")
    #N2 = N1 + 1; demo_distr(N2, theoretical = NormalDistr(1,1))
    #N2 = 1 + N2; demo_distr(N2, theoretical = NormalDistr(2,1))
    #N2 = N2 - 1; demo_distr(N2, theoretical = NormalDistr(1,1))
    #Nerr = N1 + "a"
    #N3 = N1 + N2; demo_distr(N3, theoretical = NormalDistr(1,sqrt(2)))
    #negN2 = -N2; plotdistr(negN2)
    #N4 = N1 - N2; plotdistr(N4)

    #N5 = N1 ** 2; plotdistr(N5)
    #N6 = N2 ** 2; plotdistr(N6)
    #N7 = DivDistr(N1, N1)
    #N8 = DivDistr(N2, N2)
    #N9 = MulDistr(N2, SumDistr(N2, N2))
    #N10 = SquareDistr(N1)
    #N11 = N5 + N5; plotdistr(N11)
    #N12 = N5 + N11; plotdistr(N12)
    #N13 = MulDistr(N1, N1)
    #N13prime = N1 * NormalDistr(0,1); plotdistr(N13prime)
    #N14 = 0.5 * N2
    #N15 = N2 * -1
    #N16 = NormalDistr(0,1) / NormalDistr(0,1); plotdistr(N16)
    #N17 = 2 - N1

    # figure()
    # N18 = 2 / N1; plotdistr(N18)
    # N19 = (N18 + N18) / 2; plotdistr(N19)
    # N20 = (N19 * 2 + N18) / 3; plotdistr(N20)
    # N21 = (N20 * 3 + N18) / 4; plotdistr(N21)

    # absolute value
    # figure()
    # N22 = abs(N1); plotdistr(N22)
    # N23 = abs(N2); plotdistr(N23)
    # N24 = N22 + N23; plotdistr(N24)

    # figure()
    # #demo_distr(NormalDistr(0,1) / NormalDistr(0,1))
    # #figure()
    # N25 = atan(NormalDistr(0,1) / NormalDistr(0,1)); 
    # N26 = NormalDistr(0,1) / NormalDistr(0,1) 
    # N27 = NormalDistr(0,1) * (1 / NormalDistr(0,1)) 
    # figure()
    # demo_distr(N25, theoretical = UniformDistr(-pi/2, pi/2), title = "atan(Cauchy) = atan(N(0,1)/N(0/1))", histogram = True)
    # figure()
    # demo_distr(N26, theoretical = lambda x: 1.0/pi/(1+x*x), title = "N(0,1) / N(0,1) == N(0,1) * (1 / N(0,1))", histogram = False)
    # demo_distr(N27, theoretical = lambda x: 1.0/pi/(1+x*x), title = "N(0,1) / N(0,1) == N(0,1) * (1 / N(0,1))", histogram = False)

    # # powers, exponents, logs
    # figure()
    #N26 = exp(N1); print N26; plotdistr(N26)
    #N27 = N26 + N26; plotdistr(N27)
    # #N28 = exp(NormalDistr(0,1) / NormalDistr(0,1)); plotdistr(N28)
    # #N29 = N28 + N28; plotdistr(N29)
    # N30 = 2 ** N1; print N30; plotdistr(N30)
    #N31 = log(abs(N1)); print N31; plotdistr(N31)
    # N32 = abs(N1) ** N1; demo_distr(N32, xmin=0, xmax = 3, ymax = 2)
    # figure()
    # u = UniformDistr(1,2)**UniformDistr(1,2)
    # u.plot()
    # histdistr(u)
    # figure()
    # u = UniformDistr(0,1)**UniformDistr(0,2)
    # demo_distr(u, xmin=0, xmax = 1, ymax = 3)

    # figure()
    # U1 = UniformDistr(1,3)
    # # UN1 = U1 / N2; plotdistr(UN1)
    # # UN2 = U1 + N2
    # # UN3 = U1 - UniformDistr(2,5)
    # # UN4 = FuncDistr(MulDistr(U1, U1), f = lambda x: x/3.0, f_inv = lambda x: 3*x, f_inv_deriv = lambda x: 3)
    # UN5 = UniformDistr(1,2) / UniformDistr(3,4); plotdistr(UN5)
    # UN7 = N2 * UniformDistr(9,11); plotdistr(UN7)
    # UN9 = UniformDistr(9,11) * N2; plotdistr(UN9)
    # UN11 = UniformDistr(-2,1) / UniformDistr(-2,1); plotdistr(UN11)
    # UN6 = atan(UN5); plotdistr(UN6)
    # UN10 = atan(UniformDistr(3,5)); plotdistr(UN10); print UN10

    # figure()
    # UN8 = UniformDistr(1,3) / UniformDistr(-2,1); plotdistr(UN8)
    # UN12 = (UN8 + UN8) / 2; plotdistr(UN12)
    # UN13 = (UN12 * 2 + UN8) / 3; plotdistr(UN13)
    # UN14 = (UN13 * 3 + UN8) / 4; plotdistr(UN14)
    # UN14_2 = (UN14 * 4 + UN8) / 5; plotdistr(UN14_2)
    # UN14_2 = (UN14 * 4 + UN8) / 5; plotdistr(UN14_2)
    # UN14_3 = (UN14_2 * 5 + UN8) / 6; plotdistr(UN14_3)
    # UN14_4 = (UN14_3 * 6 + UN8) / 7; plotdistr(UN14_4)
    # UN14_5 = (UN14_4 * 7 + UN8) / 8; plotdistr(UN14_5)

    # the slash distribution
    #figure()
    #UN15 = NormalDistr(0,1) / UniformDistr(0,1); plotdistr(UN15)
    #UN16 = (UN15 + UN15) / 2; plotdistr(UN16)
    #UN17 = (UN16 * 2 + UN15) / 3; plotdistr(UN17)
    #UN18 = (UN17 * 3 + UN15) / 4; plotdistr(UN18)
    #UN19 = (UN18 * 4 + UN15) / 5; plotdistr(UN19)
    #UN20 = (UN19 * 5 + UN15) / 6; plotdistr(UN20)

    # from Springer and others
    #figure()
    #CauchyDistr().plot()
    #demo_distr(CauchyDistr(), histogram = False)
    #UN21 = NormalDistr(0,1) / NormalDistr(0,1) #* UniformDistr(-1,1)
    #demo_distr(UN21, histogram = True)
    #UN21.summary()
    #UN22 = NormalDistr(-1,1) / NormalDistr(-1,1)# * UniformDistr(0,1)
    #plotdistr(UN22)
    #UN23 = NormalDistr(-1,1) / NormalDistr(-1,1) * UniformDistr(0,1)
    #figure()
    #UN23.plot()
    #histdistr(UN23, l=-2, u=2)
    #UN23_copy = NormalDistr(-1,1) / NormalDistr(-1,1) * UniformDistr(0,1)
    #UN24 = (UN23 + UN23_copy) / 2
    #figure()
    #UN24.plot()
    #demo_distr(UN24, xmin = -2, xmax = 2)
    # tails
    # !!!! does not work with /2
    #UN24.get_piecewise_pdf().plot_tails()
    
    #U = UniformDistr(0,1)
    #U_inv = InvDistr(U) 
    #X = U * U_inv
    #Y = U / U
    #R = X.get_piecewise_pdf() - Y.get_piecewise_pdf()
    #figure()
    #R.plot()

    # Cauchy with params
    #demo_distr(CauchyDistr(gamma = 2, center = 1), histogram = True, xmin = -3, xmax = 5)

    # Gamma
    # figure()
    # demo_distr(GammaDistr(1,2), xmax = 20)
    # demo_distr(GammaDistr(2,2), xmax = 20)
    # demo_distr(GammaDistr(3,2), xmax = 20)
    # demo_distr(GammaDistr(5,1), xmax = 20)
    # demo_distr(GammaDistr(9,0.5), xmax = 20)
    # demo_distr(GammaDistr(0.5,2), xmax = 20, ymax = 1.2)
    # figure()
    # demo_distr(GammaDistr(1,1) + GammaDistr(1,1) + GammaDistr(1,1), theoretical = GammaDistr(3,1), xmax = 50)
    

    # Beta
    # figure()
    # print BetaDistr(alpha = 1, beta = 1)
    # demo_distr(BetaDistr(alpha = 1, beta = 1), theoretical = UniformDistr(0,1))
    # figure()
    # demo_distr(BetaDistr(alpha = 0.5, beta = 0.5), histogram = True, ymax = 3)
    # demo_distr(BetaDistr(alpha = 2, beta = 2), histogram = True, ymax = 3)
    # demo_distr(BetaDistr(alpha = 8, beta = 5), histogram = True, ymax = 3)

    # figure()
    # demo_distr(BetaDistr(alpha = 0.3, beta = 0.1), histogram = True, ymax = 3)
    # figure()
    # demo_distr(BetaDistr(alpha = 0.3, beta = 0.1) + BetaDistr(alpha = 0.3, beta = 0.1), ymax = 3)
    # figure()
    # demo_distr(BetaDistr(alpha = 0.3, beta = 0.1) + BetaDistr(alpha = 0.3, beta = 0.1) + BetaDistr(alpha = 0.3, beta = 0.1), ymax = 3)

    # figure()
    # bb = BetaDistr(alpha = 0.5, beta = 0.5) + BetaDistr(alpha = 0.5, beta = 0.5)
    # Xs, Ys =  bb.get_piecewise_pdf().segments[-1].f.getNodes()
    # #for x, y, xx in zip(Xs, Ys, bb.get_piecewise_pdf().segments[-1].f.Xs):
    # #    print repr(x), repr(xx), repr(y)
    # demo_distr(bb, histogram = True, ymax = 3)
    # figure()
    # bbb = bb + BetaDistr(alpha = 0.5, beta = 0.5)
    # demo_distr(bbb, histogram = True, ymax = 1)
    # figure()
    # bbbb = bbb + BetaDistr(alpha = 0.5, beta = 0.5)
    # demo_distr(bbbb, histogram = True, ymax = 1)
    # figure()
    # bbbbb = bbbb + BetaDistr(alpha = 0.5, beta = 0.5)
    # demo_distr(bbbbb, histogram = True, ymax = 1)

    # Pareto
    #figure()
    #p = ParetoDistr(1, 3)
    #demo_distr(p, xmin = 1, xmax = 1e20)

    #figure()
    #p2 = ParetoDistr(1.5)
    #demo_distr(p2, xmin = 1, xmax = 1e20)
    #figure()
    #p2.get_piecewise_cdf().plot(show_nodes = True, right=20)
    #figure()
    #demo_distr((p2+p2+p2+p2)/4.0, xmin = 1, xmax = 20)
    # demo_distr(p, xmin = 1, xmax = 20)
    # demo_distr(p+p, xmin = 1, xmax = 20)
    # figure()
    # demo_distr(log(p/3), xmin = 1, xmax = 20)
    # figure()
    # p2 = ParetoDistr(0.1)
    # demo_distr(p2, xmin = 1, xmax = 1e2, ymax = 0.1)
    # figure()
    # p2.get_piecewise_cdf().plot(show_nodes = True, right=5e1)
    # figure()
    # demo_distr((p2+p2)/2, xmin = 1, xmax = 1e2, ymax = 0.01)
    
    # c1 = ChiSquareDistr(1)
    # L = LevyDistr()
    # c = L**(-1)
    # figure() 
    # demo_distr(L**(-1), theoretical = c1,xmin = 0, xmax = 1e1, ymax = 3)
    # figure() 
    # demo_distr(1/c1, theoretical = L, xmin = 0, xmax = 10)
    # figure()
    # demo_distr(1/(L+L), theoretical = c1, xmin = 0, xmax = 1e1, ymax = 3)
    # 
    # print c.get_piecewise_pdf()
    

    # ChiSquareDistr
    # c1 = ChiSquareDistr(1)
    # figure()
    # c2 = c1 + c1
    # demo_distr(c2, theoretical = ChiSquareDistr(2))
    # figure()
    # c3 = c2 + c1
    # demo_distr(c3, theoretical = ChiSquareDistr(3))
    # figure()
    # c4 = c3 + c1
    # demo_distr(c4, theoretical = ChiSquareDistr(4))
    # figure()
    # c5 = c4 + c1
    # demo_distr(c5, theoretical = ChiSquareDistr(5))

    # # Levy
    # l = LevyDistr()
    # figure()
    # demo_distr(l, xmin = 0, xmax = 10)
    # demo_distr(l+l, xmin = 0, xmax = 10)
    # demo_distr(l*l, xmin = 0, xmax = 10)
    # figure()
    # demo_distr(1 / ChiSquareDistr(1), xmin = 0, xmax = 10)
    # demo_distr(1 / l, xmin = 0, xmax = 10)

    # # Laplace
    # figure()
    # demo_distr(LaplaceDistr())
    # demo_distr(LaplaceDistr() + LaplaceDistr())
    # figure()
    # demo_distr(abs(LaplaceDistr()), theoretical = ExponentialDistr())
    # figure()
    # demo_distr(NormalDistr()*NormalDistr() + NormalDistr()*NormalDistr(), theoretical = LaplaceDistr())
    
    # Student t
    # figure()
    # demo_distr(StudentTDistr(3), xmin = -5, xmax = 5)
    # demo_distr(StudentTDistr(0.5), xmin = -5, xmax = 5)
    # demo_distr(StudentTDistr(100), xmin = -5, xmax = 5)
    # figure()
    # demo_distr(NormalDistr() / sqrt(ChiSquareDistr(3) / 3), theoretical = StudentTDistr(3), xmin = -5, xmax = 5)
    # figure()
    # demo_distr(NormalDistr() / (sqrt(ChiSquareDistr(3)) / sqrt(3.0)), theoretical = StudentTDistr(3), xmin = -5, xmax = 5)
    # figure()
    # demo_distr(NormalDistr() / (sqrt(ChiSquareDistr(3))) * sqrt(3.0), theoretical = StudentTDistr(3), xmin = -5, xmax = 5)

    figure()
    n = 4
    T10 = (NormalDistr() / sqrt(ChiSquareDistr(n))) * n ** 0.5
    demo_distr(T10, theoretical = StudentTDistr(n), xmin = -1e10, xmax=1e10)
    figure()
    def test_student(n):
        N1 = NormalDistr()
        print "================================================num===="
        num = N1
        for i in range(n-1): 
            num  += N1
        num.get_piecewise_pdf()
        C1 = ChiSquareDistr(1)
        print "================================================den===="
        den = C1
        for i in range(n-1): 
            den  += C1
        Tn = num / den**0.5 #* 5 ** 0.5
        
        print Tn.get_piecewise_pdf().segments[0].f.vl.getNodes()
        figure()
        demo_distr(num, theoretical = NormalDistr(0, n**0.5), xmin = -1e2, xmax=1e2)
        figure()
        demo_distr(den, theoretical = ChiSquareDistr(n), xmin = 0, xmax=1e1)
        figure()
        demo_distr(Tn, theoretical = StudentTDistr(n), xmin = -1e1, xmax=1e1)
     	return num, den, Tn
    test_student(5)
    # test_student(4)

    # demo_distr(NormalDistr(1,1) * NormalDistr(1,1))
    # figure()
    # demo_distr(NormalDistr(10,1) * NormalDistr(10,1))
    # figure()
    # demo_distr(NormalDistr(100,1) * NormalDistr(100,1))

    # figure()
    # demo_distr(FDistr(2, 2), xmax = 10)
    # figure()
    # demo_distr(FDistr(4, 5), xmax = 10)
    # figure()
    # demo_distr(FDistr(2, 2) + FDistr(4, 5) + FDistr(1, 1), xmax = 10)

    figure()
    df1, df2, df3 = 2, 101,40
    c1 =ChiSquareDistr(df1)
    c2 =ChiSquareDistr(df2)
    c3 =ChiSquareDistr(df3)
    c4 =ChiSquareDistr(df3)
    d = c1 + c2
    c1.summary()
    c2.summary()
    c3.summary()
    d.summary()
    d.plot(right=1e4)
    demo_distr(d, theoretical = ChiSquareDistr(df1  + df2 ), xmax = 1e4)
    
    show()
    0/0

    # figure()
    # demo_distr(SemicircleDistr())
    figure()
    demo_distr(SemicircleDistr() + SemicircleDistr())
    # figure()
    # demo_distr(SemicircleDistr() + SemicircleDistr() + SemicircleDistr())
    figure()
    demo_distr(SemicircleDistr() + BetaDistr(0.2, 0.9))
    
    figure()
    demo_distr(SemicircleDistr())
    figure()
    demo_distr(BetaDistr(0.2, 0.9))
    
    figure()
    F = SemicircleDistr() + BetaDistr(0.2, 0.9)
    c = F.get_piecewise_cdf()
    F.plot()
    c.plot()
    figure()
    #hist(F.rand_invcdf(10000))
    F.plot()
    #show_distr = histdistr
    show_distr = plotdistr

    # figure()
    # demo_distr(SemicircleDistr())
    figure()
    demo_distr(SemicircleDistr() + SemicircleDistr())
    figure()
    demo_distr(SemicircleDistr() + SemicircleDistr() + SemicircleDistr())
    # this does not work (at least not yet ;)
    figure()
    dd = SemicircleDistr() + BetaDistr(0.3, 0.1)
    demo_distr(dd)
    figure()
    dd = SemicircleDistr() + BetaDistr(0.5, 0.5)
    demo_distr(dd)
    

    #show_distr = histdistr
    show_distr = plotdistr

    #show_distr(N1)
    #show_distr(N2)
    #show_distr(UN2)
    #show_distr(N4)
    #show_distr(N5)
    #show_distr(N6)
    #show_distr(N7)
    #show_distr(N8)
    #show_distr(N9)
    #show_distr(N10);show_distr(N13) # Example: X**2 the same as X*X with our semantics
    #show_distr(N10);show_distr(N13prime) # Example: X**2 not the same as X*X.copy()
    #show_distr(N11)
    #show_distr(N14);show_distr(N15) # multiply by a constant
    #show_distr(U1)
    #show_distr(UN1)
    #show_distr(UN2)
    #show_distr(UN3);print UN3.breaks
    #show_distr(UN4)
    #show_distr(UN6)
    #show_distr(UN7)
    #show_distr(UN8, l=-6, u=6) # my favorite distr
    #show_distr(UN9)
    #show_distr(UN10);print UN10.breaks
    #show_distr(UN11)
    #histdistr(UN11, l=4, u=4)
    #show_distr(UN1);print UN1.breaks;histdistr(UN1, l = -10, u = 10)
    #show_distr(UI1); print "U1.err =",UI1.err
    #show_distr(UI2);




    ## another example: http://www.physicsforums.com/showthread.php?t=75889
    ## probability density of two resistors in parallel XY/(X+Y)
    ##
    ## XY an X+Y are not independent: we are not yet ready to handle this
    #L = 40; U = 70
    #X = uniformDistr(100,120)
    #Y = uniformDistr(100,120)
    #N = mulDistr(X,Y)
    #D = sumDistr(X,Y)
    #Ni = interpolatedDistr(N)
    #Di = interpolatedDistr(D)
    #R = divDistr(Ni, Di)
    #Ri = interpolatedDistr(R)
    #print integrate(lambda x: Ri.PDF(x), limit=100)
    #show_distr(Ri, L, U);histdistr(R, l = L, u = U, n = 1000000)
    #xlim(L, U)


    # Distrete
    
    # figure()
    # I = One()
    # Two = I + I
    # Two.plot()
    # Two.get_piecewise_cdf().plot()
    # histdistr(Two)
    # 
    # figure()
    # d = DiscreteDistr(xi =[0, 1], pi = [0.2, 0.8])
    # 
    # b5 = d + d + d + d + d
    # b5.plot()
    # b5.get_piecewise_cdf().plot()
    # from pylab import hist
    # histdistr(b5)
    # 
    # d = DiscreteDistr(xi =[1, 2], pi = [0.2, 0.8])
    # U = UniformDistr(0,2)
    # A1 = d + U
    # A2 = d * U
    # A3 = d / U
    # A4 = U / d
    # figure()
    #  
    # A1.plot()
    # A2.plot()
    # A3.plot()
    # A4.plot()
    # histdistr(A1)
    # histdistr(A2)
    # histdistr(A3, l=0.5, u =5)
    # histdistr(A4)
    # 
    # figure()
    # A1.get_piecewise_cdf().plot()
    # A2.get_piecewise_cdf().plot()
    # A3.get_piecewise_cdf().plot()
    # A4.get_piecewise_cdf().plot()
    
        
    show()
