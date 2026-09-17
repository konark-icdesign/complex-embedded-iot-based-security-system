import unittest,tempfile,json
from pathlib import Path
import numpy as np
from src.dsp import features,background,train_synthetic,Baseline
from src.fusion import Fusion,Sensors,Outbox,PacketGate
from src.vision import room,compensate,Camera

class Regression(unittest.TestCase):
    def test_missing_download_is_reported_as_not_run(self):
        from src.real_audio import evaluate
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'fixtures'/'esc50';p.mkdir(parents=True)
            (p/'manifest.json').write_text(json.dumps([{'filename':'missing.wav','status':'downloaded'}]))
            result=evaluate(Path(d),{})
            self.assertEqual(result['status'],'NOT_RUN_INCOMPLETE_DATA')
            self.assertEqual(result['missing_files'],['missing.wav'])

    def test_invalid_audio_frame_cannot_inherit_anomaly(self):
        model=Baseline(np.zeros(9),np.ones(9),3.5)
        f={'x':np.full((3,9),10.),'valid':np.array([True,True,False])}
        _,flag=model.detect(f)
        self.assertFalse(flag[2])

    def test_green_visits_yellow_before_red(self):
        f=Fusion(); e=dict(A=True,P=True,M=True)
        self.assertEqual(f.update(1.,e)[0],1)
        self.assertEqual(f.update(1.1,e)[0],2)

    def test_stale_evidence_does_not_accumulate(self):
        f=Fusion()
        f.update(0.,dict(A=True))
        f.update(5.,dict(P=True))
        f.update(10.,dict(M=True))
        self.assertNotEqual(f.state,2)

    def test_gain_shape_invariance(self):
        x=background(2.,123)
        a=features(x)['x']; b=features(3*x)['x']
        np.testing.assert_allclose(a,b,rtol=1e-10,atol=1e-10)

    def test_global_light_and_local_change(self):
        x=room(); corrected,_,_=compensate(x,x+60)
        self.assertLess(np.mean(np.abs(corrected)>12),.001)
        y=x.copy();y[30:80,40:70]+=60
        corrected,_,_=compensate(x,y)
        self.assertAlmostEqual(np.mean(np.abs(corrected)>12),1500/19200,places=4)

    def test_saturated_camera_not_motion(self):
        c=Camera();c.update(0,room().astype(np.uint8))
        v=c.update(.2,np.full((120,160),255,dtype=np.uint8))
        self.assertTrue(v['health']);self.assertFalse(v['motion'])

    def test_median_glitch_and_timeout(self):
        s=Sensors()
        for i in range(20):self.assertFalse(s.update(False,False,.35 if i==9 else 3.)[2])
        for _ in range(12):result=s.update(False,False,1.2)
        self.assertTrue(result[2])
        self.assertFalse(s.update(False,False,float('nan'))[2])

    def test_durable_retry_lost_ack(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'outbox.db';o=Outbox(p);o.enqueue(dict(id='persistent-id',t=8.))
            o.pump(False);self.assertEqual(o.count(),0);o.close()
            o=Outbox(p);o.pump(True,lose_ack=True);o.close()
            o=Outbox(p);o.pump(True);o.pump(True)
            self.assertEqual(o.count(),1);self.assertEqual(o.pending(),0);o.close()

    def test_packet_freshness(self):
        p=PacketGate()
        self.assertTrue(p.accept(0,1.,1.1));self.assertFalse(p.accept(0,1.,1.2))
        self.assertFalse(p.accept(1,1.,4.));self.assertFalse(p.accept(1,4.,3.))
        self.assertTrue(p.accept(2,4.,4.1))

    def test_old_packet_cannot_refresh_physical_evidence(self):
        f=Fusion();f.update(1.,dict(A=True,P=True,M=True))
        f.update(10.,dict(P=True,M=True),captured=dict(P=1.,M=1.))
        f.update(10.1,dict(A=True))
        self.assertNotEqual(f.state,2)

    def test_acquisition_timestamps_allow_bounded_delay(self):
        f=Fusion();f.update(8.2,dict(A=True),captured=dict(A=8.))
        f.update(8.7,dict(P=True),captured=dict(P=8.5))
        state,_,_,_=f.update(9.2,dict(M=True),captured=dict(M=9.))
        self.assertEqual(state,2)

    def test_persistent_camera_fault_does_not_merge_separate_incidents(self):
        f=Fusion();e=dict(P=True,M=True,U=True)
        f.update(1.,e,True);f.update(1.1,e,True)
        f.update(10.,{},True)
        self.assertEqual(f.state,1)
        f.update(12.,e,True)
        self.assertEqual(len(f.alerts),2)

if __name__=='__main__':unittest.main()
