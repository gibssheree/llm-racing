"""Hand-drawn circuit shapes, before repair.

Each one is drawn for a silhouette rather than for a lap time: a hairpin is a
hairpin because the points double back, not because a search happened to find
one. tracksearch.repair() then nudges whatever is illegal.
"""

DRAFTS = {
    # long start straight, fast right, esses down the right side, big stop,
    # a proper hairpin at the bottom, fast sweeper back up the left
    "autodrome": [
        (430, 330), (1100, 280), (1780, 270), (2340, 330),
        (2700, 560), (2620, 830), (2380, 980), (2560, 1220),
        (2480, 1520), (2130, 1740), (1700, 1810), (1330, 1700),
        (1240, 1420), (1470, 1250), (1280, 1030), (900, 1080),
        (700, 1330), (520, 1480), (330, 1240), (350, 780),
    ],
    # two enormous straights joined by one hairpin at each end
    "speedbowl": [
        (400, 420), (1200, 300), (2050, 290), (2560, 360),
        (2790, 640), (2760, 950), (2440, 1090), (2600, 1330),
        (2540, 1640), (2100, 1800), (1250, 1810), (560, 1720),
        (330, 1450), (360, 1080), (620, 940), (380, 730),
    ],
    # infield knot: chicane, hairpin, esses, almost no straight anywhere
    "technical": [
        (520, 380), (980, 300), (1240, 470), (1560, 330),
        (1900, 470), (2260, 340), (2620, 520), (2680, 860),
        (2380, 1000), (2600, 1260), (2350, 1520), (1960, 1420),
        (1780, 1650), (1420, 1720), (1180, 1520), (1330, 1250),
        (1020, 1120), (720, 1290), (470, 1520), (300, 1200),
        (430, 880), (700, 760), (420, 590),
    ],
    # the long one: wide sweepers, a stadium section, one hairpin
    "endurance": [
        (380, 620), (760, 340), (1400, 250), (2050, 270),
        (2540, 400), (2800, 700), (2760, 1060), (2450, 1230),
        (2680, 1470), (2400, 1760), (1900, 1830), (1450, 1760),
        (1180, 1560), (1360, 1330), (1080, 1180), (740, 1240),
        (560, 1500), (300, 1330), (280, 940),
    ],
    # angular street circuit: long drags into near right-angle corners
    "street": [
        (360, 400), (1150, 330), (1900, 330), (2620, 420),
        (2700, 780), (2280, 900), (2280, 1220), (2680, 1340),
        (2620, 1700), (1980, 1790), (1420, 1720), (1420, 1380),
        (980, 1300), (880, 1660), (480, 1700), (320, 1360),
        (620, 1120), (330, 880),
    ],
    # figure-of-eight feel without a crossing: two big loops pinched in the middle
    "twinloop": [
        (500, 480), (1080, 320), (1500, 520), (1360, 880),
        (900, 1000), (700, 1340), (1050, 1620), (1600, 1700),
        (2050, 1560), (2180, 1200), (1800, 1000), (1900, 640),
        (2340, 430), (2740, 620), (2800, 1080), (2680, 1560),
        (2280, 1810), (1500, 1880), (760, 1820), (350, 1560),
        (300, 1020), (330, 700),
    ],
}
