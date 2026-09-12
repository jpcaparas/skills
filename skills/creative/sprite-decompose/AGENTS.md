# sprite-decompose

Use this skill to separate many existing illustrations from one raster into transparent, alpha-tight PNG files and a validated manifest.

Keep `SKILL.md` authoritative. Use native image analysis for region and grouping decisions, then delegate only background fitting, alpha construction, trimming, writing, and verification to `scripts/sprite_decompose.py`.
