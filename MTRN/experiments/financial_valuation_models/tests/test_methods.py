"""Statistical invariants that protect the historical simulation."""
import sys,unittest,tempfile,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'code'))
from settings import *
import numpy as np,pandas as pd
from learning import Regressor,tune,feature_sets
from variance_models import variance_filter,fit_garchx
from score import metric_values
from common.code.point_in_time import PointInTimeFacts
from unittest.mock import patch

class Methods(unittest.TestCase):
    def test_garchx_reduces_to_garch(self):
        e=np.array([1.,-2.,.5,3.]);p=np.array([.1,.08,.85,0.]);z=np.ones((4,1));v=variance_filter(e,z,p,2.)
        expected=[2.]
        for shock in e[:-1]:expected.append(.1+.08*shock**2+.85*expected[-1])
        np.testing.assert_allclose(v,expected)
    def test_garchx_external_term_uses_previous_session(self):
        e=np.zeros(4);z=np.array([[0.],[0.],[10.],[1000.]])
        v=variance_filter(e,z,[1.,.1,.5,2.],2.)
        np.testing.assert_allclose(v,[2.,2.,2.,22.])
    def test_garchx_positive_forecast(self):
        rng=np.random.default_rng(19);r=rng.normal(0,.02,400);z=rng.normal(0,1,(400,1))**2
        prediction,info=fit_garchx(r,z,21)
        self.assertGreater(prediction,0);self.assertLessEqual(info['alpha']+info['beta'],.9950001)
    def test_preprocessing_does_not_learn_from_future(self):
        x=pd.DataFrame({'a':np.arange(100,dtype=float),'b':np.arange(100,dtype=float)**2});x.loc[0,'a']=np.nan
        fit=Regressor('ridge',1).fit(x.iloc[:80],np.sin(np.arange(80)))
        before=(fit.center.copy(),fit.scale.copy(),fit.low.copy(),fit.high.copy(),fit.median.copy())
        y=fit.predict(x.iloc[[80]])
        future=x.iloc[81:].copy()*1e9;fit.predict(future)
        for a,b in zip(before,(fit.center,fit.scale,fit.low,fit.high,fit.median)):np.testing.assert_array_equal(a,b)
        np.testing.assert_array_equal(y,fit.predict(x.iloc[[80]]))
    def test_coverage_is_training_only(self):
        x=pd.DataFrame({'good':np.arange(100,dtype=float),'future_only':[np.nan]*80+list(range(20))})
        fit=Regressor().fit(x.iloc[:80],np.arange(80));self.assertEqual(fit.columns,['good'])
    def test_lag_difference_and_percentage_are_distinct(self):
        s=pd.Series([10.,15.,12.]);self.assertEqual(s.shift(1).iloc[-1],15)
        self.assertEqual(s.diff().iloc[-1],-3);self.assertAlmostEqual(s.pct_change().iloc[-1],-.2)
    def test_future_filing_cannot_revise_old_snapshot(self):
        sessions=pd.bdate_range('2020-01-01','2021-12-31')
        base=dict(end='2019-12-31',val=100,form='10-K',filed='2020-02-03',accn='old')
        revised=dict(base,val=999,filed='2021-02-03',accn='new')
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/'facts.json';path.write_text(json.dumps({'facts':{'us-gaap':{'Assets':{'units':{'USD':[base,revised]}}}}}))
            sel=PointInTimeFacts(path,sessions,'TEST')
            self.assertTrue(np.isnan(sel.value('Assets','2020-02-03')))
            self.assertEqual(sel.value('Assets','2020-02-04'),100)
            self.assertEqual(sel.value('Assets','2021-02-04'),999)
    def test_three_month_inner_labels_are_purged(self):
        dates=pd.date_range('2010-01-31',periods=90,freq='ME').strftime('%Y-%m-%d').to_numpy()
        x=pd.DataFrame({'date':dates,'value':np.arange(90)});seen=[]
        class Fake:
            def __init__(self,*args):pass
            def fit(self,X,y):self.end=X.date.max();seen.append(self.end);return self
            def predict(self,X):
                self_boundary=pd.Timestamp(X.date.min());self_end=pd.Timestamp(self.end)+pd.offsets.MonthEnd(3)
                if self_end>self_boundary:raise AssertionError('Unmatured label entered training')
                return np.zeros(len(X))
        with patch('learning.Regressor',Fake):tune('ols',x,np.ones(90),dates,horizon=3)
        self.assertEqual(len(seen),2)
        self.assertEqual(seen[0],dates[63]);self.assertEqual(seen[1],dates[75])
    def test_metrics_and_qlike_calibration(self):
        d=pd.DataFrame({'actual':[.01,.02],'prediction':[.01,.02],'benchmark':[.015,.015],'task':['variance']*2,'fallback':[False]*2,'target_end':['2020-01-31','2020-02-29']})
        m=metric_values(d);self.assertAlmostEqual(m['qlike'],0);self.assertAlmostEqual(m['r2_oos'],1)
        d['prediction']*=2;self.assertGreater(metric_values(d)['qlike'],0)
    def test_primary_factors_exclude_claims_proxies_and_targets(self):
        stages,full=feature_sets()
        self.assertFalse(any(n.endswith('_target') or 'proxy' in n for n in full))
        self.assertTrue(set(['roic_proxy','ev_ebitda_proxy','ev_sales_proxy']).issubset(stages['claims_proxy_sensitivity']))
    def test_block_removal_also_removes_derived_columns(self):
        from learning import groups,parents
        stages,full=feature_sets();g=groups()
        for block in ['valuation','financial','market','industry','business','momentum','risk']:
            leaked=[n for n in stages['without_'+block] if block in parents(n,g)]
            self.assertEqual(leaked,[],f'{block} survives its own removal via {leaked}')
        self.assertNotIn('pe_pct_change',stages['without_valuation'])
        self.assertNotIn('beta_252',stages['without_market'])
    def test_protocol_ladder_is_nested_and_ends_at_the_full_set(self):
        stages,full=feature_sets()
        order=['P1_financial','P2_valuation','P3_transform','P4_market','P5_industry','P6_business']
        for earlier,later in zip(order,order[1:]):
            self.assertTrue(set(stages[earlier])<=set(stages[later]),f'{earlier} is not nested inside {later}')
        self.assertEqual(set(stages['P6_business']),set(full))
    def test_out_of_sample_r2_uses_the_real_time_benchmark(self):
        d=pd.DataFrame({'actual':[.02,-.01,.03],'prediction':[.01,.00,.02],'benchmark':[.015,.015,.015],
                        'task':['return']*3,'fallback':[False]*3,'target_end':['2023-01-31','2023-02-28','2023-03-31']})
        m=metric_values(d)
        e=d.actual-d.prediction;b=d.actual-d.benchmark
        self.assertAlmostEqual(m['r2_oos'],1-float((e**2).sum()/(b**2).sum()))
        # Using the test-sample mean instead would be a different, unknowable quantity.
        self.assertNotAlmostEqual(m['r2_oos'],1-float((e**2).sum()/((d.actual-d.actual.mean())**2).sum()))
    def test_holm_never_reduces_a_p_value_and_preserves_order(self):
        from score import holm
        raw=np.array([.001,.04,.2,.5])
        adjusted=holm(raw)
        self.assertTrue(np.all(adjusted>=raw-1e-12))
        self.assertTrue(np.all(np.diff(adjusted)>=-1e-12))
        np.testing.assert_allclose(holm(np.array([.01])),[.01])
    def test_later_data_cannot_change_an_earlier_forecast(self):
        rng=np.random.default_rng(7)
        x=pd.DataFrame(rng.normal(size=(120,4)),columns=list('abcd'));y=rng.normal(size=120)
        first=Regressor('ridge',1.).fit(x.iloc[:90],y[:90]).predict(x.iloc[[90]])[0]
        perturbed=x.copy();perturbed.iloc[95:]*=1e6
        second=Regressor('ridge',1.).fit(perturbed.iloc[:90],y[:90]).predict(perturbed.iloc[[90]])[0]
        self.assertAlmostEqual(first,second,places=12)
    def test_equity_fallback_is_gated_on_measured_materiality(self):
        import features
        sessions=pd.bdate_range('2018-01-01','2022-12-31')
        def facts(nci):
            return {'facts':{'us-gaap':{
              features.EQUITY_PARENT:{'units':{'USD':[dict(end='2019-12-31',val=1000,form='10-K',filed='2020-02-03',accn='a')]}},
              features.EQUITY_TOTAL:{'units':{'USD':[dict(end='2019-12-31',val=1000+nci,form='10-K',filed='2020-02-03',accn='a'),
                                                     dict(end='2020-12-31',val=1200,form='10-K',filed='2021-02-03',accn='b')]}}}}}
        for nci,expected in [(1,True),(200,False)]:
            with tempfile.TemporaryDirectory() as td:
                path=Path(td)/'f.json';path.write_text(json.dumps(facts(nci)))
                sel=PointInTimeFacts(path,sessions,'TEST')
                value,basis=features.equity_at(sel,'2021-06-01','2020-12-31')
                self.assertEqual(np.isfinite(value),expected,basis)
                self.assertIn('tolerance',basis)

if __name__=='__main__':unittest.main(verbosity=2)
