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
#   --config stamps=/path/to/scripts/rawdata-2020-05-26.stamps \
#            binpat=/path/to/"Rawdata_05_26_2020/run01tri/WIB00step18_FEMB_B8_{timestamp}.bin" \
#            workdir=/path/to/work/pcbro" \
#            cfgdir=/path/to/source/pcbro/cfg" \
#   --directory /home/bv/work/pcbro
# see "scripts/snakeit.sh" 

# In the work directory, these raw data files are needed.
# "Rawdata_05_26_2020/run01tri/WIB00step18_FEMB_B8_{timestamp}.bin"
rawdata_bin_p = config["binpat"]
cdir = config["cfgdir"]
odir = config["outdir"]         # where to put stuff we make here
fdir = config["rfrdir"]         # raw field response 


# These names must match what get-fpdata.sh provide.
# We must enact different patterns depending on the sample.
FP2SAMPLES = ["dv-2000v", "dv-2000v-h2mm0", "dv-2000v-h2mm5"]
FP3SAMPLES = ["reference3views"]
FPSAMPLES = FP2SAMPLES + FP3SAMPLES

# The 50L DAQ run timestamps we want to process
#TIMESTAMPS = [s for s in open("scripts/rawdata-2020-05-26.stamps").read().split('\n') if s.strip()]
TIMESTAMPS = [s for s in open(config["stamps"]).read().split('\n') if s.strip()]


# Just simulation or sim+sigproc
TIERS = ["sim", "ssp"]
TRIGGERS = [0]

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
        col = f"{fdir}/{{resp}}/collection.tar",
        ind1 =f"{fdir}/{{resp}}/induction1.tar",
        ind2 =f"{fdir}/{{resp}}/induction2.tar"
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
        f"{odir}/plots/fpresp/{{resp}}.pdf"
    shell:
        "wirecell-pcbro fpstrips-draw-fp {input} {output}"

# Make intermediate NPZ file following WCT units/layout
rule wctnpzfile:
    input:
        fpresp_p
    output:
        f"{odir}/wctresp/{{resp}}.npz"
    shell:
        "wirecell-pcbro fpstrips-wct-npz {input} {output}"

# Make WCT field response JSON file from FP npz file
rule wctjsonfile:
    input:
        fpresp_p
    output:
        f"{odir}/resp/{{resp}}.json.bz2"
    shell:
        "wirecell-pcbro convert-fpstrips {input} {output}"

# Make standard WCT field response plots
rule fieldplots:
    input:
        rules.wctjsonfile.output
    output:
        f"{odir}/plots/wctresp/{{resp}}.png"
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
        f"{odir}/proc/raw/raw-{{timestamp}}.npz"
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
        f"{odir}/proc/sig/sig-{{resp}}-{{timestamp}}.npz"
    shell: """
    wire-cell -A resps_file={input.resp} \
      -A infile={input.data} -A outfile={output} \
      -c cli-bin-sp-npz.jsonnet
    """
    

rule activity:
    input:
        rules.sigproc.output
    output:
        f"{odir}/proc/act/sig-active-{{resp}}-{{timestamp}}.npz"
    shell: """ 
    wirecell-pcbro activity -t 1000000 {input} {output}
    """

# Roll up everything
rule wctproc:
    input:
        expand(rules.decode.output, timestamp=TIMESTAMPS),
        expand(rules.sigproc.output, resp=FP2SAMPLES, timestamp=TIMESTAMPS),
        expand(rules.activity.output, resp=FP2SAMPLES, timestamp=TIMESTAMPS)


rule evdplots_raw:
    input:
        rules.decode.output
    output:
        f"{odir}/plots/raw/raw-{{timestamp}}-{{trigger}}-{{cmap}}.{{plotext}}"
    shell: """
    wirecell-pcbro evd2d -t {wildcards.trigger} --channels '0:64,64:128' \
        --title='Raw data from run {wildcards.timestamp} trigger {{trigger}}' \
        --color-unit='ADC from baseline' \
        --color-map={wildcards.cmap} \
        --color-range='-300,0,300' \
        --ticks '0:645' --tshift '-12' \
        --baseline-subtract=median \
        -o {output} {input}
    """


rule evdplots_sig:
    input:
        rules.sigproc.output
    output:
        f"{odir}/plots/sig/sig-{{resp}}-{{timestamp}}-{{trigger}}-{{cmap}}.{{plotext}}"
    shell: """
    wirecell-pcbro evd2d -t {wildcards.trigger} --channels '0:64,64:128' \
        --title='{wildcards.resp} signals from run {wildcards.timestamp} trigger {{trigger}}' \
        --color-map={wildcards.cmap} \
        --color-range='0,2500,20000' --mask-min=0 --ticks='0:450' \
        -T gauss0 \
        -o {output} {input}
    """


