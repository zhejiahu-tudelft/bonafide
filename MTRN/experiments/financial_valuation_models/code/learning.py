"""Small deterministic estimators with training-only preprocessing and tuning."""
import hashlib, json, warnings
import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression,Ridge,Lasso,ElasticNet
from sklearn.ensemble import RandomForestRegressor,GradientBoostingRegressor
from settings import SEED,CONFIG

# Every tuned procedure may choose to forecast the training mean: when validation
# finds no usable signal, the fitted model collapses to the historical-mean benchmark.
INTERCEPT='intercept_only'

class Regressor:
    def __init__(self,kind='ridge',parameter=1.):
        # Elastic Net carries a (lambda, mixing) pair; every other estimator a scalar.
        self.kind=kind;self.parameter=parameter;self.intercept_only=parameter==INTERCEPT
        self.alpha,self.mix=(None,None) if self.intercept_only else (parameter if isinstance(parameter,(tuple,list)) else (parameter,.5))
    def fit(self,X,y):
        a=X.replace([np.inf,-np.inf],np.nan)
        gate=CONFIG['feature_training_min_coverage'];coverage=a.notna().mean();spread=a.std()
        # Record why each candidate predictor is absent from this particular fit.
        self.candidates=list(a.columns)
        self.excluded={c:('training coverage below gate' if coverage[c]<gate else 'constant in training window')
                       for c in a.columns if not (coverage[c]>=gate and spread[c]>1e-12)}
        self.columns=[c for c in a.columns if c not in self.excluded]
        self.ymean=float(np.mean(y));self.yscale=max(float(np.std(y)),1e-8);self.n=len(a)
        if self.intercept_only:
            self.names=[];self.model=None;self._design=None;self.missing=np.zeros(0,bool)
            return self
        if not self.columns:raise ValueError('No eligible varying predictors in training data')
        a=a[self.columns].to_numpy(float)
        self.low=np.nanquantile(a,.01,axis=0);self.high=np.nanquantile(a,.99,axis=0)
        a=np.clip(a,self.low,self.high);self.median=np.nanmedian(a,axis=0)
        self.missing=np.any(~np.isfinite(a),axis=0)
        b=np.where(np.isfinite(a),a,self.median)
        self.center=b.mean(axis=0);self.scale=b.std(axis=0);self.scale[self.scale<1e-12]=1
        self.names=self.columns+[x+' missing' for x,m in zip(self.columns,self.missing) if m]
        b=self.transform(X)
        z=(np.asarray(y)-self.ymean)/self.yscale
        p=self.alpha
        if self.kind=='ols':model=LinearRegression()
        # Per-observation penalty: the same lambda means the same shrinkage per
        # observation in an individual fit and in a four-issuer pooled fit.
        elif self.kind=='ridge':model=Ridge(alpha=p*len(b))
        elif self.kind=='lasso':model=Lasso(alpha=p,max_iter=10000,tol=1e-5)
        elif self.kind=='elastic':model=ElasticNet(alpha=p,l1_ratio=self.mix,max_iter=10000,tol=1e-5)
        elif self.kind=='forest':model=RandomForestRegressor(n_estimators=80,max_depth=3 if p==0 else 5,min_samples_leaf=8 if p==0 else 12,max_features=.7,n_jobs=1,random_state=SEED)
        elif self.kind=='boost':model=GradientBoostingRegressor(n_estimators=60 if p==0 else 100,max_depth=1 if p==0 else 2,min_samples_leaf=10,learning_rate=.04,loss='squared_error',random_state=SEED)
        else:raise ValueError(self.kind)
        with warnings.catch_warnings():warnings.simplefilter('ignore');model.fit(b,z)
        self.model=model;self._design=b
        return self
    def transform(self,X):
        a=X[self.columns].replace([np.inf,-np.inf],np.nan).to_numpy(float)
        missing=~np.isfinite(a);a=np.clip(a,self.low,self.high)
        a=np.where(missing,self.median,a);a=(a-self.center)/self.scale
        return np.column_stack([a,missing[:,self.missing].astype(float)])
    def predict(self,X):
        if self.intercept_only:return np.full(len(X),self.ymean)
        return self.ymean+self.yscale*self.model.predict(self.transform(X))
    def effects(self):
        if self.intercept_only:return []
        values=getattr(self.model,'coef_',getattr(self.model,'feature_importances_',np.zeros(len(self.names))))
        effect_type='coefficient per training SD in target units' if hasattr(self.model,'coef_') else 'training impurity importance, noncausal'
        if hasattr(self.model,'coef_'):values=values*self.yscale
        return [dict(variable=n,effect=float(v),effect_type=effect_type,center=float(self.center[i]) if i<len(self.columns) else 0,scale=float(self.scale[i]) if i<len(self.columns) else 1,impute=float(self.median[i]) if i<len(self.columns) else 0,clip_lo=float(self.low[i]) if i<len(self.columns) else 0,clip_hi=float(self.high[i]) if i<len(self.columns) else 1) for i,(n,v) in enumerate(zip(self.names,values))]
    def describe(self):
        """Complexity and selection record for this fitted specification.

        Rank and condition number are for the centred, standardised design actually
        passed to the estimator (missing indicators included). Removing exactly
        duplicated columns does not guarantee full rank or remove economic overlap.
        Effective degrees of freedom: trace of the ridge hat matrix, the rank for OLS,
        the count of nonzero coefficients for Lasso/Elastic Net; trees report leaves.
        """
        record=dict(candidates=len(self.candidates),retained=len(self.columns),
            missing_indicators=int(np.sum(self.missing)),
            excluded_low_coverage=sum(v.startswith('training coverage') for v in self.excluded.values()),
            excluded_constant=sum(v.startswith('constant') for v in self.excluded.values()),
            # Identity of the predictors that passed the gate, before any selection, so
            # identical sets on both sides of a contrast reveal an untestable comparison.
            retained_set=hashlib.sha1('|'.join(self.columns).encode()).hexdigest()[:12] if self.columns else 'none',
            intercept_only=self.intercept_only,train_rows=self.n,rank=0,condition_number=np.nan,effective_df=0.,nonzero_coefficients=0,tree_leaves=np.nan)
        if self.intercept_only:return record
        x=self._design-self._design.mean(axis=0);s=np.linalg.svd(x,compute_uv=False);tol=s.max()*max(x.shape)*np.finfo(float).eps if s.size else 0
        record['rank']=int(np.sum(s>tol));record['condition_number']=float(s[0]/s[s>tol][-1]) if record['rank'] else np.nan
        coef=getattr(self.model,'coef_',None)
        if coef is not None:record['nonzero_coefficients']=int(np.sum(np.abs(coef)>1e-12))
        if self.kind=='ridge':record['effective_df']=float(np.sum(s**2/(s**2+self.alpha*len(x))))
        elif self.kind=='ols':record['effective_df']=float(record['rank'])
        elif self.kind in ('lasso','elastic'):record['effective_df']=float(record['nonzero_coefficients'])
        else:
            record['effective_df']=np.nan
            trees=self.model.estimators_.ravel() if self.kind=='boost' else self.model.estimators_
            record['tree_leaves']=int(sum(t.get_n_leaves() for t in trees))
        return record

