import os,re,tempfile,textwrap,csv,hashlib,subprocess,sys
src=open("edge_daq.py.g19").read().splitlines()
i=next(k for k,l in enumerate(src) if "# 7. Append to hot_backup.csv" in l)
# extract the real block: from the 'if CSV_RECORDING_ENABLED' line to the line before the next step comment / except end
j=i+1; blk=[]
while not src[j].lstrip().startswith("# 8."): blk.append(src[j]); j+=1
    # (stop at next numbered step)
block=textwrap.dedent("\n".join(blk))
print("gate line:",block.splitlines()[0])
def run(enabled,path):
    pk={"timestamp":1.0,"vibration":{"g_total":1,"rms_dyn":2,"kurtosis":3,"crest_factor":4,"peak_dyn":5},"temperature":{"temp_c":6,"slope_c_per_min":7},"acoustic":{"db_spl":8,"zcr":9},"fault_proba":None}
    g=dict(CSV_RECORDING_ENABLED=enabled,now_wall=100.0,last_csv_log=0.0,HISTORY_FILE=path,csv=csv,packet=pk,seq=1,state="Healthy",fault_label="x")
    exec(block,g); return g
d=tempfile.mkdtemp(); p=d+"/h.csv"; open(p,"w").write("a,b\n1,2\n"); h=lambda:hashlib.md5(open(p,"rb").read()).hexdigest()
h0=h(); st=os.stat(p); run(False,p); s2=os.stat(p)
assert h()==h0 and s2.st_mtime_ns==st.st_mtime_ns; print("OFF: file byte-identical and mtime unchanged: PASS")
run(True,p); assert h()!=h0 and open(p).read().count("\n")==3; print("ON (G12_CSV_RECORDING=1): appends: PASS")
assert 'os.environ.get("G12_CSV_RECORDING", "0") == "1"' in "\n".join(src); print("default is OFF: PASS")
# read-only existing file / missing file must not matter when off
run(False,"/nonexistent/x.csv"); print("OFF with unwritable path: no error: PASS")
