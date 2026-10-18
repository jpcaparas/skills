# Prompting Nano Banana

Use this file when writing or repairing a prompt. Each rule says where it came from: **[G]** is Google's [image generation guide](https://ai.google.dev/gemini-api/docs/image-generation#prompt-guide), **[T]** is this skill's 2026-10-18 tests (`references/evidence.md`). Templates are starting points; adapt them to the brief.

## Core rules

1. **Describe a scene, not a keyword list.** Write sentences covering subject, setting, composition, camera or medium, lighting, mood, and the image's purpose ("a hero image for a skincare landing page"). [G]
2. **State purpose and audience.** "A logo for a minimalist skincare brand" beats "a logo". [G]
3. **Use camera and art language for control:** "85 mm portrait lens, shallow depth of field", "top-down flat lay", "low-angle shot", "isometric", "flat vector, two-tone". [G]
4. **Say what you want, not what you don't.** "An empty, deserted street" works better than "no cars". [G]
5. **Break complex scenes into ordered steps:** background first, then the main subject, then details. [G]
6. **Ask for one image per request.** Requests for "three variations" returned one image. Run separate requests (or `batch-submit`) for variants. [T]
7. **Do not rely on seeds or temperature.** Both were accepted, but identical seeds gave different images. Steer with words. [T]

## Text in images

The model sets short and medium copy well, including colons, em dashes, middle dots, arrows, accents and macrons. Its failures are additions and casing rather than misspellings. [T]

- Put every visible string in double quotes and give each line its own line in the prompt.
- Add a closing instruction: *"Show exactly these lines and nothing else — no icons, pictograms, logos or extra words. Keep the capitalisation, punctuation and accents exactly as written."* Without it, signs gained airplane icons and recased lines; with it, 2 of 2 were exact. [T]
- Expect unrequested text with more thinking: at `medium` and `high`, labelled diagrams gained titles and captions ("Sun", "THE SOLAR SYSTEM"). Say "no title, no caption, no other labels" when that matters. [T]
- Small print renders legibly at 1K and 2K but tends to come back in capitals; 4K kept sentence case in the test. Inspect it, and composite legally binding copy instead of trusting it. [T]
- When the copy itself needs writing, write and approve the text first, then ask for the image with that exact text. [G]

```text
A minimalist event poster on a cream background. Title at the top in a bold serif: "Night Market: Vol. 3".
Below it, a simple line illustration of paper lanterns. At the bottom, two lines in a clean sans-serif:
"Sat 14 Nov — 6pm till late" and "Free entry · All ages".
Show exactly these lines and nothing else. Keep capitalisation and punctuation exactly as written.
```

## Data, charts, diagrams, maps

- Give the numbers. "Bars drawn to scale on a 0–400 axis with gridlines every 100: Mon 120, Tue 310, ..." produced correct, proportional charts at every thinking level. [T]
- For facts the model must recall (release years, chronology), use `medium` or `high`, or `--search`. At `minimal`, one of two film timelines had two wrong years; `medium` and `high` were 4 of 4 correct. [T]
- Name orientation explicitly: "standard anatomical orientation", "north at the top", "left to right in order from the Sun". [T]
- Describe precise geometry in words and then check it. A drawn reference did **not** fix a clock: given an exact 7:20 diagram, both renders moved the hour hand to roughly 7:35. Composite exact hands or dials afterwards. [T]

## Editing an image

- Name the single change, then list what must stay: *"Replace the mint sprig with a thin slice of lemon. Keep everything else exactly the same: the cup, saucer, lighting, background and camera angle."* The rest of the image stayed near-identical (about 38 dB PSNR away from the edit), but edits regenerate the whole frame, so pixels are never bit-identical. [T]
- Ink and masks need no special API. Draw on the image ("place a teaspoon where the red circle is, then remove the red circle") or send a black-and-white mask as a second image and say what white means. Both the ink edit and the mask edit placed the object in the marked spot, left no marks behind, and changed nothing else visible. [T][G]
- Omit `--ratio` to keep the input's aspect ratio. [T]
- For style transfer, say which elements must stay in place: "Keep the composition, the red cable car and the houses in the same positions." [G]

## Several references

- Number the images and give each a job: *"Image 1 is the product. Image 2 sets the lighting and palette. Image 3 is the background location."* [G]
- Name each product's distinguishing details and quote any label text. A jar label ("ORCHARD & OAK", "Feijoa Chutney", "250 g · Batch 07") survived exactly into new lifestyle scenes, 2 of 2. [T]
- Stay within 14 references: 4 people and 10 objects are the documented fidelity limits. The API accepted 20 images, but that is beyond the documented range. [G][T]
- References can be video (a frame summary) or PDF (the menu text came through exactly). [T]

## Characters and multi-turn work

- Continue the same conversation for consistency (`--continue`); a mascot kept its identity and earlier additions across three turns. [T]
- Make one change per turn and restate what must persist ("keep the raincoat"). [G][T]
- Repeat small identity details (a scar, a single earring) in every prompt; they are the first to drift. [G]
- If drift accumulates, start a new conversation with a detailed description and the best image as a reference. [G]
- For multiple views of a character, include earlier outputs as references when asking for a new angle. [G]

## Handedness and mirror-sensitive details

The model put a pen in the right hand in 8 of 8 left-handed signing scenes, including when the prompt said which side of the frame the hand was on. If no legible text is visible, generate the scene and flip it horizontally (`magick in.jpg -flop out.jpg`). Otherwise accept the limitation or composite. [T]

## Search-grounded images

- Tell the model to search first: *"Search the web for ..., then create ..."*. [G]
- Use `--image-search` for real species, products and places whose appearance matters; the takahē and tūī cards came back accurate. [T]
- Image search does not use real photos of people as references. [G]
- Grounded responses carry attribution. Show the saved `.search.html` suggestions when presenting results in a product UI (Google's terms require it). [G]

## Templates

**Photorealistic scene**

```text
A [shot type] photograph of [subject] [doing what] in [setting]. [Lens, angle]. [Lighting and time of day].
[Mood]. [Background details]. Purpose: [where the image will be used].
```

**Product shot**

```text
A premium studio product photograph for an online store: [product with materials, colours, distinguishing details]
on [surface], [props], [shadow direction], [background]. [Label text in quotes, exactly as written.]
```

**Illustration or icon**

```text
A [style, e.g. flat vector / watercolour / 3D clay] illustration of [subject], [palette], [line weight or texture],
[background]. [Composition and negative space].
```

**Sequential panels**

```text
A four-panel comic strip in [style], arranged as a 2x2 grid. The same [character description] appears in every panel.
Panel 1: [action], speech bubble: "[text]". Panel 2: ... Keep the character's colours and proportions identical across panels.
```

**Wide banner or panorama** — use `--ratio 4:1`/`8:1` (or `1:4`/`1:8` for tall), describe one continuous scene ("a single unbroken horizon"), and request 2K for a usable width.
