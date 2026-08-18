# LiDAR terrain predictors

The terrain pipeline uses the Environment Agency LIDAR Composite DTM 1 m WCS.
It sends the pilot boundary's British National Grid bounding box to the service
and requests server-side resampling to 10 m. This avoids downloading national
coverage or hundreds of native 1 m tiles and keeps the free cloud workload
bounded. The resulting pilot GeoTIFF is about 36 MB and is not versioned in Git.

The grid feature product contains mean, standard deviation, minimum and maximum
elevation, local relief, mean slope, 90th-percentile slope, and valid pixel count
for each clipped 2 km cell. Elevation is in metres relative to Ordnance Datum
Newlyn; slope is in degrees.

The 2022 composite combines surveys captured between 2000 and 2022, choosing the
newest suitable coverage. It is therefore a largely static terrain covariate,
not a contemporaneous 2024 observation. Resampling to 10 m is appropriate for
catchment-scale screening but not asset-level drainage or engineering decisions.
