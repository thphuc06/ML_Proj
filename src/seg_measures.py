"""SegFormer-B5 (Cityscapes) measures on a 640 crop, for sampling only (never labels). Used by
src/analysis/16_train_extra_preview.py and src/analysis/17_check_scorer_pilot.py.
  near_y  how low the sidewalk reaches: lowest row (0 top, 1 bottom) where sidewalk covers >= 10% of the row
  occ_v1  parked-vehicle share of the lower half, exactly as parked() in src/analysis/14_rule_check.py:
          vehicle blobs > 150 px touching sidewalk and not near a rider
  occ_v2  occ_v1 after dropping two false-positive kinds seen in the 2026-11-04 preview sheet:
          foreground  blob touches the bottom edge or covers > FG_AREA of the image (vehicle right at the camera)
          on road     in the band under the blob's lower third, road pixels outnumber sidewalk pixels
          (moving motorbikes are on the road, so this also removes most riders segmented as person; a person-based
          rule was tried and dropped because it also removed vendors' carts on the sidewalk)
          and 0 when parked + sidewalk pixels cover < MIN_DEN of the lower half (too little sidewalk to judge)
  n_v2    number of blobs kept by occ_v2"""
import numpy as np
import torch
from PIL import Image
from scipy import ndimage

MODEL = "nvidia/segformer-b5-finetuned-cityscapes-1024-1024"
ROAD, SW, PERSON, RIDER, CAR, TRUCK, BUS, MOTO, BIKE = 0, 1, 11, 12, 13, 14, 15, 17, 18
VEH = [CAR, TRUCK, BUS, MOTO, BIKE]
H, FG_AREA, BOTTOM, MIN_DEN = 512, 0.15, 6, 0.05


def load_model():
    from transformers import SegformerForSemanticSegmentation, SegformerImageProcessor
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    net = SegformerForSemanticSegmentation.from_pretrained(MODEL).to(dev).eval()
    if dev == "cuda":
        net = net.half()
    return SegformerImageProcessor.from_pretrained(MODEL), net, dev


@torch.no_grad()
def segment(model, paths):
    """Class map (H x H, uint8) for each image path."""
    proc, net, dev = model
    x = proc(images=[Image.open(p).convert("RGB").resize((H, H)) for p in paths], return_tensors="pt")["pixel_values"].to(dev)
    lg = net(pixel_values=x.half() if dev == "cuda" else x).logits.float()
    return torch.nn.functional.interpolate(lg, size=(H, H), mode="bilinear").argmax(1).cpu().numpy().astype(np.uint8)


def measures(seg):
    sw = seg == SW
    rows = np.where(sw.mean(axis=1) >= 0.10)[0]
    near_sw = ndimage.binary_dilation(sw, iterations=6)
    near_rider = ndimage.binary_dilation(seg == RIDER, iterations=6)
    blobs, n = ndimage.label(np.isin(seg, VEH))
    v1, v2, n2 = np.zeros_like(sw), np.zeros_like(sw), 0
    for k, sl in enumerate(ndimage.find_objects(blobs), 1):
        b = blobs == k
        if b.sum() <= 150 or not (b & near_sw).any() or (b & near_rider).any():
            continue
        v1 |= b
        if sl[0].stop >= H - BOTTOM or b.sum() > FG_AREA * H * H:
            continue
        ring = ndimage.binary_dilation(b, iterations=6) & ~b
        ring[: sl[0].start + 2 * (sl[0].stop - sl[0].start) // 3] = False
        if (seg[ring] == ROAD).sum() > (seg[ring] == SW).sum():
            continue
        v2 |= b
        n2 += 1

    def occ(mask, min_den=0.0):
        low = mask[H // 2:].sum()
        den = low + sw[H // 2:].sum()
        return float(low / den) if den >= max(min_den * H * H / 2, 1) else 0.0
    return {"near_y": float(rows.max() / H) if len(rows) else 0.0, "occ_v1": occ(v1), "occ_v2": occ(v2, MIN_DEN), "n_v2": n2}
