import os
import re
import sys
import csv
import queue
import shutil
import threading
import subprocess
from datetime import datetime
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

try:
    from rdkit import Chem
except Exception:
    Chem = None

try:
    from meeko import MoleculePreparation, PDBQTWriterLegacy
except Exception:
    MoleculePreparation = None
    PDBQTWriterLegacy = None

APP_TITLE = "MultiDock1.0 - Ligand Preparation & Molecular Docking"
AUTHOR = "Nguyen Duc Tri Thuc"
AFFILIATION = "Faculty of Pharmacy, Ton Duc Thang University"
CREATE_NO_WINDOW = 0x08000000 if os.name == "nt" else 0

def resource_path(relative_path):
    base_path = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)

class VinaGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.configure(bg="white")
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure(".", background="white")
        style.configure("TFrame", background="white")
        style.configure("TLabel", background="white", foreground="#0B2D5C")
        style.configure("TLabelframe", background="white")
        style.configure("TLabelframe.Label", background="white", foreground="#0B2D5C",
                        font=("Segoe UI", 9, "bold"))
        style.configure("TCheckbutton", background="white", foreground="#1F2937")
        style.configure("TButton", padding=(8, 5))
        style.configure("Treeview", background="white", fieldbackground="white", foreground="#1F2937")
        style.configure("Treeview.Heading", background="#F4F7FB", foreground="#0B2D5C",
                        font=("Segoe UI", 9, "bold"))
        style.configure("TEntry", fieldbackground="white", foreground="#111827")
        style.configure("Horizontal.TProgressbar", background="#168BD2", troughcolor="#F1F5F9")

        self.title(APP_TITLE)
        try:
            if os.name == "nt":
                self.iconbitmap(resource_path("MultiDock1.0.ico"))
        except Exception:
            pass
        self.geometry("1120x880")
        self.minsize(1000, 780)

        # Docking state
        self.proc = None
        self.stop_requested = False
        self.events = queue.Queue()
        self.receptor = tk.StringVar()
        self.ligdir = tk.StringVar()
        self.cx = tk.StringVar(value="-13.988")
        self.cy = tk.StringVar(value="-43.906")
        self.cz = tk.StringVar(value="27.108")
        self.sx = tk.StringVar(value="50")
        self.sy = tk.StringVar(value="50")
        self.sz = tk.StringVar(value="60")
        self.exhaust = tk.StringVar(value="200")
        self.energy = tk.StringVar(value="7")
        self.num_modes = tk.StringVar(value="9")
        self.cpu = tk.StringVar(value="0")
        self.skip_existing = tk.BooleanVar(value=True)
        self.status = tk.StringVar(value="Ready")
        self.current = tk.StringVar(value="-")
        self.progress_text = tk.StringVar(value="0 / 0")

        # Ligand preparation state
        self.prep_input = tk.StringVar()
        self.prep_output = tk.StringVar()
        self.prep_status = tk.StringVar(value="Ready")
        self.prep_current = tk.StringVar(value="-")
        self.prep_progress_text = tk.StringVar(value="0 / 0")
        self.prep_stop_requested = False
        self.prep_proc = None
        self.prep_events = queue.Queue()

        self._build()
        self.logbox.insert("end", f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] MultiDock1.0 is ready.\n")
        self.prep_logbox.insert("end", f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Ligand Preparation is ready.\n")
        self.after(100, self._poll_events)
        self.after(100, self._poll_prep_events)
        self.protocol("WM_DELETE_WINDOW", self._close)

    def _header(self):
        header = ttk.Frame(self)
        header.pack(fill="x", padx=12, pady=(8, 4))
        header.columnconfigure(1, weight=1)
        try:
            self.logo_image = tk.PhotoImage(file=resource_path("multidock_logo.png"))
            ttk.Label(header, image=self.logo_image).grid(row=0, column=0, rowspan=3, sticky="nw", padx=(0,18))
        except Exception:
            ttk.Label(header, text="MultiDock1.0", font=("Segoe UI",16,"bold")).grid(row=0,column=0,rowspan=3,sticky="nw",padx=(0,18))
        c = ttk.Frame(header); c.grid(row=0,column=1,rowspan=3,sticky="n")
        ttk.Label(c,text="MultiDock1.0",font=("Segoe UI",26,"bold")).pack()
        ttk.Label(c,text="Ligand Preparation & Molecular Docking",font=("Segoe UI",12,"bold")).pack(pady=(2,0))
        ttk.Label(c,text="Simple - Fast - Reliable",font=("Segoe UI",10,"italic")).pack(pady=(2,0))
        a=ttk.Frame(header); a.grid(row=0,column=2,rowspan=3,sticky="ne")
        ttk.Label(a,text=AUTHOR,font=("Segoe UI",11,"bold")).pack(anchor="e")
        ttk.Label(a,text=AFFILIATION,font=("Segoe UI",9)).pack(anchor="e")
        ttk.Separator(a,orient="horizontal").pack(fill="x",pady=(6,4))
        ttk.Label(a,text="For a healthier tomorrow",font=("Segoe UI",9,"italic")).pack(anchor="e")

    def _build(self):
        self._header()
        self.tabs = ttk.Notebook(self)
        self.tabs.pack(fill="both", expand=True, padx=12, pady=(6,12))
        self.prep_tab = ttk.Frame(self.tabs)
        self.dock_tab = ttk.Frame(self.tabs)
        self.tabs.add(self.prep_tab, text="  Ligand Preparation  ")
        self.tabs.add(self.dock_tab, text="  Molecular Docking  ")
        self._build_prep_tab()
        self._build_dock_tab()

    def _build_prep_tab(self):
        pad={"padx":8,"pady":5}
        top=ttk.LabelFrame(self.prep_tab,text="SDF → PDBQT")
        top.pack(fill="x",padx=10,pady=(10,6))
        ttk.Label(top,text="Input ligand folder").grid(row=0,column=0,sticky="w",**pad)
        ttk.Entry(top,textvariable=self.prep_input).grid(row=0,column=1,sticky="ew",**pad)
        ttk.Button(top,text="Browse...",command=self.pick_prep_input).grid(row=0,column=2,**pad)
        ttk.Label(top,text="Input format").grid(row=1,column=0,sticky="w",**pad)
        ttk.Label(top,text="SDF (.sdf)",font=("Segoe UI",9,"bold")).grid(row=1,column=1,sticky="w",**pad)
        ttk.Label(top,text="Output PDBQT folder").grid(row=2,column=0,sticky="w",**pad)
        ttk.Entry(top,textvariable=self.prep_output).grid(row=2,column=1,sticky="ew",**pad)
        ttk.Button(top,text="Browse...",command=self.pick_prep_output).grid(row=2,column=2,**pad)
        top.columnconfigure(1,weight=1)

        note=ttk.LabelFrame(self.prep_tab,text="Preparation protocol")
        note.pack(fill="x",padx=10,pady=6)
        ttk.Label(note,text="RDKit input validation → add missing explicit H → 3D coordinate check → Meeko Python API (Gasteiger) → PDBQT syntax validation",
                  wraplength=1000).pack(anchor="w",padx=8,pady=(7,2))
        ttk.Label(note,text="Input is restricted to SDF to preserve ligand bond-order information consistently.",
                  wraplength=1000).pack(anchor="w",padx=8,pady=(0,7))

        ctr=ttk.Frame(self.prep_tab); ctr.pack(fill="x",padx=10,pady=6)
        self.prep_start_btn=ttk.Button(ctr,text="START PREPARATION",command=self.start_preparation)
        self.prep_start_btn.pack(side="left")
        self.prep_stop_btn=ttk.Button(ctr,text="STOP",command=self.stop_preparation,state="disabled")
        self.prep_stop_btn.pack(side="left",padx=10)
        ttk.Button(ctr,text="Open output folder",command=self.open_prep_output).pack(side="right")

        prog=ttk.LabelFrame(self.prep_tab,text="Current process"); prog.pack(fill="x",padx=10,pady=6)
        ttk.Label(prog,text="Ligand:").grid(row=0,column=0,sticky="w",**pad)
        ttk.Label(prog,textvariable=self.prep_current).grid(row=0,column=1,sticky="w",**pad)
        ttk.Label(prog,textvariable=self.prep_progress_text).grid(row=0,column=2,sticky="e",**pad)
        self.prep_bar=ttk.Progressbar(prog,maximum=100); self.prep_bar.grid(row=1,column=0,columnspan=3,sticky="ew",**pad)
        ttk.Label(prog,textvariable=self.prep_status).grid(row=2,column=0,columnspan=3,sticky="w",**pad)
        prog.columnconfigure(1,weight=1)

        body=ttk.Panedwindow(self.prep_tab,orient="vertical"); body.pack(fill="both",expand=True,padx=10,pady=(6,10))
        lf=ttk.LabelFrame(body,text="Ligand preparation log")
        self.prep_logbox=tk.Text(lf,height=12,wrap="none",bg="white",fg="#111827",insertbackground="#111827",
                                 relief="flat",highlightthickness=1,highlightbackground="#D9E2EC")
        sy=ttk.Scrollbar(lf,orient="vertical",command=self.prep_logbox.yview)
        self.prep_logbox.configure(yscrollcommand=sy.set); self.prep_logbox.pack(side="left",fill="both",expand=True); sy.pack(side="right",fill="y")
        body.add(lf,weight=3)

        rf=ttk.LabelFrame(body,text="Preparation summary")
        cols=("ligand","fmt","h","tors","status")
        self.prep_tree=ttk.Treeview(rf,columns=cols,show="headings",height=8)
        for c,t,w in [("ligand","Ligand",230),("fmt","Input",75),("h","H added",90),("tors","TORSDOF",90),("status","Status",140)]:
            self.prep_tree.heading(c,text=t); self.prep_tree.column(c,width=w,anchor="center" if c!="ligand" else "w")
        self.prep_tree.pack(fill="both",expand=True); body.add(rf,weight=2)

    def _build_dock_tab(self):
        pad={"padx":8,"pady":5}
        top=ttk.LabelFrame(self.dock_tab,text="Input files"); top.pack(fill="x",padx=10,pady=(10,6))
        ttk.Label(top,text="Receptor (.pdbqt)").grid(row=0,column=0,sticky="w",**pad)
        ttk.Entry(top,textvariable=self.receptor).grid(row=0,column=1,sticky="ew",**pad)
        ttk.Button(top,text="Browse...",command=self.pick_receptor).grid(row=0,column=2,**pad)
        ttk.Label(top,text="Ligand folder").grid(row=1,column=0,sticky="w",**pad)
        ttk.Entry(top,textvariable=self.ligdir).grid(row=1,column=1,sticky="ew",**pad)
        ttk.Button(top,text="Browse...",command=self.pick_ligdir).grid(row=1,column=2,**pad)
        top.columnconfigure(1,weight=1)

        params=ttk.LabelFrame(self.dock_tab,text="Docking parameters"); params.pack(fill="x",padx=10,pady=6)
        labels=[("center_x",self.cx),("center_y",self.cy),("center_z",self.cz),("size_x",self.sx),("size_y",self.sy),
                ("size_z",self.sz),("exhaustiveness",self.exhaust),("energy_range",self.energy),("num_modes",self.num_modes),("CPU (0 = Vina auto)",self.cpu)]
        for i,(lab,var) in enumerate(labels):
            r,c=divmod(i,5); b=c*2
            ttk.Label(params,text=lab).grid(row=r,column=b,sticky="w",padx=(8,2),pady=6)
            ttk.Entry(params,textvariable=var,width=11).grid(row=r,column=b+1,sticky="w",padx=(2,10),pady=6)

        ctr=ttk.Frame(self.dock_tab); ctr.pack(fill="x",padx=10,pady=6)
        ttk.Checkbutton(ctr,text="Skip completed outputs",variable=self.skip_existing).pack(side="left")
        self.start_btn=ttk.Button(ctr,text="START DOCKING",command=self.start); self.start_btn.pack(side="left",padx=10)
        self.stop_btn=ttk.Button(ctr,text="STOP",command=self.stop,state="disabled"); self.stop_btn.pack(side="left")
        ttk.Button(ctr,text="Open results folder",command=self.open_results).pack(side="right")

        prog=ttk.LabelFrame(self.dock_tab,text="Current process"); prog.pack(fill="x",padx=10,pady=6)
        ttk.Label(prog,text="Ligand:").grid(row=0,column=0,sticky="w",**pad)
        ttk.Label(prog,textvariable=self.current).grid(row=0,column=1,sticky="w",**pad)
        ttk.Label(prog,textvariable=self.progress_text).grid(row=0,column=2,sticky="e",**pad)
        self.bar=ttk.Progressbar(prog,maximum=100); self.bar.grid(row=1,column=0,columnspan=3,sticky="ew",**pad)
        ttk.Label(prog,textvariable=self.status).grid(row=2,column=0,columnspan=3,sticky="w",**pad); prog.columnconfigure(1,weight=1)

        body=ttk.Panedwindow(self.dock_tab,orient="vertical"); body.pack(fill="both",expand=True,padx=10,pady=(6,10))
        lf=ttk.LabelFrame(body,text="Vina output")
        self.logbox=tk.Text(lf,height=12,wrap="none",bg="white",fg="#111827",insertbackground="#111827",relief="flat",highlightthickness=1,highlightbackground="#D9E2EC")
        sy=ttk.Scrollbar(lf,orient="vertical",command=self.logbox.yview); self.logbox.configure(yscrollcommand=sy.set)
        self.logbox.pack(side="left",fill="both",expand=True); sy.pack(side="right",fill="y"); body.add(lf,weight=3)
        rf=ttk.LabelFrame(body,text="Ranking — Vina score (kcal/mol)")
        self.tree=ttk.Treeview(rf,columns=("rank","ligand","score"),show="headings",height=8)
        for c,t,w in [("rank","Rank",70),("ligand","Ligand",240),("score","Vina score (kcal/mol)",180)]:
            self.tree.heading(c,text=t); self.tree.column(c,width=w,anchor="center" if c!="ligand" else "w")
        self.tree.pack(fill="both",expand=True); body.add(rf,weight=2)

    # ---------- Ligand Preparation ----------
    def pick_prep_input(self):
        p=filedialog.askdirectory()
        if p:
            self.prep_input.set(p)
            if not self.prep_output.get():
                self.prep_output.set(os.path.join(os.path.dirname(p),"pdbqt"))

    def pick_prep_output(self):
        p=filedialog.askdirectory()
        if p: self.prep_output.set(p)

    @staticmethod
    def _hcount(mol):
        return sum(1 for a in mol.GetAtoms() if a.GetAtomicNum()==1)

    def _read_ligand(self, src):
        ext=os.path.splitext(src)[1].lower()
        if ext != ".sdf":
            raise ValueError(f"Unsupported input format: {ext}. MultiDock ligand preparation accepts SDF only.")
        mols=[m for m in Chem.SDMolSupplier(src,removeHs=False,sanitize=True) if m is not None]
        if len(mols)!=1:
            raise ValueError(f"Expected exactly 1 valid molecule in SDF; found {len(mols)}")
        return mols[0], "SDF"

    def _prepare_input_mol(self, src):
        if Chem is None:
            raise RuntimeError("RDKit is not available in this build")
        m,fmt=self._read_ligand(src)
        hb=self._hcount(m)
        # AddHs fills hydrogens implied by RDKit valence even when some explicit H already exist.
        m=Chem.AddHs(m,addCoords=True)
        ha=self._hcount(m); added=ha>hb
        if ha==0: raise ValueError("No explicit hydrogens after RDKit AddHs")
        if m.GetNumConformers()==0: raise ValueError("No conformer/coordinates")
        conf=m.GetConformer()
        if not conf.Is3D():
            raise ValueError("Coordinates are not marked as 3D; generate a 3D ligand before docking")
        return m,fmt,hb,ha,added

    @staticmethod
    def _meeko_to_pdbqt(mol):
        if MoleculePreparation is None or PDBQTWriterLegacy is None:
            raise RuntimeError("Meeko Python API is not available in this build")
        prep=MoleculePreparation(charge_model="gasteiger", add_index_map=True)
        setups=prep.prepare(mol)
        if not setups:
            raise RuntimeError("Meeko returned no molecule setup")
        if len(setups)!=1:
            raise RuntimeError(f"Meeko returned {len(setups)} setups; expected 1")
        # Current Meeko returns (pdbqt_string, is_ok, error_msg).
        result=PDBQTWriterLegacy.write_string(setups[0], add_index_map=True)
        if isinstance(result, tuple):
            pdbqt=result[0]; ok=result[1] if len(result)>1 else True; err=result[2] if len(result)>2 else ""
        else:
            pdbqt=result; ok=True; err=""
        if not ok:
            raise RuntimeError("Meeko writer failed: " + str(err))
        if not pdbqt or not str(pdbqt).strip():
            raise RuntimeError("Meeko generated an empty PDBQT")
        return str(pdbqt)

    @staticmethod
    def _validate_pdbqt(path):
        errs=[]; warns=[]; atoms=br=ebr=root=eroot=0; tors=None
        with open(path,encoding="utf-8",errors="replace") as f: lines=f.read().splitlines()
        if not lines: return False,None,["Empty PDBQT"],[]
        for n,line in enumerate(lines,1):
            if line.startswith("ROOT"): root+=1
            elif line.startswith("ENDROOT"): eroot+=1
            elif line.startswith("BRANCH"): br+=1
            elif line.startswith("ENDBRANCH"): ebr+=1
            elif line.startswith("TORSDOF"):
                try: tors=int(line.split()[1])
                except Exception: errs.append(f"Line {n}: invalid TORSDOF")
            if line[:6].strip() in ("ATOM","HETATM"):
                atoms+=1
                try: float(line[30:38]); float(line[38:46]); float(line[46:54])
                except Exception: errs.append(f"Line {n}: invalid XYZ")
                fields=line.split()
                if len(fields)<12: errs.append(f"Line {n}: incomplete atom record")
                else:
                    try: float(fields[-2])
                    except Exception: errs.append(f"Line {n}: invalid partial charge")
                    if not fields[-1]: errs.append(f"Line {n}: missing AutoDock atom type")
        if atoms==0: errs.append("No ATOM/HETATM records")
        if root!=1 or eroot!=1: errs.append(f"ROOT/ENDROOT={root}/{eroot}")
        if br!=ebr: errs.append(f"BRANCH/ENDBRANCH={br}/{ebr}")
        if tors is None: errs.append("TORSDOF not found")
        elif tors<0: errs.append("Negative TORSDOF")
        if tors is not None and tors!=br: warns.append(f"TORSDOF={tors}, BRANCH count={br}")
        return not errs,tors,errs,warns

    def start_preparation(self):
        inp=self.prep_input.get().strip(); out=self.prep_output.get().strip()
        if not os.path.isdir(inp):
            messagebox.showerror("Cannot start","Input ligand folder does not exist."); return
        files=sorted([os.path.join(inp,x) for x in os.listdir(inp)
                      if os.path.isfile(os.path.join(inp,x)) and x.lower().endswith(".sdf")])
        if not files:
            messagebox.showerror("Cannot start","No SDF ligand files (*.sdf) were found."); return
        if not out:
            out=os.path.join(os.path.dirname(inp),"pdbqt"); self.prep_output.set(out)
        os.makedirs(out,exist_ok=True)
        if Chem is None:
            messagebox.showerror("Cannot start","RDKit is not available in this MultiDock build."); return
        if MoleculePreparation is None or PDBQTWriterLegacy is None:
            messagebox.showerror("Cannot start","Meeko Python API is not available in this MultiDock build."); return
        for item in self.prep_tree.get_children(): self.prep_tree.delete(item)
        self.prep_logbox.delete("1.0","end")
        self.prep_stop_requested=False; self.prep_start_btn.config(state="disabled"); self.prep_stop_btn.config(state="normal")
        self.prep_status.set("Preparing ligands...")
        threading.Thread(target=self._prep_worker,args=(files,out),daemon=True).start()

    def _prep_worker(self,files,outdir):
        failed_dir=os.path.join(outdir,"failed"); os.makedirs(failed_dir,exist_ok=True)
        rows=[]; failures=[]; ready=0
        for i,src in enumerate(files,1):
            if self.prep_stop_requested: break
            base=os.path.basename(src); name=os.path.splitext(base)[0]; ext=os.path.splitext(base)[1].lower().lstrip(".").upper()
            out=os.path.join(outdir,name+".pdbqt")
            self.prep_events.put(("progress",i,len(files),base))
            row={"Ligand":base,"Input_format":ext,"Input_valid":"NO","Explicit_H_before":"","Explicit_H_after":"","H_added":"",
                 "Meeko":"NOT_RUN","PDBQT_valid":"NO","TORSDOF":"","Status":"FAILED","Notes":""}
            stage="RDKit input validation"
            try:
                mol,fmt,hb,ha,added=self._prepare_input_mol(src)
                row.update(Input_format=fmt,Input_valid="YES",Explicit_H_before=hb,Explicit_H_after=ha,H_added="YES" if added else "NO")
                note=""
                if fmt=="PDB": note="PDB warning: bond-order information may be incomplete. "
                self.prep_events.put(("line",f"[{i}/{len(files)}] {base}: {fmt} OK | explicit H {hb}->{ha}" + (" | H added\n" if added else "\n")))
                stage="Meeko preparation"
                pdbqt=self._meeko_to_pdbqt(mol)
                with open(out,"w",encoding="utf-8",newline="\n") as f: f.write(pdbqt)
                row["Meeko"]="OK"
                stage="PDBQT validation"
                valid,tors,errs,warns=self._validate_pdbqt(out); row["TORSDOF"]="" if tors is None else tors
                if valid:
                    row["PDBQT_valid"]="YES"; row["Status"]="READY"; row["Notes"]=note+"; ".join(warns); ready+=1
                    self.prep_events.put(("line",f"[READY] {name}.pdbqt | TORSDOF={tors}\n\n"))
                else:
                    row["Notes"]=note+"; ".join(errs+warns); failures.append(f"{base}\tStage: {stage}\t{row['Notes']}")
                    try: shutil.copy2(src,os.path.join(failed_dir,base))
                    except Exception: pass
                    try: os.remove(out)
                    except Exception: pass
            except Exception as e:
                row["Notes"]=f"Stage: {stage} | {str(e).replace(chr(10),' | ')}"
                failures.append(f"{base}\t{row['Notes']}")
                try: shutil.copy2(src,os.path.join(failed_dir,base))
                except Exception: pass
                try:
                    if os.path.exists(out): os.remove(out)
                except Exception: pass
                self.prep_events.put(("line",f"[FAILED] {base} | {row['Notes']}\n\n"))
            rows.append(row); self.prep_events.put(("row",row))
        summary=os.path.join(outdir,"ligand_preparation_summary.csv")
        with open(summary,"w",newline="",encoding="utf-8-sig") as f:
            fields=["Ligand","Input_format","Input_valid","Explicit_H_before","Explicit_H_after","H_added","Meeko","PDBQT_valid","TORSDOF","Status","Notes"]
            w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(rows)
        with open(os.path.join(outdir,"failed_ligands.txt"),"w",encoding="utf-8") as f:
            f.write("\n".join(failures) if failures else "No failed ligands.\n")
        self.prep_events.put(("finished",ready,len(rows)-ready,self.prep_stop_requested,outdir))

    def _poll_prep_events(self):
        try:
            while True:
                ev=self.prep_events.get_nowait(); kind=ev[0]
                if kind=="line":
                    self.prep_logbox.insert("end",ev[1]); self.prep_logbox.see("end")
                elif kind=="progress":
                    _,i,n,name=ev; self.prep_current.set(name); self.prep_progress_text.set(f"{i} / {n}"); self.prep_bar["value"]=(i/n)*100
                elif kind=="row":
                    r=ev[1]; self.prep_tree.insert("","end",values=(r["Ligand"],r["Input_format"],r["H_added"],r["TORSDOF"],r["Status"]))
                elif kind=="finished":
                    _,ok,fail,stopped,outdir=ev
                    self.prep_start_btn.config(state="normal"); self.prep_stop_btn.config(state="disabled")
                    self.prep_status.set(f"{'Stopped' if stopped else 'Completed'} — READY: {ok}, FAILED: {fail}")
                    if not stopped: self.prep_bar["value"]=100
                    if ok>0:
                        self.ligdir.set(outdir)
        except queue.Empty: pass
        self.after(100,self._poll_prep_events)

    def stop_preparation(self):
        self.prep_stop_requested=True; self.prep_status.set("Stopping...")
        p=self.prep_proc
        if p and p.poll() is None:
            try: p.terminate()
            except Exception: pass

    def open_prep_output(self):
        p=self.prep_output.get()
        if p and os.path.isdir(p):
            if os.name=="nt": os.startfile(p)
            else: subprocess.Popen(["xdg-open",p])

    def pick_receptor(self):
        p = filedialog.askopenfilename(filetypes=[("PDBQT", "*.pdbqt"), ("All files", "*.*")])
        if p:
            self.receptor.set(p)

    def pick_ligdir(self):
        p = filedialog.askdirectory()
        if p:
            self.ligdir.set(p)

    def _vina_path(self):
        vina_name = "vina.exe" if os.name == "nt" else "vina"

        # When running as a PyInstaller executable, bundled files are
        # extracted to sys._MEIPASS.
        if getattr(sys, "frozen", False):
            bundle_dir = getattr(
                sys,
                "_MEIPASS",
                os.path.dirname(sys.executable)
            )

            bundled_vina = os.path.join(bundle_dir, vina_name)
            if os.path.isfile(bundled_vina):
                return bundled_vina

            # Fallback: allow an external vina.exe beside the GUI EXE.
            external_vina = os.path.join(
                os.path.dirname(sys.executable),
                vina_name
            )
            if os.path.isfile(external_vina):
                return external_vina

        else:
            # When running directly from VinaBatchDocking.py.
            script_dir = os.path.dirname(os.path.abspath(__file__))
            local_vina = os.path.join(script_dir, vina_name)
            if os.path.isfile(local_vina):
                return local_vina

        # Final fallback: look for Vina in PATH.
        return shutil.which("vina")

    def validate(self):
        if not os.path.isfile(self.receptor.get()):
            raise ValueError("Receptor PDBQT does not exist.")
        if not os.path.isdir(self.ligdir.get()):
            raise ValueError("Ligand folder does not exist.")
        ligs = sorted(
            os.path.join(self.ligdir.get(), x)
            for x in os.listdir(self.ligdir.get())
            if x.lower().endswith(".pdbqt")
        )
        if not ligs:
            raise ValueError("No .pdbqt ligand files were found.")
        vina = self._vina_path()
        if not vina:
            raise ValueError("vina.exe was not found. Put vina.exe beside this program.")
        # Validate numeric values.
        for v in (self.cx, self.cy, self.cz, self.sx, self.sy, self.sz):
            float(v.get())
        for v in (self.exhaust, self.energy, self.num_modes, self.cpu):
            int(v.get())
        return vina, ligs

    def start(self):
        try:
            vina, ligs = self.validate()
        except Exception as e:
            messagebox.showerror("Cannot start", str(e))
            return

        project = os.path.dirname(os.path.abspath(self.receptor.get()))
        self.logdir = os.path.join(project, "log")
        self.outdir = os.path.join(project, "output")
        os.makedirs(self.logdir, exist_ok=True)
        os.makedirs(self.outdir, exist_ok=True)
        self.ranking_file = os.path.join(project, "docking_ranking.csv")
        self.summary_file = os.path.join(project, "docking_summary.csv")
        self.failed_file = os.path.join(project, "failed_ligands.txt")
        self.params_file = os.path.join(project, "docking_parameters.txt")

        self._write_parameters(vina, len(ligs))
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.logbox.delete("1.0", "end")
        self.stop_requested = False
        self.start_btn.config(state="disabled")
        self.stop_btn.config(state="normal")
        self.status.set("Docking...")
        threading.Thread(target=self._worker, args=(vina, ligs), daemon=True).start()

    def _write_parameters(self, vina, n):
        with open(self.params_file, "w", encoding="utf-8") as f:
            f.write("Software: MultiDock1.0\n")
            f.write(f"Author: {AUTHOR}\n")
            f.write(f"Affiliation: {AFFILIATION}\n")
            f.write(f"Date: {datetime.now().isoformat(sep=' ', timespec='seconds')}\n")
            f.write(f"Receptor: {self.receptor.get()}\n")
            f.write(f"Ligand folder: {self.ligdir.get()}\n")
            f.write(f"Vina executable: {vina}\n")
            f.write(f"center_x: {self.cx.get()}\ncenter_y: {self.cy.get()}\ncenter_z: {self.cz.get()}\n")
            f.write(f"size_x: {self.sx.get()}\nsize_y: {self.sy.get()}\nsize_z: {self.sz.get()}\n")
            f.write(f"exhaustiveness: {self.exhaust.get()}\n")
            f.write(f"energy_range: {self.energy.get()}\n")
            f.write(f"num_modes: {self.num_modes.get()}\n")
            f.write(f"cpu: {self.cpu.get()} (0 = not passed to Vina)\n")
            f.write(f"Total ligands: {n}\n")

    def _worker(self, vina, ligs):
        results, failed = [], []
        total = len(ligs)

        for idx, lig in enumerate(ligs, 1):
            if self.stop_requested:
                break
            name = os.path.splitext(os.path.basename(lig))[0]
            outfile = os.path.join(self.outdir, name + "_out.pdbqt")
            logfile = os.path.join(self.logdir, name + "_log.txt")
            self.events.put(("progress", idx, total, name))

            if self.skip_existing.get() and os.path.isfile(outfile) and os.path.isfile(logfile):
                score = self._parse_score(logfile)
                if score is not None:
                    results.append((name, score))
                    self.events.put(("line", f"[SKIP] {name}: {score:.3f} kcal/mol\n"))
                    continue

            cmd = [
                vina, "--receptor", self.receptor.get(), "--ligand", lig,
                "--center_x", self.cx.get(), "--center_y", self.cy.get(), "--center_z", self.cz.get(),
                "--size_x", self.sx.get(), "--size_y", self.sy.get(), "--size_z", self.sz.get(),
                "--exhaustiveness", self.exhaust.get(),
                "--energy_range", self.energy.get(),
                "--num_modes", self.num_modes.get(),
                "--out", outfile,
            ]
            if int(self.cpu.get()) > 0:
                cmd += ["--cpu", self.cpu.get()]

            try:
                with open(logfile, "w", encoding="utf-8", errors="replace") as lf:
                    self.proc = subprocess.Popen(
                        cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                        text=True, bufsize=1,
                        creationflags=CREATE_NO_WINDOW
                    )
                    for line in self.proc.stdout:
                        lf.write(line)
                        lf.flush()
                        self.events.put(("line", line))
                    rc = self.proc.wait()
                    self.proc = None

                score = self._parse_score(logfile)
                if rc == 0 and score is not None:
                    results.append((name, score))
                    self.events.put(("line", f"[DONE] {name}: {score:.3f} kcal/mol\n\n"))
                else:
                    failed.append(name)
                    self.events.put(("line", f"[FAILED] {name} (exit={rc})\n\n"))
            except Exception as e:
                self.proc = None
                failed.append(name)
                self.events.put(("line", f"[ERROR] {name}: {e}\n\n"))

            self._save_results(results, failed)

        self._save_results(results, failed)
        self.events.put(("finished", results, failed, self.stop_requested))

    @staticmethod
    def _parse_score(logfile):
        # Vina mode-1 row, e.g. "   1       -11.3      0.000      0.000"
        pat = re.compile(r"^\s*1\s+(-?\d+(?:\.\d+)?)\s+")
        try:
            with open(logfile, encoding="utf-8", errors="replace") as f:
                for line in f:
                    m = pat.match(line)
                    if m:
                        return float(m.group(1))
        except OSError:
            pass
        return None

    def _save_results(self, results, failed):
        ranked = sorted(results, key=lambda x: x[1])
        with open(self.summary_file, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f)
            w.writerow(["Ligand", "Best_Vina_Score_kcal_mol"])
            w.writerows(results)
        with open(self.ranking_file, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f)
            w.writerow(["Rank", "Ligand", "Best_Vina_Score_kcal_mol"])
            for i, (name, score) in enumerate(ranked, 1):
                w.writerow([i, name, score])
        with open(self.failed_file, "w", encoding="utf-8") as f:
            for x in failed:
                f.write(x + "\n")
        self.events.put(("ranking", ranked))

    def _poll_events(self):
        try:
            while True:
                ev = self.events.get_nowait()
                kind = ev[0]
                if kind == "line":
                    self.logbox.insert("end", ev[1])
                    self.logbox.see("end")
                elif kind == "progress":
                    _, i, n, name = ev
                    self.current.set(name)
                    self.progress_text.set(f"{i} / {n}")
                    self.bar["value"] = (i / n) * 100
                elif kind == "ranking":
                    for item in self.tree.get_children():
                        self.tree.delete(item)
                    for i, (name, score) in enumerate(ev[1], 1):
                        self.tree.insert("", "end", values=(i, name, f"{score:.3f}"))
                elif kind == "finished":
                    _, results, failed, stopped = ev
                    self.start_btn.config(state="normal")
                    self.stop_btn.config(state="disabled")
                    self.status.set(
                        f"{'Stopped' if stopped else 'Completed'} — success: {len(results)}, failed: {len(failed)}"
                    )
                    if not stopped:
                        self.bar["value"] = 100
        except queue.Empty:
            pass
        self.after(100, self._poll_events)

    def stop(self):
        self.stop_requested = True
        self.status.set("Stopping...")
        p = self.proc
        if p and p.poll() is None:
            try:
                p.terminate()
            except Exception:
                pass

    def open_results(self):
        receptor = self.receptor.get()
        folder = os.path.dirname(os.path.abspath(receptor)) if receptor else os.getcwd()
        if os.path.isdir(folder):
            if os.name == "nt":
                os.startfile(folder)
            else:
                subprocess.Popen(["xdg-open", folder])

    def _close(self):
        running_dock = self.proc and self.proc.poll() is None
        running_prep = self.prep_proc and self.prep_proc.poll() is None
        if running_dock or running_prep:
            if not messagebox.askyesno("Exit", "A process is running. Stop and exit?"):
                return
            if running_dock: self.stop()
            if running_prep: self.stop_preparation()
        self.destroy()


if __name__ == "__main__":
    VinaGUI().mainloop()
