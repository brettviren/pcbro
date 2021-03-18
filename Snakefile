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
        "tmp/{resp}-fp.npz"
    shell:
        "wirecell-pcbro fpstrips-fp-npz {input} {output}"

# Make a PDF vis of FP data
rule fppdffile:
    input:
        "tmp/{resp}-fp.npz"
    output:
        "plots/{resp}-fp.pdf"
    shell:
        "wirecell-pcbro fpstrips-draw-fp {input} {output}"

# Make intermediate NPZ file following WCT units/layout
rule wctnpzfile:
    input:
        "tmp/{resp}-fp.npz"
    output:
        "tmp/{resp}.npz"
    shell:
        "wirecell-pcbro fpstrips-wct-npz {input} {output}"

# Make WCT field response JSON file from FP zip file
rule wctjsonfile:
    input:
        "fp/{resp}-fixed.tgz"
    output:
        "resp/{resp}.json.bz2"
    shell:
        "wirecell-pcbro convert-fpstrips {input} {output}"

# Make standard WCT field response plots
rule fieldplots:
    input:
        "resp/{resp}.json.bz2"
    output:
        "plots/{resp}.png"
    shell:
        "wirecell-sigproc plot-response --region 0 --trange 0,120 --reflect {input} {output}"


# Run field response file preperation for all known samples
rule fieldprep:
    input:
        expand("resp/{resp}.json.bz2", resp=FPSAMPLES) \
            + expand("plots/{resp}-fp.pdf", resp=FPSAMPLES)
            + expand("plots/{resp}.png", resp=FPSAMPLES)


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
        resp = "resp/{resp}.json.bz2"
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

rule evdplots_raw:
    input:
        "proc/raw-{timestamp}.npz"
    output:
        "plots/raw-{timestamp}-{trigger}.{plotext}"
    shell:
        "wirecell-pcbro evd2d -t {wildcards.trigger} --channels '0:64,64:128' \
        --title='Raw data from run {wildcards.timestamp} trigger {{trigger}}' \
        --color-unit='ADC from baseline' \
        --color-map=seismic \
        --color-range='-300,0,300' \
        --ticks '100:550' --tshift '-12' \
        --baseline-subtract=median \
        -o {output} {input}"

rule evdplots_sig:
    input:
        "proc/sig-{resp}-{timestamp}.npz"
    output:
        "plots/sig-{resp}-{timestamp}-{trigger}-{cmap}.{plotext}"
    shell:
        "wirecell-pcbro evd2d -t {wildcards.trigger} --channels '0:64,64:128' \
        --title='{wildcards.resp} signals from run {wildcards.timestamp} trigger {{trigger}}' \
        --color-map={wildcards.cmap} \
        --color-range='0,2500,20000' --mask-min=0 --ticks='0:450' \
        -T gauss0 \
        -o {output} {input}"


rule evdplots:
    input:
        expand("plots/raw-{timestamp}-{trigger}.{plotext}",
               timestamp=["159048405892"],
               trigger=["31"],
               plotext=["png","pdf"]) +
        expand("plots/sig-{resp}-{timestamp}-{trigger}-{cmap}.{plotext}",
               resp=FPSAMPLES,
               cmap=['cubehelix','gnuplot','seismic'],
               timestamp=["159048405892"],
               trigger=["31"],
               plotext=["png","pdf"])


