#!/usr/bin/env snakemake

## This converts FP response data to WCT form (.json.bz2), runs WCT
## sim and sigproc jobs on sim and data using the FR and it makes
## various diagnostic plots.  See scripts/get-fpdata.sh for how to
## properly populate input tar files holding FP responses.  For raw
## data processing you will need to provide .bin files according to
## rawdata_bin_p below and provide a list of timestamps via the
## "stamps" config parameter.

# use this like:
# snakemake -jall \
#   --config stamps=$(pwd)/scripts/rawdata-2020-05-26.stamps \
#   --config binpat="Rawdata_05_26_2020/run01tri/WIB00step18_FEMB_B8_{timestamp}.bin" \
#   --directory /home/bv/work/pcbro
# see "scripts/snakeit.sh" 

# In the work directory, these raw data files are needed.
# "Rawdata_05_26_2020/run01tri/WIB00step18_FEMB_B8_{timestamp}.bin"
rawdata_bin_p = config["binpat"]


# These names must match what get-fpdata.sh provide.
# We must enact different patterns depending on the sample.
FP2SAMPLES = ["dv-2000v", "dv-2000v-h2mm0", "dv-2000v-h2mm5"]
FP3SAMPLES = ["reference3views"]
FPSAMPLES = FP2SAMPLES + FP3SAMPLES

# The 50L DAQ run timestamps we want to process
#TIMESTAMPS = [s for s in open("scripts/rawdata-2020-05-26.stamps").read().split('\n') if s.strip()]
TIMESTAMPS = [s for s in open(config["stamps"]).read().split('\n') if s.strip()]


# We make Numpy .npz files with minimal processing beyond reformatting
# in order to erase the differing formats and superficial differences
# in content between the various raw FP samples.  Once we have
# fpresp/*.npz then each "resp" looks the same to the rest of the
# rules.  They culminate in:
fpresp_p = "fpresp/{resp}.npz"

# Make intermediate 2-view NPZ file from FP zip file.
rule fp2npzfile:
    input: 
        "fp/{resp}-fixed.tgz"
    output:
        fpresp_p
    shell:
        "wirecell-pcbro fpstrips-fp-npz {input} {output}"
# Make intermediate 3-view NPZ file from FP zip file.
rule fp3npzfile:
    input:
        col = "fp/{resp}/collection.tar",
        ind1 = "fp/{resp}/induction1.tar",
        ind2 = "fp/{resp}/induction2.tar"
    output:
        fpresp_p
    shell: """
    wirecell-pcbro fpstrips-trio-npz \
      --col {input.col} --ind1 {input.ind1} --ind2 {input.ind2} \
      {output}
    """
# Make a PDF vis of FP data
rule fppdffile:
    input:
        fpresp_p
    output:
        "plots/fpresp/{resp}.pdf"
    shell:
        "wirecell-pcbro fpstrips-draw-fp {input} {output}"

# Make intermediate NPZ file following WCT units/layout
rule wctnpzfile:
    input:
        fpresp_p
    output:
        "wctresp/{resp}.npz"
    shell:
        "wirecell-pcbro fpstrips-wct-npz {input} {output}"

# Make WCT field response JSON file from FP npz file
rule wctjsonfile:
    input:
        fpresp_p
    output:
        "resp/{resp}.json.bz2"
    shell:
        "wirecell-pcbro convert-fpstrips {input} {output}"

# Make standard WCT field response plots
rule fieldplots:
    input:
        rules.wctjsonfile.output
    output:
        "plots/wctresp/{resp}.png"
    shell:
        "wirecell-sigproc plot-response --region 0 --trange 0,120 --reflect {input} {output}"


# Run field response file preperation for all known samples
rule all_fields:
    input:
        expand(rules.wctjsonfile.output, resp=FPSAMPLES),
        expand(rules.fieldplots.output, resp=FPSAMPLES),
        expand(rules.fppdffile.output, resp=FPSAMPLES)

# Decode raw 50L data into NPZ
rule decode:
    input:
        rawdata_bin_p
    output:
        "proc/raw/raw-{timestamp}.npz"
    shell: """
    wire-cell -A infile={input} -A outfile={output} \
      -c cli-bin-npz.jsonnet
    """

# Run sigproc from raw 50L data
rule sigproc:
    input:
        data = rawdata_bin_p,
        resp = rules.wctjsonfile.output
    output:
        "proc/sig/sig-{resp}-{timestamp}.npz"
    shell: """
    wire-cell -A resps_file={input.resp} \
      -A infile={input.data} -A outfile={output} \
      -c cli-bin-sp-npz.jsonnet
    """
    

rule activity:
    input:
        rules.sigproc.output
    output:
        "proc/act/sig-active-{resp}-{timestamp}.npz"
    shell:
        "wirecell-pcbro activity -t 1000000 {input} {output}"

# Roll up everything
rule wctproc:
    input:
        expand(rules.decode.output, timestamp=TIMESTAMPS),
        expand(rules.sigproc.output, resp=FPSAMPLES, timestamp=TIMESTAMPS),
        expand(rules.activity.output, resp=FPSAMPLES, timestamp=TIMESTAMPS)

rule evdplots_raw:
    input:
        rules.decode.output
    output:
        "plots/raw/raw-{timestamp}-{trigger}.{plotext}"
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
        rules.sigproc.output
    output:
        "plots/sig/sig-{resp}-{timestamp}-{trigger}-{cmap}.{plotext}"
    shell:
        "wirecell-pcbro evd2d -t {wildcards.trigger} --channels '0:64,64:128' \
        --title='{wildcards.resp} signals from run {wildcards.timestamp} trigger {{trigger}}' \
        --color-map={wildcards.cmap} \
        --color-range='0,2500,20000' --mask-min=0 --ticks='0:450' \
        -T gauss0 \
        -o {output} {input}"


rule all_proc:
    input:
        rules.wctproc.input,
        expand(rules.evdplots_raw.output,
               timestamp=["159048405892"],
               trigger=["31"],
               plotext=["png","pdf"]) +
        expand(rules.evdplots_sig.output,
               resp=FPSAMPLES,
               cmap=['cubehelix','gnuplot','seismic'],
               timestamp=["159048405892"],
               trigger=["31"],
               plotext=["png","pdf"])


rule all:
    input:
        rules.all_proc.all
