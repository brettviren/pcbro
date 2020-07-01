[
    {
        rule: "(= direction 'inject')",
        rw: "w",
        filepat: "flow.hdf",
        grouppat: "flow/{stream}",
    },
    {
        rule: "(= direction 'extract')",
        rw: "r",
        filepat: "flow.hdf",
        grouppat: "flow/{stream}",
    }
]