class SpecLog:
    """Per-fit specification records plus a change log of excluded predictors."""
    def __init__(self):self.rows=[];self.exclusions=[];self.last={}
    def add(self,fit,**key):
        self.rows.append(dict(**key,hyperparameter=str(fit.parameter),**fit.describe()))
        k=tuple(key.get(x) for x in ('task','horizon','ticker','model','window'))
        now=fit.excluded;before=self.last.get(k,{})
        for v in sorted(set(now)|set(before)):
            if now.get(v)!=before.get(v):self.exclusions.append(dict(**key,variable=v,status=now.get(v,'readmitted')))
        self.last[k]=dict(now)

def candidates(kind):
    if kind=='ols':return [0]
    grid=CONFIG['lambda_grid']
    if kind in ['forest','boost']:base=[0,1]
    elif kind=='elastic':base=[(a,m) for a in grid for m in CONFIG['elastic_mixing']]
    else:base=list(grid)
    return ([INTERCEPT] if CONFIG['intercept_only_candidate'] else [])+base

def simplicity(parameter,kind='ridge'):
    """Tie-rule order, simplest first: intercept-only, then smaller tree capacity or
    a stronger penalty, then a larger L1 share."""
    if parameter==INTERCEPT:return (0,0.,0.)
    if kind in ('forest','boost','ols'):return (1,float(parameter),0.)
    alpha,mix=parameter if isinstance(parameter,(tuple,list)) else (parameter,.5)
    return (1,-float(alpha),-float(mix))

