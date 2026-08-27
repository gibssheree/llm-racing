"""Global tuning constants for LLM Grand Prix."""

# ---------------------------------------------------------------- display ----
SCREEN_W, SCREEN_H = 1360, 780
FPS = 60
TITLE = "LLM GRAND PRIX"

# The world the track lives in (pixels). Bigger than the screen; camera pans.
WORLD_W, WORLD_H = 3000, 2000

# ------------------------------------------------------------------ track ----
TRACK_HALF_WIDTH = 100         # road is 200px wide - still 11 car-widths across
KERB_WIDTH = 14
SAMPLES_PER_SEGMENT = 30       # raw spline resolution per control segment
SMOOTH_PASSES = 4              # Laplacian passes that remove spline kinks
SAMPLE_SPACING = 15.0          # final uniform centreline spacing (px)
GRID_CELL = 130                # spatial hash cell (must be >= TRACK_HALF_WIDTH)
MASK_RES = 4                   # tarmac bitmap resolution, px per cell

# ------------------------------------------------------------------- race ----
DEFAULT_LAPS = 3
COUNTDOWN_SECONDS = 3.6
GRID_ROW_GAP = 70              # spacing between rows on the starting grid
GRID_COL_GAP = 58              # lateral spacing between the two grid columns

# ---------------------------------------------------------------- physics ----
# Units are pixels and seconds. One "metre" is roughly 12px.
PX_PER_M = 7.0
SUBSTEPS = 2                   # physics substeps per frame, keeps grip stable
OFFTRACK_GRIP_MULT = 0.42      # sliding on grass
OFFTRACK_DRAG = 2.4            # extra rolling resistance on grass
WALL_BOUNCE = 0.35             # energy kept when clipping the outer barrier
CAR_LENGTH = 34
CAR_WIDTH = 18
COLLISION_RADIUS = 15

# ----------------------------------------------------------------- vision ----
SENSOR_RANGE = 560.0           # how far a car can "see" the track edge
SENSOR_STEP = 10.0             # raycast marching step (px)
PROXIMITY_RANGE = 130.0        # how far a car can sense another car

# ----------------------------------------------------------------- colours ---
C_GRASS_A = (26, 48, 33)
C_GRASS_B = (31, 56, 39)
C_ROAD = (56, 58, 64)
C_ROAD_DARK = (48, 50, 56)
C_KERB_A = (198, 62, 62)
C_KERB_B = (232, 232, 232)
C_LINE = (218, 218, 224)
C_BG = (13, 15, 20)
C_PANEL = (19, 22, 29)
C_PANEL_EDGE = (44, 50, 62)
C_TEXT = (226, 230, 238)
C_TEXT_DIM = (138, 147, 163)
C_ACCENT = (108, 176, 255)
