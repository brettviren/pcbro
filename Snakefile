#!/usr/bin/env snakemake


# These names come from FP's dropbox folder names, but lower cased.
# Downloading their zip files is not done here as it is error prone
# due to Dropbox unreliability.  Provide them manually.
FPSAMPLES = ["dv-2000v", "dv-2000v-h2mm0", "dv-2000v-h2mm5"]

# The 50L DAQ run timestamps we want to process
TIMESTAMPS = [s for s in open("scripts/rawdata-2020-05-26.stamps").read().split('\n') if s.strip()]

workdir: os.environ.get("PCBRO_DATADIR", "/home/bv/work/pcbro")

# Make intermediate NPZ file from FP zip file
rule fpnpxfile:
    input: 
        "fp/{resp}-fixed.tgz"
    output:
        "fp/{resp}-fp.npz"
    shell:
        "wirecell-pcbro fpstrips-fp-npz {input} {output}"

# Make a PDF vis of FP data
rule fppdffile:
    input:
        "fp/{resp}-fp.npz"
    output:
        "fp/{resp}-fp.pdf"
    shell:
        "wirecell-pcbro fpstrips-draw-fp {input} {output}"

# Make intermediate NPZ file following WCT units/layout
rule wctnpzfile:
    input:
        "fp/{resp}-fp.npz"
    output:
        "fp/{resp}.npz"
    shell:
        "wirecell-pcbro fpstrips-wct-npz {input} {output}"

# Make WCT field response JSON file from FP zip file
rule wctjsonfile:
    input:
        "fp/{resp}-fixed.tgz"
    output:
        "{resp}.json.bz2"
    shell:
        "wirecell-pcbro convert-fpstrips {input} {output}"

# Make standard WCT field response plots
rule fieldplots:
    input:
        "{resp}.json.bz2"
    output:
        "fp/{resp}.png"
    shell:
        "wirecell-sigproc plot-response --region 0 --trange 0,120 --reflect {input} {output}"


# Run field response file preperation for all known samples
rule fieldprep:
    input:
        expand("{resp}.json.bz2", resp=FPSAMPLES) \
            + expand("fp/{resp}-fp.pdf", resp=FPSAMPLES)
            + expand("fp/{resp}.png", resp=FPSAMPLES)


# Decode raw 50L data into NPZ
rule decode:
    input:
        "Rawdata_05_26_2020/run01tri/WIB00step18_FEMB_B8_{timestamp}.bin"
    output:
        "proc/raw-{timestamp}.npz"
    shell:
        "wire-cell -A infile={input} -A outfile={output} -c cli-bin-npz.jsonnet"

# Run sigproc from raw 50L data
rule sigproc:
    input:
        data = "Rawdata_05_26_2020/run01tri/WIB00step18_FEMB_B8_{timestamp}.bin",
        resp = "{resp}.json.bz2"
    output:
        "proc/sig-{resp}-{timestamp}.npz"
    shell:
        "wire-cell -A resp={input.resp} -A infile={input.data} -A outfile={output} -c cli-bin-sp-npz.jsonnet"
    

rule activity:
    input:
        "proc/sig-{resp}-{timestamp}.npz"
    output:
        "proc/sig-active-{resp}-{timestamp}.npz"
    shell:
        "wirecell-pcbro activity -t 1000000 {input} {output}"

# Roll up everything
rule wctproc:
    input:
        expand("proc/raw-{timestamp}.npz", timestamp=TIMESTAMPS) \
            + expand("proc/sig-{resp}-{timestamp}.npz", resp=FPSAMPLES, timestamp=TIMESTAMPS) \
            + expand("proc/sig-active-{resp}-{timestamp}.npz", resp=FPSAMPLES, timestamp=TIMESTAMPS)
