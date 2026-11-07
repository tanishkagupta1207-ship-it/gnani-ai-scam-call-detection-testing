"""Accuracy report. Put recordings in test_audio/scam/ and test_audio/normal/,
then run: python evaluate.py   (writes results.csv, prints the summary)."""
import os, csv, glob
from gnani.stt import GnaniSTTClient
from detector import analyze

stt = GnaniSTTClient(api_key=os.environ["GNANI_API_KEY"])
rows = []
for expected in ("scam", "normal"):
    for p in sorted(glob.glob(f"test_audio/{expected}/*.*")):
        t = stt.transcribe(p, language_code="hi-IN")["transcript"]
        label = analyze(t)["label"]
        rows.append([os.path.basename(p), expected, label, t])
        print(expected, label, os.path.basename(p))

with open("results.csv", "w", newline="", encoding="utf-8-sig") as f:
    csv.writer(f).writerows([["file", "expected", "predicted", "transcript"]] + rows)

scam = [r for r in rows if r[1] == "scam"]; normal = [r for r in rows if r[1] == "normal"]
caught = sum(r[2] != "none" for r in scam); false_alarms = sum(r[2] != "none" for r in normal)
print(f"\nScam calls caught: {caught}/{len(scam)}")
print(f"False alarms on normal calls: {false_alarms}/{len(normal)}")
