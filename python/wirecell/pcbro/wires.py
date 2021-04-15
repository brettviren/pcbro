
from wirecell import units
def generate_ref3(pitches=(5*units.mm, 5*units.mm, 5*units.mm)):
    '''
    3-view reference case:
    - equilateral hole pattern
    - hole spacing ~2.85mm
    - 2.3 mm hole diameter
    - strips oriented at 120 deg
    - collection strip pitch ~ 4.9 mm
    - inductions strip pitch: ~7.35 mm
    - distance between the two PCB’s: 10 mm
    - PCB thichness: 3.2 mm
    '''
    for plane, pitch in enumerate(pitches):
        pass



def generate_50l(pitches=(5*units.mm, 5*units.mm, 5*units.mm)):

    # 320mm x 320mm active area with 64x64 strips.  Strip pitch is
    # 5mm.  1.25mm hole at 2mm hole-pitch, 2.5mm hole at 3.33 mm
    # hole-pitch.  A collection strip has constant hole pattern.
    # Induction strip is half small-hole, half large-hole.

    pitch_cm = [p/units.cm for p in pitches]
    

    # "physical" channels match strips and are:
    # - 1-64 for collection
    # - 65-128 for induction 1
    # - 129-192 for duplicate induction 2
    print(f"generate wires with: {pitch_cm} cm")
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
    sz = -32*pitch_cm[plane]
    ez = +32*pitch_cm[plane]
    sy = ey = -32*pitch_cm[plane] + 0.5*pitch_cm[plane]
    for iwire in range(64,128):
        chan = iwire+1
        l = f'{chan:3d} {plane:1d} {iwire:3d} {sx:8.2f} {sy:8.2f} {sz:8.2f} {ex:8.2f} {ey:8.2f} {ez:8.2f}'
        lines.append(l)
        sy += pitch_cm[plane]
        ey += pitch_cm[plane]
        
    # A second induction plane is identically overlapping the first
    # and has "virtual" channels starting just after the first
    # induction plane.  Data for this plane is identical for first
    # induction but may have a different field response.
    plane=1
    # put collection strips pointing along Y-axis and just negative in X.
    sx = ex = +0.1              # cm, and totally bogus
    sz = -32*pitch_cm[plane]
    ez = +32*pitch_cm[plane]
    sy = ey = -32*pitch_cm[plane] + 0.5*pitch_cm[plane]
    for iwire in range(128,192):
        chan = iwire+1
        l = f'{chan:3d} {plane:1d} {iwire:3d} {sx:8.2f} {sy:8.2f} {sz:8.2f} {ex:8.2f} {ey:8.2f} {ez:8.2f}'
        lines.append(l)
        sy += pitch_cm[plane]
        ey += pitch_cm[plane]

    # A single collection plane has strips parallel to the Y-axis.
    # Strips are counted from most-negative to most-positive Z.  First
    # 32 channels (Z<0) have small holes, second 32 channels (Z>0)
    # have large holes.
    plane=2                     # collection
    # put collection strips pointing along Y-axis and just negative in X.
    sx = ex = -0.1              # cm, and totally bogus
    sy = -32*pitch_cm[plane]
    ey = +32*pitch_cm[plane]
    sz = ez = -32*pitch_cm[plane] + 0.5*pitch_cm[plane]
    for iwire in range(0,64):
        chan = iwire+1
        l = f'{chan:3d} {plane:1d} {iwire:3d} {sx:8.2f} {sy:8.2f} {sz:8.2f} {ex:8.2f} {ey:8.2f} {ez:8.2f}'
        lines.append(l)
        sz += pitch_cm[plane]
        ez += pitch_cm[plane]

    text = '\n'.join(lines)
    text += '\n'
    return text
    
