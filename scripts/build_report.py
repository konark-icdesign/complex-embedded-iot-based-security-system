"""Build a readable report strictly from the executed result files."""
from pathlib import Path
import csv,json,html,re,sys
from collections import Counter
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle,Image,PageBreak,KeepTogether
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet,ParagraphStyle
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from matplotlib.font_manager import findfont,FontProperties

ROOT=Path(__file__).resolve().parents[1];R=ROOT/'results'
OUT=ROOT/'output'/'pdf';OUT.mkdir(parents=True,exist_ok=True)
S=json.loads((R/'summary.json').read_text());REAL=json.loads((R/'real_audio_results.json').read_text())
ROWS=list(csv.DictReader((R/'scenario_results.csv').open()))
REPLAY=json.loads((R/'embedded_replay.json').read_text())
AGG=[]
for name in ['rain','engine','footsteps','glass_breaking','door_wood_knock','door_wood_creaks','thunderstorm','wind','clock_tick','coughing']:
    rows=[r for r in REAL['rows'] if r['category']==name]
    AGG.append((name,len(rows),sum(r['anomaly'] for r in rows),sum(r['synthetic_model_anomaly'] for r in rows)))

def markdown_report():
    m=S['monte_carlo'];p=S['primary']
    text=f'''# Simulation report - 17 September 2026

## Verdict

Proceed as a college ECE experiment. The simulation and embedded logic run, but the design is not ready for unattended security use. Keep the measured misses and false alarms visible. MATLAB execution and physical room validation remain outstanding.

## Actual execution

| Item | Result |
|---|---|
| Synthetic evaluation | {m['trials']} trials: 52 cases x 10 noise seeds |
| Intrusion trials detected | {m['detected']} / {m['intrusion_trials']} |
| Missed intrusion trials | {m['missed']} / {m['intrusion_trials']} |
| False alerts | {m['false_alerts']} / {m['nonintrusion_trials']} non-intrusion trials |
| Naive any-sensor false alerts | {m['naive_false_alerts']} / {m['nonintrusion_trials']} |
| Latency among detections | Median {m['median_latency']} s; maximum {m['max_latency']} s in idealized simulation |
| Synthetic non-intrusion duration | {m['nonintrusion_simulated_hours']} hours, fragmented 24-second trials |
| Real sound recordings | 40 clips: 6 train, 4 calibration, 30 evaluation from 25 original source IDs |
| Native regression suite | 13 Python regressions passed; original failures retained |
| Embedded host checks | Strict GCC warnings, ASan and UBSan passed; leak checking unavailable |
| Embedded cross-language replay | {REPLAY['input_ticks']} ticks, {REPLAY['mismatches']} mismatches |
| Arduino target | UNO R4 WiFi, official Renesas core 1.6.0; compile succeeded |
| Compiled firmware footprint | 53,724 bytes flash; 6,904 bytes global RAM |
| MATLAB | Source provided; NOT RUN |
| Hardware / HP throughput | NOT TESTED |
| Remote alert | Local simulated receiver only; no human contacted |

The repeated cases use the same event schedules and simplified sensor responses. Noise-seed repetition is not independent field validation. Do not advertise 84.2% real-world detection or 93.9% reliability from these counts. No room-level accuracy has been established.

## Unresolved system failures

| Case | Observed | Why |
|---|---|---|
| 31 Audio + PIR only | Missed intrusion; YELLOW | Below the deliberate corroboration requirement |
| 32 Audio + radar only | Missed intrusion; YELLOW | Same evidence tradeoff |
| 51 Silent far entrant outside camera, radar only | Missed intrusion; YELLOW | Insufficient observability |
| 38 Heated moving object | False RED | Camera and PIR can share one harmless cause |
| 42 Nearby outside activity | False RED | Poor placement lets outside activity affect audio, PIR and radar |

These five outcomes repeat across the ten seeds. We did not feed their ground-truth labels into the decision logic to force a pass. They require better boundary sensing, placement and room data, not cosmetic code changes.

## Real-audio challenge

Source: [ESC-50, official dataset](https://github.com/karolpiczak/ESC-50). Six rain/engine clips in fold 1 trained a separate proxy model; four fold-2 clips calibrated it. Thirty fold-5 clips evaluated both that model and the frozen synthetic model. No evaluation clip trained either model. Three clips per category are a small stress check, not a validated benchmark. The 30 clips come from 25 original source IDs.

The proxy treats either approved rain or engine background as normal. It deliberately tests a broader baseline than one real room; this is separate from the context-selected synthetic dry/rain models. The minimum-distance choice can hide suspicious sounds. Engine recordings are not recordings of your PC fan.

| Class | Tested | Proxy model flagged | Synthetic model flagged |
|---|---:|---:|---:|
'''
    for name,n,a,b in AGG:text+=f'| {name} | {n} | {a} | {b} |\n'
    text+='''
All six held-out background proxy clips were accepted by the broad model, but all three footsteps were missed. Their source titles describe wood, carpet, and dirt/rocks footsteps. The synthetic model flagged all 30 clips, including every held-out normal proxy. This is strong evidence that attractive synthetic plots do not establish transfer to a real microphone/room. Audio remains an anomaly trigger, not a validated footstep classifier.

## Reproduced mechanisms

- Clean global brightness increase: naive changed area 100%; compensated changed area 0%.
- Local 50x30 change in a 160x120 image: 7.8125% changed area remains after compensation.
- One 0.35 m echo among roughly 3 m echoes: rejected by the causal five-sample median.
- Sustained 1.2 m target: accepted after median and persistence; typical synthetic delay 0.4 s.
- Camera obstruction: central RED can still use audio and physical evidence; obstruction alone stays a health/YELLOW condition.
- PC/USB failure with independently powered board and all three physical inputs: local fallback activates in the model.
- Internet outage, process restart and lost acknowledgment: persistent queue yields one unique local receiver alert after retry. This is not proof of external provider exactly-once delivery.

## Actual debug history

1. Regression `test_green_visits_yellow_before_red` failed: simultaneous qualifying evidence moved directly from GREEN to RED. The transition was fixed; the first failing log is retained.
2. Code inspection found that the evidence ring copied the next 100 ms audio chunk. It was changed to retain only samples already completed at the current timestamp. No claim is made that this inspection was an instrumented failing test.
3. Regression `test_persistent_camera_fault_does_not_merge_separate_incidents` failed: a persistent fault held RED indefinitely and suppressed a later distinct event. Activity-clear timing was separated from health timing; a cleared incident now returns to YELLOW when faults remain.
4. The first sanitizer invocation could not start LeakSanitizer under the hosted process tracer. The rerun disabled leak detection only; address and undefined-behavior checks remained enabled. The board build also contains warnings from the official vendor core. They were retained, not disguised as a warning-free core build.

## Correlation-window sensitivity

With isolated audio, PIR and radar event impulses, a 2-second window missed a 3.2-second delayed third input. Four seconds accepted it. Eight seconds accepted a constructed set of unrelated inputs 7 seconds apart. See `impulse_timing_sensitivity.csv`. Four seconds is a documented prototype compromise, not universal calibration. The companion sustained-sensor sweep shows little difference because sustained signals overlap.

## All primary scenarios

| Scenario | Ground truth | Outcome | First alert delay (s) |
|---|---|---|---:|
'''
    for r in ROWS:
        text+=f"| {r['name']} | {'intrusion' if r['intrusion']=='True' else 'non-intrusion'} | {r['outcome']} | {r['latency'] or '-'} |\n"
    text+='''
## Outstanding work and files

The ZIP contains Python and MATLAB source, the UNO R4 sketch, exact selected audio files with attribution, baseline fixtures, complete CSV/JSON traces, original failure logs, final test logs, a sample synthetic WAV/MP4 and guides. `docs/hp_setup.md` gives software choices for the 8 GB HP; `docs/dsp_maths.md` explains the mathematics; `docs/learning_and_validation.md` lists practical learning and field-validation steps.

Still required: literal MATLAB execution; continuous physical acquisition and clock mapping; actual microphone/camera/sensor measurements; HP workload benchmarking; real notification transport; power/disk-failure handling; and frozen-model evaluation on held-out room recordings. This project is published on GitHub; no external security alert was sent.

Official references for software and board facts are in `docs/sources.md`. Simulation facts are derived from `results/summary.json`, `scenario_results.csv`, `real_audio_results.csv`, `embedded_replay.json` and the compile/test logs.
'''
    (ROOT/'docs'/'experiment_report.md').write_text(text)

