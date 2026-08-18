"""HydroATLAS upstream-basin site feature normalization."""

from typing import Any

import pandas as pd

SOURCE_ATTRIBUTES = (
    "HYBAS_ID",
    "NEXT_DOWN",
    "SUB_AREA",
    "UP_AREA",
    "pre_mm_uyr",
    "tmp_dc_uyr",
    "crp_pc_use",
    "pst_pc_use",
    "urb_pc_use",
    "for_pc_use",
    "cly_pc_uav",
    "slt_pc_uav",
    "snd_pc_uav",
    "soc_th_uav",
    "ero_kh_uav",
    "pop_ct_usu",
    "ppd_pk_uav",
    "rdd_mk_uav",
)


def rows_from_hydroatlas(features: list[dict[str, Any]]) -> pd.DataFrame:
    """Normalize site-to-basin Earth Engine results without rescaling source values."""
    rows = []
    for feature in features:
        properties = feature.get("properties", {})
        row = {"point_notation": str(properties["notation"])}
        row.update({name: properties.get(name) for name in SOURCE_ATTRIBUTES})
        rows.append(row)
    frame = pd.DataFrame(rows).reindex(columns=["point_notation", *SOURCE_ATTRIBUTES])
    if frame.empty:
        raise ValueError("Earth Engine returned no upstream site assignments")
    if frame["point_notation"].duplicated().any():
        raise ValueError("Earth Engine returned duplicate upstream site assignments")
    if frame[list(SOURCE_ATTRIBUTES)].isna().any().any():
        raise ValueError("Some monitoring sites have no complete HydroATLAS assignment")
    return frame.sort_values("point_notation").reset_index(drop=True)
