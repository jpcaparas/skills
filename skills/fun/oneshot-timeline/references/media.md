# Documentary images and investigative collage

Read this when an explainer uses third-party photographs, logos, documents, screenshots or image-library assets. The goal is an engaging editorial composition that remains honest about what its source images show.

## Discover broadly and select deliberately

Search official organisations, company press rooms, government archives, courts, museums, news outlets, photo agencies, Wikimedia, image libraries and other useful sources. Do not impose a domain allowlist or retreat to generic icons when an authentic picture would explain the topic better. A search engine is a discovery aid; inspect the originating page and full image before selecting it.

Download selected media into the workspace and preserve the unmodified master. Bundle processed derivatives locally; do not hotlink a news-site URL as a runtime dependency. Inspect the actual downloaded file: a `.jpg` URL can return a blocked-page HTML response. Use the environment's authenticated attachment downloader for private user attachments, and do not forward credentials to unrelated hosts.

Broad discovery is not blanket permission to republish. Record the creator, original page, direct file URL when available, capture/publication date, licence or stated reuse basis and required attribution. Government hosting does not make an underlying third-party photograph or court exhibit public domain. Publicly accessible does not mean unrestricted reuse. Respect access controls and licence conditions; do not remove watermarks. If rights are uncertain, use a different suitable asset, link to it, or clearly flag a narrowly justified editorial reproduction for review rather than inventing permission.

## Make a real cutout when it helps

1. Choose an image with enough detail for its eventual size. Crop to the relevant person or object; remove unrelated bystanders from the composition rather than implying they participated.
2. Use an available background-removal or image-editing tool to create actual alpha transparency. For a simple flat background, a conservative mask may suffice; for hair or complex edges use segmentation and inspect the result. Tool names and models are environment choices, not hard dependencies of this skill.
3. Preserve documentary faces, logos, quotations and document pixels. Background removal, cropping, resizing and outlines are editorial transformations; generating a new face, changed document or fake screenshot is not evidence. Keep original text and logo proportions intact.
4. Add padding **before** expanding the alpha mask for a stroke, so the outline is not clipped at the image boundary. A cream outer sticker edge with a fine dark edge often reads well on pastels. Keep any shadow restrained.
5. Check the alpha channel and composite the exported asset over light and dark backgrounds. Repair missing hair, leftover background, clipped strokes or accidental halos. A white rectangle or checkerboard pattern is not proof of transparency.
6. If clean isolation fails, use an intentional framed photograph or document crop. Label it honestly as a photograph, not as a successful cutout. Do not discard useful authentic media merely because segmentation is imperfect.

Use paid generation or processing only with the required authorization. If an available tool cannot preserve the evidence, keep a simpler local composition. An image-generation tool may create decorative paper, original icons or conceptual illustration, but must not fabricate documentary material.

## Compose like an editorial desk

Give each collage one focal subject and a few supporting pieces. Use topic-matched pastel paper, short annotations, restrained rotations and intentional outline strokes. Show a real source document when the document matters; show a contextual portrait when the person matters. A different crop alone is not always a different idea.

Keep all essential labels in adjacent HTML. Caption any potentially misleading time relationship, such as a 2015 portrait accompanying a 2019 event. Distinguish illustration from evidence; do not mount invented labels to look like an authentic company filing. Apply the graph/vector quality gate in the main workflow before keeping supplementary marks. Collage alone is a complete composition.

Optimise image size for the rendered use, set intrinsic dimensions and lazy-load below-the-fold assets. Keep full-resolution originals in the workspace, not in the portable artifact unless actually needed.

## Leave an auditable credit trail

Keep a compact media note in the workspace. For each original and final asset record:

| Record | What it establishes |
| --- | --- |
| Local original and derivative paths | Which source pixels produced the displayed asset |
| Source page, creator and direct download | Attribution and reproducible discovery |
| Capture date and publication date, when known | What the picture can and cannot establish about chronology |
| Licence or reuse basis, with source | Actual conditions or explicit uncertainty |
| Modifications | Crop, isolation, resize, rotation, strokes and drawn annotations |

Expose the relevant attribution and modification notices in a reader-accessible credits page or section in the artifact, with links from the timeline. Keep licence text where required. Do not bury all credits in a workspace file the reader never receives. Do not copy private source notes into a public artifact by default.
