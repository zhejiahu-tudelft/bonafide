"""Small deterministic estimators with training-only preprocessing and tuning."""
import json, warnings
import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression,Ridge,Lasso,ElasticNet
from sklearn.ensemble import RandomForestRegressor,GradientBoostingRegressor
from settings import SEED,CONFIG

class Regressor:
    def __init__(self,kind='ridge',parameter=1.):
        # Elastic Net carries a (penalty, mixing) pair; every other estimator a scalar.
        self.kind=kind;self.parameter=parameter
        self.alpha,self.mix=(parameter if isinstance(parameter,(tuple,list)) else (parameter,.5))
    def fit(self,X,y):
        a=X.replace([np.inf,-np.inf],np.nan)
        names=a.columns[(a.notna().mean()>=CONFIG['feature_training_min_coverage']) & (a.std()>1e-12)]
        self.columns=list(names);a=a[names].to_numpy(float)
        if not len(names):raise ValueError('No eligible varying predictors in training data')
        self.low=np.nanquantile(a,.01,axis=0);self.high=np.nanquantile(a,.99,axis=0)
        a=np.clip(a,self.low,self.high);self.median=np.nanmedian(a,axis=0)
        self.missing=np.any(~np.isfinite(a),axis=0)
        b=np.where(np.isfinite(a),a,self.median)
        self.center=b.mean(axis=0);self.scale=b.std(axis=0);self.scale[self.scale<1e-12]=1
        self.names=self.columns+[x+' missing' for x,m in zip(self.columns,self.missing) if m]
        b=self.transform(X)
        self.ymean=float(np.mean(y));self.yscale=max(float(np.std(y)),1e-8)
        z=(np.asarray(y)-self.ymean)/self.yscale
        p=self.alpha
        if self.kind=='ols':model=LinearRegression()
        elif self.kind=='ridge':model=Ridge(alpha=p)
        elif self.kind=='lasso':model=Lasso(alpha=p,max_iter=10000,tol=1e-5)
        elif self.kind=='elastic':model=ElasticNet(alpha=p,l1_ratio=self.mix,max_iter=10000,tol=1e-5)
        elif self.kind=='forest':model=RandomForestRegressor(n_estimators=80,max_depth=3 if p==0 else 5,min_samples_leaf=8 if p==0 else 12,max_features=.7,n_jobs=1,random_state=SEED)
        elif self.kind=='boost':model=GradientBoostingRegressor(n_estimators=60 if p==0 else 100,max_depth=1 if p==0 else 2,min_samples_leaf=10,learning_rate=.04,loss='squared_error',random_state=SEED)
        else:raise ValueError(self.kind)
        with warnings.catch_warnings():warnings.simplefilter('ignore');model.fit(b,z)
        self.model=model
        return self
    def transform(self,X):
        a=X[self.columns].replace([np.inf,-np.inf],np.nan).to_numpy(float)
        missing=~np.isfinite(a);a=np.clip(a,self.low,self.high)
        a=np.where(missing,self.median,a);a=(a-self.center)/self.scale
        return np.column_stack([a,missing[:,self.missing].astype(float)])
    def predict(self,X):return self.ymean+self.yscale*self.model.predict(self.transform(X))
    def effects(self):
        values=getattr(self.model,'coef_',getattr(self.model,'feature_importances_',np.zeros(len(self.names))))
        effect_type='coefficient per training SD in target units' if hasattr(self.model,'coef_') else 'training impurity importance, noncausal'
        if hasattr(self.model,'coef_'):values=values*self.yscale
        return [dict(variable=n,effect=float(v),effect_type=effect_type,center=float(self.center[i]) if i<len(self.columns) else 0,scale=float(self.scale[i]) if i<len(self.columns) else 1,impute=float(self.median[i]) if i<len(self.columns) else 0,clip_lo=float(self.low[i]) if i<len(self.columns) else 0,clip_hi=float(self.high[i]) if i<len(self.columns) else 1) for i,(n,v) in enumerate(zip(self.names,values))]

def candidates(kind):
    if kind in ['forest','boost']:return [0,1]
    if kind=='ols':return [0]
    if kind=='elastic':return [(a,m) for a in CONFIG['regularization_grid'] for m in CONFIG['elastic_mixing']]
    return list(CONFIG['regularization_grid'])

def simplicity(parameter):
    """Ordering for the tie rule: a stronger penalty is the simpler candidate."""
    alpha,mix=parameter if isinstance(parameter,(tuple,list)) else (parameter,.5)
    return (-float(alpha),-float(mix))

def tune(kind,X,y,dates,variance=False,horizon=1):
    unique=np.sort(np.unique(dates));trials=[]
    if len(unique)<84:return candidates(kind)[-1],[]
    for p in candidates(kind):
        errors=[]
        for offset in [24,12]:
            boundary=unique[-offset];end=unique[-offset+12] if offset>12 else None
            train=np.asarray(dates)<boundary;valid=np.asarray(dates)>=boundary
            label_ends=(pd.to_datetime(dates)+pd.offsets.MonthEnd(horizon)).strftime('%Y-%m-%d').to_numpy()
            train &= label_ends<=boundary
            if end is not None:valid &= np.asarray(dates)<end
            try:
                fit=Regressor(kind,p).fit(X.loc[train],np.asarray(y)[train]);pred=fit.predict(X.loc[valid])
                if variance:
                    smear=np.mean(np.exp(np.asarray(y)[train]-fit.predict(X.loc[train])))
                    ratio=np.exp(np.asarray(y)[valid]-pred)/smear
                    errors.extend(ratio-np.log(ratio)-1)
                else:errors.extend((np.asarray(y)[valid]-pred)**2)
            except Exception:errors.append(np.inf)
        trials.append(dict(parameter=p,validation_mse=float(np.mean(errors))))
    finite=[x for x in trials if np.isfinite(x['validation_mse'])]
    if not finite:return candidates(kind)[-1],trials
    best=min(finite,key=lambda x:(x['validation_mse'],simplicity(x['parameter'])))
    return best['parameter'],trials

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
