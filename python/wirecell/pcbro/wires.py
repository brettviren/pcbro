def generate(pitch=0.5):
    # 320mm x 320mm active area with 64x64 strips.  Strip pitch is
    # 5mm.  1.25mm hole at 2mm hole-pitch, 2.5mm hole at 3.33 mm
    # hole-pitch.  A collection strip has constant hole pattern.
    # Induction strip is half small-hole, half large-hole.
    pitch = 0.5                 # cm, strip pitch
    

    # "physical" channels match strips and are:
    # - 1-64 for collection
    # - 65-128 for induction 1
    # - 129-192 for duplicate induction 2
    print("warning: using ideal wire spacing")
    lines = list()
    
    # In Z vs Y space the detector has 4 unique quadrants (ignoring
    # some edge details)
    # (+Y, +Z) : large holes (large col chan nums, large ind chan nums)
    # (-Y, +Z) : large holes (large col chan nums, small ind chan nums)
    # (+Y, -Z) : small holes (small col chan nums, large ind chan nums)
    # (-Y, -Z) : small holes (small col chan nums, small ind chan nums)
    

    # A first inducton strip runs parallel to Z axis.  Small holes are
    # Z<0, big holds Z>0.  Strips counted from most negative to most
    # positive Y.  A strip boundary between two middle strips is at
    # Y=0.
    plane=0
    sx = ex = +0.1              # cm, bogus value
    sz = -32*pitch
    ez = +32*pitch
    sy = ey = -32*pitch + 0.5*pitch
    for iwire in range(64,128):
        chan = iwire+1
        l = f'{chan:3d} {plane:1d} {iwire:3d} {sx:8.2f} {sy:8.2f} {sz:8.2f} {ex:8.2f} {ey:8.2f} {ez:8.2f}'
        lines.append(l)
        sy += pitch
        ey += pitch
        
    # A second induction plane is identically overlapping the first
    # and has "virtual" channels starting just after the first
    # induction plane.  Data for this plane is identical for first
    # induction but may have a different field response.
    plane=1
    # put collection strips pointing along Y-axis and just negative in X.
    sx = ex = +0.1              # cm, and totally bogus
    sz = -32*pitch
    ez = +32*pitch
    sy = ey = -32*pitch + 0.5*pitch
    for iwire in range(128,192):
        chan = iwire+1
        l = f'{chan:3d} {plane:1d} {iwire:3d} {sx:8.2f} {sy:8.2f} {sz:8.2f} {ex:8.2f} {ey:8.2f} {ez:8.2f}'
        lines.append(l)
        sy += pitch
        ey += pitch

    # A single collection plane has strips parallel to the Y-axis.
    # Strips are counted from most-negative to most-positive Z.  First
    # 32 channels (Z<0) have small holes, second 32 channels (Z>0)
    # have large holes.
    plane=2                     # collection
    # put collection strips pointing along Y-axis and just negative in X.
    sx = ex = -0.1              # cm, and totally bogus
    sy = -32*pitch
    ey = +32*pitch
    sz = ez = -32*pitch + 0.5*pitch
    for iwire in range(0,64):
        chan = iwire+1
        l = f'{chan:3d} {plane:1d} {iwire:3d} {sx:8.2f} {sy:8.2f} {sz:8.2f} {ex:8.2f} {ey:8.2f} {ez:8.2f}'
        lines.append(l)
        sz += pitch
        ez += pitch

    text = '\n'.join(lines)
    text += '\n'
    return text
    