pdfmetrics.registerFont(TTFont('BodyDoc',findfont(FontProperties(family='DejaVu Sans'))))
pdfmetrics.registerFont(TTFont('BodyDocBold',findfont(FontProperties(family='DejaVu Sans',weight='bold'))))
pdfmetrics.registerFontFamily('BodyDoc',normal='BodyDoc',bold='BodyDocBold',italic='BodyDoc',boldItalic='BodyDocBold')
STYLES=getSampleStyleSheet()
STYLES.add(ParagraphStyle(name='Body2',fontName='BodyDoc',fontSize=10.5,leading=15,spaceAfter=9,textColor=colors.HexColor('#263844')))
STYLES.add(ParagraphStyle(name='Small2',fontName='BodyDoc',fontSize=8.7,leading=12,spaceAfter=7,textColor=colors.HexColor('#4d626e')))
STYLES.add(ParagraphStyle(name='Title2',fontName='BodyDocBold',fontSize=28,leading=32,spaceAfter=16,textColor=colors.HexColor('#173b4b')))
STYLES.add(ParagraphStyle(name='Head2',fontName='BodyDocBold',fontSize=18,leading=22,spaceAfter=12,textColor=colors.HexColor('#173b4b')))
STYLES.add(ParagraphStyle(name='Sub2',fontName='BodyDocBold',fontSize=12,leading=16,spaceBefore=8,spaceAfter=7,textColor=colors.HexColor('#276d76')))
W=A4[0]-88
story=[]
def p(text,style='Body2'):return Paragraph(text,STYLES[style])
def add(text,style='Body2'):story.append(p(text,style))
def title(n,text):add(f'{n:02d} / {text}','Head2')
def table(rows,widths=None,small=False):
    data=[[p(html.escape(str(c)),'Small2') for c in row] for row in rows]
    t=Table(data,colWidths=widths or [W/len(rows[0])]*len(rows[0]),repeatRows=1,hAlign='LEFT')
    t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#dcebed')),
          ('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),7),('RIGHTPADDING',(0,0),(-1,-1),7),
          ('TOPPADDING',(0,0),(-1,-1),6 if not small else 3),('BOTTOMPADDING',(0,0),(-1,-1),4 if not small else 1),
          ('LINEBELOW',(0,0),(-1,0),.7,colors.HexColor('#73a1a7')),
          ('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#f4f7f7')])]))
    story.append(t);story.append(Spacer(1,10))
