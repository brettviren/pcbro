#!/usr/bin/env snakemake


# These names come from FP's dropbox folder names, but lower cased.
# Downloading their zip files is not done here as it is error prone
# due to Dropbox unreliability.  Provide them manually.
FPSAMPLES = ["dv-2000v", "dv-2000v-h2mm0", "dv-2000v-h2mm5"]

# The 50L DAQ run timestamps we want to process
TIMESTAMPS = [s for s in open("scripts/rawdata-2020-05-26.stamps").read().split('\n') if s.strip()]

workdir: os.environ.get("PCBRO_DATADIR", "/home/bv/work/pcbro/fp")

# Make intermediate NPZ file from FP zip file
rule fpnpxfile:
    input: 
        "{sample}-fixed.tgz"
    output:
        "{sample}-fp.npz"
    shell:
        "wirecell-pcbro fpstrips-fp-npz {input} {output}"

# Make a PDF vis of FP data
rule fppdffile:
    input:
        "{sample}-fp.npz"
    output:
        "{sample}-fp.pdf"
    shell:
        "wirecell-pcbro fpstrips-draw-fp {input} {output}"

# Make intermediate NPZ file following WCT units/layout
rule wctnpzfile:
    input:
        "{sample}-fp.npz"
    output:
        "{sample}.npz"
    shell:
        "wirecell-pcbro fpstrips-wct-npz {input} {output}"

# Make WCT field response JSON file from FP zip file
rule wctjsonfile:
    input:
        "{sample}-fixed.tgz"
    output:
        "{sample}.json.bz2"
    shell:
        "wirecell-pcbro convert-fpstrips {input} {output}"

# Make standard WCT field response plots
rule fieldplots:
    input:
        "{sample}.json.bz2"
    output:
        "{sample}.png"
    shell:
        "wirecell-sigproc plot-response --region 0 --trange 0,120 --reflect {input} {output}"


# Run field response file preperation for all known samples
rule fieldprep:
    input:
        expand("{sample}.json.bz2", sample=FPSAMPLES) \
            + expand("{sample}-fp.pdf", sample=FPSAMPLES)
            + expand("{sample}.png", sample=FPSAMPLES)

rule wctproc:
    input:
        expand("data/raw-{sample}.npz", sample=TIMESTAMPS) \
            + expand("data/sig-{sample}.npz", sample=TIMESTAMPS) \
            + expand("data/sig-active-{sample}.npz", sample=TIMESTAMPS)


rule decode:
    params:
        datadir = os.environ.get("PCBRO_DATADIR", "/home/bv/work/pcbro")
    input:
        "{params.datdir}/Rawdata_05_26_2020/run01tri/WIB00step18_FEMB_B8_{sample}.bin"
    output:
        "data/raw-{sample}.npz"
    shell:
        "wire-cell -A infile={input} -A outfile={output} -c cfg/cli-bin-npz.jsonnet"


rule sigproc:
    params:
        datadir = os.environ.get("PCBRO_DATADIR", "/home/bv/work/pcbro")
    input:
        "{params.datadir}/Rawdata_05_26_2020/run01tri/WIB00step18_FEMB_B8_{sample}.bin"
    output:
        "data/sig-{sample}.npz"
    shell:
        "wire-cell -A resp=dv-2000v.json.bz2 -A infile={input} -A outfile={output} -c cfg/cli-bin-sp-npz.jsonnet"
    

rule activity:
    input:
        "data/sig-{sample}.npz"
    output:
        "data/sig-active-{sample}.npz"
    shell:
        "wirecell-pcbro activity -t 1000000 {input} {output}"