favorite_timestamps = ["159048405892"]
rule fav_proc:
    input:
        expand(rules.decode.output,
               timestamp=favorite_timestamps),
        expand(rules.sigproc.output,
               resp=FP2SAMPLES, timestamp=favorite_timestamps),
        expand(rules.activity.output,
               resp=FP2SAMPLES, timestamp=favorite_timestamps),
        expand(rules.evdplots_raw.output,
               cmap=['nipy_spectral','seismic'],
               timestamp=favorite_timestamps,
               trigger=["31"],
               plotext=["png","pdf"]),

        # for avgwf
        expand(rules.evdplots_raw.output, cmap=['seismic'],plotext=["png"],
               timestamp=["159048336841"],trigger=["12"]),
        expand(rules.evdplots_raw.output, cmap=['seismic'],plotext=["png"],
               timestamp=["159048364354"],trigger=["40"]),
        expand(rules.evdplots_raw.output, cmap=['seismic'],plotext=["png"],
               timestamp=["159048405892"],trigger=["23"]),

        expand(rules.evdplots_sig.output,
               resp=FP2SAMPLES,
               cmap=['cubehelix','gnuplot','seismic', 'nipy_spectral'],
               timestamp=favorite_timestamps,
               trigger=["31"],
               plotext=["png","pdf"])


# A "tier" of "sim" (just simulation) or "ssp" (sim+sigproc)
rule wctsimtier3:
    input:
        respfile=rules.wctjsonfile.output,
        config=f"{cdir}/cli-{{tier}}-npz.jsonnet"
    output:
        f"{odir}/proc/{{tier}}/{{resp}}.npz"
    params:
        outdir = f"{odir}/proc/{{tier}}"
    shell:
        """
        mkdir -p {params.outdir};
        wire-cell -c {input.config} \
          -A resps_file={input.respfile} \
          -A outfile={output} 
        """

tier_plot_p = f"{odir}/plots/{{tier}}/{{trigger}}/{{resp}}.png"
rule evdplots3_sim:
    input:
        rules.wctsimtier3.output
    output:
        tier_plot_p
    wildcard_constraints:
        tier=r"\bsim\b"
    shell: """
    wirecell-pcbro evd2d -t {wildcards.trigger} \
        --channels '0:64,64:128,128:192' \
        --cnames 'col,ind1,ind2' \
        --title='Sim raw trigger {wildcards.trigger} ({wildcards.resp})' \
        --color-unit='ADC from baseline' \
        --color-map={wildcards.cmap} \
        --color-range='-300,0,300' \
        --ticks='0:800' \
        --baseline-subtract=median \
        -T orig0 \
        -o {output} {input}
    """

rule evdplots3_ssp:
    input:
        rules.wctsimtier3.output
    output:
        tier_plot_p
    wildcard_constraints:
        tier=r"\bssp\b"
    shell: """
    wirecell-pcbro evd2d -t {wildcards.trigger} \
        --channels '0:64,64:128,128:192' \
        --cnames 'col,ind1,ind2' \
        --title='Sim sigproc trigger {wildcards.trigger} ({wildcards.resp})' \
        --color-map={wildcards.cmap} \
        --color-range='0,2500,20000' \
        --mask-min=0 \
        --ticks='0:800' \
        -T gauss0 \
        -o {output} {input}
    """

rule all_tier3:
    input:
        expand(rules.wctsimtier3.output,
               resp=FP3SAMPLES, tier=["sim","ssp"]),
        expand(tier_plot_p, resp=FP3SAMPLES, tier=["sim","ssp"],
               cmap=["seismic", "cubehelix", "gnuplot", "nipy_spectral"],
               trigger=TRIGGERS)


rule avgwf_raw:
    input:
        rules.decode.output
    output:
        f"{odir}/plots/avgwf/raw-{{timestamp}}-{{trigger}}.png"
    params:
        array = "frame__{trigger}"
    shell: """
    ./scripts/avgwf.py plot \
      -a {params.array} \
      -o {output} {input}
    """
rule avgwf_munge:
    input:
        "munged-frame-sim.npz"
    output:
        f"{odir}/plots/avgwf/munged-frame-sim.png"
    params:
        array = "frame_orig0_0"
    shell: """
    ./scripts/avgwf.py plot \
      -a {params.array} \
      -o {output} {input}
    """

rule all_avgwf:
    input:
        expand(rules.avgwf_raw.output, zip,
               timestamp=["159048336841",
                          "159048364354",
                          "159048405892"],
               trigger=["12","40","23"]),
        rules.avgwf_munge.output
               

# 12 /home/bv/work/pcbro/proc/raw/raw-159048336841.npz
# 40 /home/bv/work/pcbro/proc/raw/raw-159048364354.npz
# 23 /home/bv/work/pcbro/proc/raw/raw-159048405892.npz


rule all:
    input:
        rules.fav_proc.input

