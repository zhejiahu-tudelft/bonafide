"""Independent arithmetic, information-timing and event-window regression tests."""
import unittest,tempfile,json
from unittest.mock import patch
from pathlib import Path
import numpy as np,pandas as pd
from settings import *
from common.code.attribution_statistics import *
from common.code.point_in_time import PointInTimeFacts
from market_analysis import french,load_prices

class Methods(unittest.TestCase):
    def test_paired_identical_series(self):
        x=np.random.default_rng(11).normal(size=120)/100
        d=pd.DataFrame({'MTRN':x,'peer':x},index=pd.bdate_range('2020-01-01',periods=120))
        a,b=bootstrap_moments(d,10,100,4)
        self.assertAlmostEqual(a.iloc[0]['variance'],sum((x-x.mean())**2)/119)
        self.assertEqual(b.iloc[0].mean_diff_lo,0);self.assertEqual(b.iloc[0].variance_ratio_hi,1)
        pd.testing.assert_frame_equal(a,bootstrap_moments(d,10,100,4)[0])

    def test_ols_covariance_identity(self):
        rng=np.random.default_rng(9);x=rng.normal(size=150);z=.8*x+rng.normal(size=150)*.2
        f=pd.DataFrame(dict(x=x,z=z),index=pd.bdate_range('2020-01-01',periods=150));y=pd.Series(.01+.3*x-.2*z+rng.normal(size=150)*.03,index=f.index)
        s,c,r=fit_attribution(y,f,3,60)
        beta=np.linalg.lstsq(np.column_stack([np.ones(150),x,z]),y,rcond=None)[0]
        np.testing.assert_allclose(c.beta,beta,atol=1e-12)
        self.assertLess(s['variance_identity_error'],1e-12);self.assertLess(s['mean_identity_error'],1e-12)
        self.assertNotAlmostEqual(s['residual_mse'],s['residual_variance'],places=8)

    def test_refitted_pairing(self):
        idx=pd.bdate_range('2020-01-01',periods=120);rng=np.random.default_rng(88)
        x=pd.DataFrame({'market':rng.normal(size=120)},index=idx);y=x.market*.5+rng.normal(size=120)
        s,p,c=joint_model_bootstrap(pd.DataFrame({'MTRN':y,'peer':y}),x,3,100,1)
        self.assertAlmostEqual(p.iloc[0].intercept_diff_lo,0);self.assertAlmostEqual(p.iloc[0].variance_ratio_hi,1)

    def test_information_available_next_session(self):
        sessions=pd.bdate_range('2019-01-01','2022-12-31')
        rows=[dict(start='2019-01-01',end='2019-12-31',val=10,filed='2020-02-07',form='10-K',accn='old'),
              dict(start='2019-01-01',end='2019-12-31',val=20,filed='2021-02-05',form='10-K',accn='recast')]
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'facts.json';path.write_text(json.dumps({'facts':{'us-gaap':{'Revenue':{'units':{'USD':rows}}}}}))
            f=PointInTimeFacts(path,sessions,'MTRN')
            self.assertIsNone(f.select('Revenue','2020-02-07'))
            self.assertEqual(f.value('Revenue','2020-02-10'),10)
            self.assertEqual(f.value('Revenue','2021-02-08'),20)
            rows.append(dict(start='2022-01-01',end='2022-03-31',val=6,filed='2022-04-29',form='10-Q',accn='new'))
            path.write_text(json.dumps({'facts':{'us-gaap':{'Revenue':{'units':{'USD':rows}}}}}))
            stale=PointInTimeFacts(path,sessions,'MTRN');self.assertTrue(np.isnan(stale.ttm('Revenue','2022-05-02')[0]))

    def test_event_estimation_excludes_news(self):
        idx=pd.bdate_range('2020-01-01',periods=300);m=pd.Series(np.sin(np.arange(300))*.01,index=idx)
        y=.001+1.2*m;y.iloc[269:272]+=.05
        e=event_car(y,m,idx[270]);self.assertAlmostEqual(e['car'],.15,places=10)
        self.assertEqual(e['n_estimation'],232);self.assertEqual(e['estimation_end'],str(idx[249].date()))
        self.assertEqual(e['window_end'],str(idx[271].date()))
        with self.assertRaisesRegex(ValueError,'Incomplete'):event_car(y,m,idx[-1])
        with self.assertRaisesRegex(ValueError,'Insufficient'):event_car(y,m,idx[100])
        self.assertEqual(session_for_release(idx,'2020-01-03',True),pd.Timestamp('2020-01-06'))

    def test_french_header_alignment_and_units(self):
        d=french('F-F_Research_Data_Factors_CSV.zip')
        self.assertTrue(d.MKT.notna().all());self.assertGreater(len(d),1000)
        self.assertLess(d.RF.abs().max(),.03);self.assertEqual(str(d.index[-1].date()),'2026-07-31')
        self.assertTrue(french('F-F_Momentum_Factor_CSV.zip').MOM.notna().all())

    def test_complete_week_and_partial_opening(self):
        calendar=pd.bdate_range('2026-04-20','2026-05-01')
        daily=pd.DataFrame({'return':[.01]*len(calendar)},index=calendar)
        full=complete_week_returns(daily,calendar,'2026-05-01')
        self.assertEqual(list(full.index),list(pd.to_datetime(['2026-04-24','2026-05-01'])))
        np.testing.assert_allclose(full['return'],1.01**5-1)
        partial=complete_week_returns(daily.loc['2026-04-24':],calendar,'2026-05-01')
        self.assertEqual(list(partial.index),[pd.Timestamp('2026-05-01')])

    def test_holiday_week_missing_price_and_partial_cutoff(self):
        # Good Friday is a market holiday; four observed sessions form a full week.
        calendar=pd.to_datetime(['2026-03-30','2026-03-31','2026-04-01','2026-04-02'])
        daily=pd.DataFrame({'a':[.01]*4,'b':[.02]*4},index=calendar)
        full=complete_week_returns(daily,calendar,'2026-04-03')
        self.assertEqual(len(full),1);self.assertAlmostEqual(full.iloc[0].a,1.01**4-1)
        self.assertTrue(complete_week_returns(daily.drop(calendar[1]),calendar,'2026-04-03').empty)
        self.assertTrue(complete_week_returns(daily,calendar,'2026-04-01').empty)
        missing=daily.copy();missing.loc[calendar[1],'b']=np.nan
        self.assertTrue(complete_week_returns(missing,calendar,'2026-04-03').empty)

    def test_price_cutoff_before_returns_and_event_windows(self):
        dates=pd.bdate_range('2025-01-01','2026-09-25')
        close=100+np.arange(len(dates))*.1
        frame=pd.DataFrame({'close':close,'adj_close':close},index=dates)
        frame.loc[frame.index>pd.Timestamp(CUTOFF),['close','adj_close']]=1e9
        with patch('market_analysis.pd.read_csv',return_value=frame):
            loaded=load_prices()
        self.assertTrue(all(str(d.index[-1].date())==CUTOFF for d in loaded.values()))
        returns=loaded['MTRN'].adj_close.pct_change().dropna()
        self.assertLess(returns.abs().max(),.01)
        with self.assertRaisesRegex(ValueError,'Incomplete event window'):
            event_car(returns,returns,pd.Timestamp(CUTOFF))
        with self.assertRaisesRegex(ValueError,'Event outside'):
            event_car(returns,returns,pd.Timestamp('2026-09-21'))

    def test_ttm_prior_vintage_metadata_and_cutoff_restatement(self):
        sessions=pd.bdate_range('2024-01-01','2026-09-25')
        rows=[dict(start='2025-01-01',end='2025-12-31',val=100,filed='2026-02-02',form='10-K',accn='annual'),
              dict(start='2025-01-01',end='2025-06-30',val=40,filed='2025-08-01',form='10-Q',accn='original'),
              dict(start='2025-01-01',end='2025-06-30',val=45,filed='2026-08-03',form='10-Q',accn='comparative'),
              dict(start='2026-01-01',end='2026-06-30',val=60,filed='2026-08-03',form='10-Q',accn='current'),
              dict(start='2025-01-01',end='2025-06-30',val=999,filed='2026-09-21',form='10-Q/A',accn='future')]
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'facts.json';path.write_text(json.dumps({'facts':{'us-gaap':{'Revenue':{'units':{'USD':rows}}}}}))
            f=PointInTimeFacts(path,sessions,'MTRN');value,end=f.ttm('Revenue',CUTOFF)
        self.assertEqual(value,115);self.assertEqual(end,'2026-06-30')
        prior=f.audit[-1];self.assertEqual(prior['accn'],'comparative')
        self.assertEqual(prior['first_filed_for_period'],'2025-08-01')
        self.assertEqual(prior['vintage_status'],'changed from earliest filed value')
        self.assertTrue(all(x['available']<=CUTOFF and x['unit']=='USD' for x in f.audit))

if __name__=='__main__':unittest.main(verbosity=2)
