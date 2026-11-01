"""Shared paths, study-area bbox and small geo helpers (local metric projection, bearings)."""
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
RAW_OSM = DATA / "raw" / "osm"
RAW_META = DATA / "raw" / "metadata"
for d in (RAW_OSM, RAW_META):
    d.mkdir(parents=True, exist_ok=True)

# Study area: central HCMC (old D1, D3, D5, D10, Phu Nhuan, Binh Thanh). (south, west, north, east)
BBOX = (10.745, 106.650, 10.815, 106.725)
LAT0, LON0 = (BBOX[0] + BBOX[2]) / 2, (BBOX[1] + BBOX[3]) / 2
KX, KY = 111320 * math.cos(math.radians(LAT0)), 110574  # metres per degree (lon, lat); <0.1% error over this area


def env(key):
    return dict(l.split("=", 1) for l in (ROOT / ".env").read_text().splitlines() if "=" in l)[key]


def to_xy(lon, lat):
    return (lon - LON0) * KX, (lat - LAT0) * KY


def bearing_xy(x1, y1, x2, y2):
    """Compass bearing (0 = north, clockwise) from point 1 to point 2 in the local metric frame."""
    return math.degrees(math.atan2(x2 - x1, y2 - y1)) % 360


CROP_FOV, CROP_PITCH, CROP_PX = 90, -4, 640
DARK = 90  # mean grey level of the pano's upper half below this = night (stamped hours are unreliable)


def side_crops(equi, travel_bearing, compass):
    """Documented crop rule: two 90-deg views perpendicular to the direction of travel (L = -90, R = +90),
    pitch -4 deg, 640 px. Yaw is relative to the pano centre, whose compass direction is `compass`."""
    import numpy as np
    import py360convert
    out = {}
    for side, off in (("L", -90), ("R", 90)):
        yaw = (travel_bearing + off - compass + 180) % 360 - 180
        img = py360convert.e2p(equi, fov_deg=CROP_FOV, u_deg=yaw, v_deg=CROP_PITCH, out_hw=(CROP_PX, CROP_PX))
        out[side] = (img.astype(np.uint8), round(yaw, 1))
    return out


RIGHT_YAW_OFF = 60  # official crop (2026-10-23): right side, 60 deg from travel direction (30 deg ahead of perpendicular)


def right_crop(equi, travel_bearing, compass):
    """Official dataset crop: one right-side view (src/09_crop_param_study.py: best near-sidewalk visibility of
    yaw {60,75,90} x pitch {-4,-10}). Returns (image uint8, yaw relative to pano centre)."""
    import numpy as np
    import py360convert
    yaw = (travel_bearing + RIGHT_YAW_OFF - compass + 180) % 360 - 180
    img = py360convert.e2p(equi, fov_deg=CROP_FOV, u_deg=yaw, v_deg=CROP_PITCH, out_hw=(CROP_PX, CROP_PX))
    return img.astype(np.uint8), round(yaw, 1)


def axis_diff(a, b):
    """Angle between two undirected axes (0-90 deg): a street has no direction, a pano travels either way."""
    d = abs(a - b) % 180
    return min(d, 180 - d)
