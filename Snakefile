TIMESTAMPS = [s for s in open("scripts/rawdata-2020-05-26.stamps").read().split('\n') if s.strip()]

rule all:
  input:
    expand("data/raw-{sample}.npz", sample=TIMESTAMPS)+expand("data/sig-{sample}.npz", sample=TIMESTAMPS)


rule decode:
  input:
    "/home/bv/work/pcbro/Rawdata_05_26_2020/run01tri/WIB00step18_FEMB_B8_{sample}.bin"
  output:
    "data/raw-{sample}.npz"
  shell:
    "wire-cell -A infile={input} -A outfile={output} -c cfg/cli-bin-npz.jsonnet"


rule sigproc:
  input:
    "/home/bv/work/pcbro/Rawdata_05_26_2020/run01tri/WIB00step18_FEMB_B8_{sample}.bin"
  output:
    "data/sig-{sample}.npz"
  shell:
    "wire-cell -A resp=dv-2000v.json.bz2 -A infile={input} -A outfile={output} -c cfg/cli-bin-sp-npz.jsonnet"
    