def fig(name,width=W):
    from PIL import Image as PILImage
    img=R/name;size=PILImage.open(img).size
    story.append(Image(str(img),width=width,height=width*size[1]/size[0]));story.append(Spacer(1,10))
def page():story.append(PageBreak())

def pdf_report():
    add('ECE / SIMULATION STUDY / 16 SEPTEMBER 2026','Small2')
    add('Multimodal<br/>night security','Title2')
    add('Executed simulation, measured failures and a practical HP setup','Sub2')
    add('<b>Verdict:</b> worthwhile as a college DSP and embedded experiment. This version is not ready for unattended security use. The failed cases are part of the engineering result.')
    table([['Completed','Still unverified'],['520 synthetic trials; 40 real sound clips; compiled UNO R4 sketch; strict native checks and replay.','Literal MATLAB execution; physical sensors; real-time HP performance; live notification delivery.']],[W/2,W/2])
    fig('scenario_outcomes.png')
    add('The chart shows one run of each of the 52 cases. Ten noise seeds repeated the same pattern. The full count is 160/190 intrusion trials detected and 20 false alerts across 330 non-intrusion trials.','Small2')
    add('No real-world accuracy is claimed. The synthetic scenes use drawn shapes and simplified sensor responses. No message to a security team was sent.','Small2')
    page()
    title(2,'What the system actually does')
    add('One room, one microphone and one camera feed the PC. An Arduino polls PIR, ultrasonic range and a radar presence output. USB serial keeps the local link independent of Internet availability.')
    table([['Stage','Implementation'],['Audio','16 kHz; 128 ms FFT frames; gain-normalized spectral/temporal features; frozen dry and rain baselines.'],['Vision','Global brightness gain/offset correction, local image change and visibility checks. No person identification.'],['Physical inputs','10 Hz sampling; three-sample persistence; five-sample range median; near-field threshold 1.8 m.'],['Fusion','4-second evidence history, explicit corroboration rules and an inspectable point score.'],['Output','GREEN / YELLOW / RED; RED queues an alert. A local SQLite receiver demonstrates retry de-duplication.']],[W*.22,W*.78])
    add('Fusion rules','Sub2')
    add('Points: audio 1.5; vision 3; PIR 2; radar 2; near range 2. RED needs at least 5 points and either vision plus a physical channel, all three physical channels, or audio plus two physical channels. These points are not probabilities.')
    add('A black frame creates a visibility fault, not a claim that somebody covered the camera. Faults create YELLOW and contribute no danger points. A broken camera cannot count as a second independent vision sensor.')
    add('The important correction','Sub2')
    add('Different sensors are not automatically independent witnesses. A warm moving object can affect vision and PIR. Nearby outside activity can affect sound, PIR and radar. Their agreement can still create a false alert.')
    page()
    title(3,'Synthetic results and retained failures')
    m=S['monte_carlo']
    table([['Measure','Executed result'],['Evaluation','52 scenarios x 10 noise seeds = 520 trials'],['Intrusion trials',f"{m['detected']} detected; {m['missed']} missed / {m['intrusion_trials']}"],['Non-intrusion trials',f"{m['false_alerts']} false alerts / {m['nonintrusion_trials']}"],['Naive any-input rule',f"{m['naive_false_alerts']} false alerts / {m['nonintrusion_trials']}"],['Detection latency','0.25 s median; 3.2 s maximum among detected synthetic cases'],['Simulated non-intrusion time','2.2 hours, fragmented into 24-second scripted trials']],[W*.36,W*.64])
    add('Five cases prevent a clean security claim','Sub2')
    table([['Case','Measured failure / implication'],['Audio + PIR only','YELLOW; intrusion missed under the conservative rule.'],['Audio + radar only','YELLOW; same false-alarm versus missed-detection tradeoff.'],['Silent far entrant; radar only','YELLOW; insufficient sensing coverage.'],['Warm moving object','False RED from shared visual and PIR evidence.'],['Nearby outside activity','False RED from sensors responding across the intended boundary.']],[W*.37,W*.63])
    add('These failures repeat across seeds. Ground-truth labels are used by the evaluator, never to force the detector to pass. A repeated noise-seed test does not sample real intruder behavior, room acoustics or sensor installation variability.','Small2')
    page()
    title(4,'Real recordings expose the audio limit')
    add('Forty selected ESC-50 clips were downloaded with source URLs, hashes and attribution. Six fold-1 rain/engine clips trained a separate background proxy, four fold-2 clips calibrated it, and thirty fold-5 clips evaluated it. Evaluation clips were not used for training or tuning.')
    table([['Sound category','Test clips','Proxy flagged','Synthetic flagged']]+[[n.replace('_',' '),total,a,b] for n,total,a,b in AGG],[W*.46,W*.16,W*.19,W*.19],True)
    add('<b>All three real footstep clips were missed by the broad proxy model.</b> Their source titles describe wood, carpet and dirt/rocks footsteps. It also accepted all six held-out rain/engine background clips. The frozen synthetic model flagged all 30 clips, including those backgrounds.')
    add('This illustrates two failures: a narrow synthetic model sees ordinary real audio as novel; a broad model can absorb suspicious sounds as normal. The real proxy accepts the closest of rain/engine models and is separate from the context-selected synthetic experiment.')
    add('The 30 evaluation clips came from 25 original source IDs. This tiny sample is a domain-transfer challenge, not room-level validation. Audio should remain an investigation trigger until calibration and held-out testing with the intended microphone establish its limits.','Small2')
    add('Source: <link href="https://github.com/karolpiczak/ESC-50" color="#247c97">ESC-50 official dataset</link>. CC BY-NC terms and clip attribution are included.','Small2')
    page()
    title(5,'DSP, camera and timing evidence')
    fig('lighting_test.png')
    add('In the constructed image test, a global +60 brightness change produced 100% naive changed area and 0% corrected area. A 50x30 local change remained visible as 7.8125% of a 160x120 frame. These are exact synthetic checks, not field performance.','Small2')
    fig('ultrasonic_test.png')
    add('The 0.35 m isolated echo was rejected. A sustained 1.2 m target became valid near evidence after median filtering and persistence. A timeout clears old range evidence.','Small2')
    add('Timing tradeoff','Sub2')
    add('For isolated channel impulses, 2 seconds missed a 3.2-second delayed confirmation; 4 seconds accepted it. An 8-second window also combined a constructed set of unrelated inputs. Four seconds is a prototype compromise, not universal calibration.','Small2')
    page()
    title(6,'Camera obstruction example')
    fig('camera_blocked_timeline.png',W*.96)
    add('The shaded period is the scripted event. Audio and physical channels support RED even when camera visibility is lost. After activity clears, the state returns to YELLOW if the camera fault persists. That permits a later separate incident to generate a new alert.','Small2')
    add('All plotted media and sensor inputs on this page are synthetic. The supplied WAV/MP4 and timestamps are a separate normal walk-in example captured from the bounded evidence buffer.','Small2')
    page()
    title(7,'Firmware, outages and debug record')
    table([['Verification','Observed result'],['UNO R4 WiFi target','Official Renesas UNO core 1.6.0 compiled successfully.'],['Static footprint','53,724 bytes flash; 6,904 bytes global RAM. Stack and electrical behavior unmeasured.'],['Native C++ checks','-Wall -Wextra -Werror -Wpedantic; AddressSanitizer and UndefinedBehaviorSanitizer.'],['Cross-language replay','12,480 ticks; zero mismatches against the reference physical filters/fallback.'],['Python regressions','13 passed. Two original failing state tests are preserved.'],['Notification fault test','One queued incident; restart and lost acknowledgment; one unique local receiver alert after retry.']],[W*.33,W*.67])
    add('Faults fixed in development','Sub2')
    add('1. Simultaneous evidence skipped YELLOW. Fixed the transition; retained the failing test log.<br/>2. Inspection found a future 100 ms audio chunk in the evidence buffer. Changed capture to completed samples only.<br/>3. A persistent camera fault held RED and merged later incidents. Separated activity-clear timing from health timing; retained the failing regression.')
    add('Verification limits','Sub2')
    add('LeakSanitizer could not run under the hosted process tracer. Leak checking was disabled only for that limitation; address/undefined-behavior checks ran. The target build retains warnings in vendor core code. Our native code compiled with warnings treated as errors.')
    add('Arduino fallback requires its own surviving power supply and all three physical inputs. USB-only power can disappear with the PC. GPIO radar output does not provide module freshness diagnostics. Edge RAM state does not survive a board power cycle. No real network provider or security recipient was tested.','Small2')
    page()
    title(8,'Software for your 8 GB HP')
    add('Assumption: HP t640, Ryzen R1505G, 8 GB RAM, NVMe SSD. Your latest message says t460; verify the label or msinfo32. The attached brief and earlier specification say t640.')
    table([['Software','Use now'],['Python 3.12 + NumPy / SciPy / Matplotlib','Runs the executed reference. A virtual environment and commands are included.'],['MATLAB if already licensed','Independent numerical implementation. Base MATLAB suffices for the offline code; literal execution still pending.'],['Arduino IDE 2 + UNO R4 Boards','Compile, upload and inspect serial. Recorded core: 1.6.0.'],['Optional FFmpeg','Exports the synthetic video clip.'],['Defer initially','MQTT, Simulink, large neural models and high-resolution multi-camera processing.']],[W*.42,W*.58])
    add('Start with mono 16 kHz audio, 320x240 grayscale camera processing at 5 fps and 10 Hz sensor telemetry. Run one numerical environment at a time. This is a target configuration, not a measured HP throughput result.')
    add('MathWorks lists 8 GB minimum and 16 GB recommended for R2026a, with Windows 10 22H2 supported. An SSD is recommended. Your stated RAM meets the minimum; do not infer that large video workloads will be smooth. <link href="https://www.mathworks.com/support/requirements/matlab-system-requirements.html" color="#247c97">Official requirements</link>.','Small2')
    add('Ten seconds of uncompressed 320x240 grayscale at 5 fps is about 3.84 MB; 16-bit mono audio at 16 kHz adds about 0.32 MB. Runtime and decoder overhead are additional. A bounded design does not need many gigabytes of raw history.','Small2')
    add('First commands','Sub2')
    add('<font name="Courier">python -m pip install -r requirements.txt<br/>python run_simulation.py --seeds 1</font>')
    add('Then inspect the false-alarm cases, read the maths guide and run MATLAB. Buy no additional hardware merely to improve a simulated result. Measure the first bench before deciding on upgrades.','Small2')
    page()
    title(9,'Full case register: 1-26')
    register(ROWS[:26])
    page()
    title(10,'Full case register: 27-52')
    register(ROWS[26:])
    page()
    title(11,'What makes this defensible')
    add('The strongest presentation is reproducible: source code, data provenance, fixed seeds, measured failures, saved logs and a clear boundary between simulated and physical results. You should be able to explain every decision you present.')
    table([['Explain or demonstrate','Where to start'],['Calculate 128 ms frames, 64 ms hop and 7.8125 Hz bins','docs/dsp_maths.md'],['Show gain invariance and why clipping breaks it','src/dsp.py and gain regression'],['Explain the warmed-object false alarm','Case 38 trace; explicit fusion rules'],['Trace a timeout and millis wraparound','firmware/night_security/core.h; native tests'],['Show the two original failing tests and fixes','results/first_regression_run.txt and second_regression_failure.txt'],['Show a result that proves the model is limited','Real audio: 0/3 footstep clips flagged'],['Run MATLAB and retain its own log','matlab/run_full_simulation.m'],['Plan real room validation without leakage','docs/learning_and_validation.md']],[W*.53,W*.47])
    add('Next decision','Sub2')
    add('Build a small bench only after reviewing these limits. Prioritize sensor placement at the restricted boundary and actual room recordings. A door contact may be useful for a single-door room, but it must be tested and cannot prove authorization. An ordinary webcam needs suitable light; true night vision needs appropriate hardware.')
    add('Remaining work: continuous real audio/video/serial acquisition, device clock mapping, HP performance measurement, disk/retention handling, actual alert transport and held-out room tests. The package is a completed simulation study, not a finished deployed service.','Small2')
    add('References','Sub2')
    for name,url in [('MathWorks system requirements','https://www.mathworks.com/support/requirements/matlab-system-requirements.html'),('Arduino UNO R4 WiFi','https://docs.arduino.cc/hardware/uno-r4-wifi'),('Arduino IDE download','https://www.arduino.cc/en/software'),('HP t640 QuickSpecs','https://h20195.www2.hp.com/v2/GetDocument.aspx?docname=c06392258'),('ESC-50 dataset and license','https://github.com/karolpiczak/ESC-50')]:
        add(f'<link href="{html.escape(url,quote=True)}" color="#247c97">{html.escape(name)}</link>','Small2')
    document=SimpleDocTemplate(str(OUT/'Night_Security_Simulation_Report.pdf'),pagesize=A4,leftMargin=44,rightMargin=44,topMargin=46,bottomMargin=44,title='Multimodal night security - simulation report',author='ECE simulation study')
    def footer(canvas,doc):
        canvas.setStrokeColor(colors.HexColor('#c6d9dc'));canvas.line(44,32,A4[0]-44,32)
        canvas.setFillColor(colors.HexColor('#627983'));canvas.setFont('BodyDoc',7)
        canvas.drawString(44,20,'NIGHT SECURITY / SIMULATION STUDY / HARDWARE UNVERIFIED')
        canvas.drawRightString(A4[0]-44,20,str(doc.page))
    document.build(story,onFirstPage=footer,onLaterPages=footer)

def register(rows):
    data=[['Scenario','Result','Delay s']]
    for r in rows:
        name=r['name'].replace('_',' ')
        outcome={'NO_DANGER':'No danger','DETECTED':'Detected','MISSED_INTRUSION':'MISSED','FALSE_ALERT':'FALSE ALERT'}[r['outcome']]
        data.append([name,outcome,r['latency'] or '-'])
    table(data,[W*.62,W*.24,W*.14],True)
    add('Ground truth is intrusion for the detected/missed rows; it is non-intrusion for the other rows. Cases 21, 22 and 49 include a scripted intrusion during a connection/processor fault. Faults alone need not stay GREEN.','Small2')

if __name__=='__main__':
    markdown_report();pdf_report();print(OUT/'Night_Security_Simulation_Report.pdf')