def tune(kind,X,y,dates,variance=False,horizon=1):
    """Choose a hyperparameter on the last 24 origins of the training history.

    Mirrors the outer procedure: at each inner origin the candidate is refitted on
    rows dated before it whose targets had matured by it, then forecasts that
    origin's rows. Losses are pooled over the 24 origins (two 12-month blocks).
    """
    dates=np.asarray(dates);y=np.asarray(y,float);unique=np.sort(np.unique(dates));options=candidates(kind)
    if len(options)==1:return options[0],[]
    if len(unique)<84:
        return min(options,key=lambda p:simplicity(p,kind)),[dict(parameter='insufficient history',validation_loss=np.nan)]
    label_ends=(pd.to_datetime(dates)+pd.offsets.MonthEnd(horizon)).strftime('%Y-%m-%d').to_numpy()
    folds=[((dates<v)&(label_ends<=v),dates==v) for v in unique[-24:]]
    matured=all(label_ends[train].max()<=v for (train,_),v in zip(folds,unique[-24:]))
    trials=[]
    for p in options:
        errors=[]
        for train,valid in folds:
            try:
                fit=Regressor(kind,p).fit(X.loc[train],y[train]);pred=fit.predict(X.loc[valid])
                if variance:
                    smear=np.mean(np.exp(y[train]-fit.predict(X.loc[train])))
                    ratio=np.exp(y[valid]-pred)/smear
                    errors.extend(ratio-np.log(ratio)-1)
                else:errors.extend((y[valid]-pred)**2)
            except Exception:errors.append(np.inf)
        trials.append(dict(parameter=str(p),validation_loss=float(np.mean(errors)),inner_origins=len(folds),
                           first_inner_origin=unique[-24],labels_matured=matured,_p=p))
    finite=[x for x in trials if np.isfinite(x['validation_loss'])]
    best=min(finite,key=lambda x:(x['validation_loss'],simplicity(x['_p'],kind)))['_p'] if finite else min(options,key=lambda p:simplicity(p,kind))
    for x in trials:x.pop('_p')
    return best,trials

def load_frame():
    from settings import OUT
    return pd.read_csv(OUT/'monthly_features_as_known.csv').sort_values(['ticker','date'])

def groups():
    from settings import OUT
    return json.loads((OUT/'feature_groups.json').read_text())

# Every derived column names the blocks it is built from. Removing a block must
# remove its differences, lags, z-scores, percentiles and interactions too, or a
# nominally valuation-free model still carries valuation information.
DERIVED={
 'industry_relative':['industry','market'],'relative_momentum':['momentum','market'],
 'industry_momentum_relative':['momentum','industry'],
 'pe_pct_change':['valuation'],'pe_percentile':['valuation'],
 'earnings_yield_percentile':['valuation'],'fcf_equipment_yield_relative':['valuation'],
 'revenue_valuation_interaction':['financial','valuation'],
 'margin_valuation_interaction':['financial','valuation'],
 'beta_252':['risk','market'],'idio_vol':['risk','market'],
 'eps_change_price':['financial'],'loss_transition':['financial'],
 'earnings_age_days':['financial'],'financial_age_days':['financial'],
}

def parents(name,g):
    """Economic blocks a column depends on, from its own block plus its construction."""
    blocks={b for b,names in g.items() if name in names}
    blocks|=set(DERIVED.get(name,[]))
    for base,names in g.items():
        for source in names:
            if name!=source and name.startswith(source+'_'):blocks.add(base);blocks|=set(DERIVED.get(source,[]))
    return blocks

def feature_sets():
    g=groups();order=['market','financial','valuation','momentum','risk','industry','business','transform','interaction']
    stages={};cols=[]
    for i,name in enumerate(order,1):
        cols=cols+g[name];stages[f'A{i}_{name}']=list(dict.fromkeys(cols))
    full=stages['A8_transform']
    # Protocol section 10 orders the ladder financials first; the A-ladder above
    # answers the separately required market-and-industry-controls-first check.
    protocol=[('P1_financial',['financial']),('P2_valuation',['financial','valuation']),
      ('P3_transform',['financial','valuation','transform']),
      ('P4_market',['financial','valuation','transform','market','momentum','risk']),
      ('P5_industry',['financial','valuation','transform','market','momentum','risk','industry']),
      ('P6_business',['financial','valuation','transform','market','momentum','risk','industry','business'])]
    for name,blocks in protocol:
        stages[name]=[c for c in full if parents(c,g)<=set(blocks)]
    stages['financial_only']=g['financial']
    stages['financial_valuation']=g['financial']+g['valuation']
    for block in ['market','financial','valuation','momentum','risk','industry','business']:
        stages['without_'+block]=[n for n in full if block not in parents(n,g)]
    stages['claims_proxy_sensitivity']=full+g['claims_proxy']
    stages['mine_inclusive_fcf']=full+g['mine_inclusive_fcf']
    return stages,full
