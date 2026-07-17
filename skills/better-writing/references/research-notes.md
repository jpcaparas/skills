# Research notes

Use this reference when you need the evidence behind the humanisation rules, want to extend `assets/aiisms.json`, or need to explain why the scanner cannot determine authorship.

Last reviewed: 2026-07-17.

## What the evidence supports

### Lexical preferences exist, but they move

Large-corpus studies have measured abrupt increases in certain style words after widespread LLM adoption. Kobak and colleagues analysed more than 15 million biomedical abstracts and used excess-vocabulary analysis to identify population-level shifts. Juzek and Ward proposed a transferable method that combines time-series change, topical controls, and comparison with model output; their focal terms included words such as `delve`, `intricate`, and `underscore`.

These studies estimate change across corpora. They do not establish that a given author or sentence used a model.

Sources:

- [Kobak et al., *Delving into LLM-assisted writing in biomedical publications through excess vocabulary*](https://arxiv.org/abs/2406.07016)
- [Juzek and Ward, *Why Does ChatGPT “Delve” So Much?*](https://arxiv.org/abs/2412.11385)
- [Liang et al., *Monitoring AI-Modified Content at Scale*](https://arxiv.org/abs/2404.01268)

Lexical signals also drift. Public discussion can make writers and model users avoid a notorious word while other preferred words continue to rise. Human speech can absorb model-associated wording as people encounter it. A static blacklist therefore decays quickly and risks punishing ordinary language.

Sources:

- [Geng and Trotta, *Human-AI Coevolution*](https://arxiv.org/abs/2502.09606)
- [Yakura et al., *Empirical evidence of Large Language Model’s influence on human spoken communication*](https://arxiv.org/abs/2409.01754)

Operational consequence: treat words as weak, contextual signals. Prefer clusters, record review dates, test counterexamples, and revise the thought rather than banning the token.

### Structure and distribution carry more information than one phrase

Research comparisons have found differences across lexical diversity, syntax, discourse, cadence, stance, and narrative structure. Results vary by model, prompt, language, proficiency, genre, and corpus.

Useful dimensions include:

- sentence-length distribution and syntactic depth
- coordination, subordination, nominalisation, and fronted phrases
- discourse-marker selection and position
- stance, hedging, boosting, and counterargument
- lexical diversity and semantic repetition
- punctuation distribution and burstiness
- paragraph regularity and conclusion allocation
- narrative chronology, ambiguity, agency, and thematic explanation

Sources:

- [Herbold et al., human and ChatGPT essay comparison in *Scientific Reports*](https://www.nature.com/articles/s41598-023-45644-9)
- [Huber and Niklaus, *CLEAR: A Comprehensive Linguistic Evaluation of Argument Rewriting by Large Language Models*](https://aclanthology.org/2025.findings-emnlp.1065/)
- [Durandard et al., *LLMs stick to the point, humans to style*](https://aclanthology.org/2025.sigdial-1.16/)
- [Zamaraeva et al., formal syntactic comparison of LLM and human news text](https://aclanthology.org/2025.acl-long.443/)
- [Guo et al., recursive synthetic-text training and diversity](https://aclanthology.org/2024.findings-naacl.228/)
- [StoryScope narrative-feature study](https://arxiv.org/abs/2604.03136)

Operational consequence: scan across categories and explain the observation. Do not reduce a multidimensional writing problem to a word list.

### Model assistance can improve an individual artefact while narrowing collective variety

In an experimental short-story study, access to generative-AI ideas improved some measures of individual story quality while making the set of stories more similar. This does not mean every assisted draft is generic. It does explain why preserving individual selection, judgement, and voice matters.

Source:

- [Doshi and Hauser, *Generative AI enhances individual creativity but reduces the collective diversity of novel content*](https://doi.org/10.1126/sciadv.adn5290)

Operational consequence: protect voice anchors and compare the revision with the writer's own samples, not with an imagined universal human style.

### Punctuation is contextual

Population-level studies can observe punctuation shifts, but a punctuation mark is not a document-level signature. The AP Stylebook explicitly rejects treating the em dash itself as an AI tell; it recommends using the mark purposefully rather than applying a numerical ban.

Sources:

- [AP Stylebook, *Em dash is not an AI tell*](https://www.apstylebook.com/blog_posts/24)
- [Population-level em-dash study](https://arxiv.org/abs/2606.29540)

Operational consequence: inspect punctuation distribution, syntactic purpose, and nearby patterns. Never gate a draft because it contains one dash, semicolon, colon, or question mark.

### Punctuation choices encode different sentence relations

Style authorities converge on a relation-first account of punctuation. A semicolon normally holds closely related independent clauses at similar rank. A colon points forward: the second element explains, specifies, exemplifies, or fulfils the first. Coordination and subordination do more than change punctuation; they state logical relations and redistribute emphasis. Public-sector plain-language guidance also advises against using semicolons merely to extend a sentence.

Sources:

- [Chicago Manual of Style Q&A, dash flexibility and overuse](https://www.chicagomanualofstyle.org/qanda/data/faq/topics/HyphensEnDashesEmDashes/faq0181.html)
- [MLA Style Center, colons and the expansion relation](https://style.mla.org/colons-how-to-use-them/)
- [MLA Style Center, semicolon constructions](https://style.mla.org/quiz-semicolons/)
- [Purdue Writing Lab, sentence structure and emphasis](https://owl.purdue.edu/owl/graduate_writing/introduction_to_writing/documents/revising-and-editing/sentence-structure-activity.pdf)
- [Australian Government Style Manual, semicolons and plain-language alternatives](https://www.stylemanual.gov.au/grammar-punctuation-and-conventions/punctuation/semicolons)
- [Australian Government Style Manual, colon functions](https://www.stylemanual.gov.au/grammar-punctuation-and-conventions/punctuation/colons)

Operational consequence: do not replace an em dash character-for-character. Identify whether it carries explanation, balance, contrast, cause, sequence, an aside, or an interruption; then rebuild the syntax and verify the changed emphasis. See `references/punctuation-and-sentence-flow.md` for the working procedure and original transformations.

## What mainstream publication practice can support

Publication guidance is practice evidence, not proof that one structure fits every genre. Several large news organisations converge on useful editorial habits:

- A Guardian news-writing guide recommends planning an information hierarchy before drafting, selecting one main development for the introduction, and using later paragraphs to add detail, explanation, context, and voices.
- BBC Academy guidance for online features asks what the reader will want to know next. It recommends mixing sentence and paragraph scale for rhythm, warns that too many short paragraphs are hard to read, and calls for a link when the topic changes.
- The Associated Press has used short, self-contained blocks for live developments while distinguishing that format from a written-through story that restores detail and background. Its news principles also require outside material to be reassessed and rewritten in AP's own approach, structure, and language rather than republished unchanged.
- The Economist's public style-guide excerpt treats professional jargon as useful when it carries specialist meaning and obstructive when it merely renames a familiar idea or conceals what happened.
- The Guardian describes house style as a consistency and values framework, not a device for making every journalist sound alike. Reuters likewise begins its standards by noting that no single definition covers every kind of journalism it publishes.

Sources:

- [The Guardian, *News writing*](https://www.theguardian.com/books/2008/sep/25/writing.journalism.news)
- [BBC Academy, *Features for the News website: A guide for writers*](https://downloads.bbc.co.uk/academy/academyfiles/Features_for_the_News_website_guide_v1-0.pdf)
- [Associated Press, *The Latest format delivers the latest news*](https://www.ap.org/the-definitive-source/announcements/heres-the-latest-on-the-latest/)
- [Associated Press, *Telling the Story*](https://www.ap.org/about/news-values-and-principles/telling-the-story/)
- [The Economist, *Writing with Style*](https://education.economist.com/blog/what-to-read/writing-with-style)
- [The Guardian, *Style guide*](https://www.theguardian.com/sustainability/guardian-style-guide)
- [Reuters, *Standards and Values*](https://reutersagency.com/about/standards-values/)

Operational consequence:

1. rank material by the reader's task before polishing sentences
2. make the opening perform one clear job rather than preview every point
3. let each paragraph answer or create a real next question
4. split at changes of job and preserve enough connection to make the whole coherent
5. rewrite formulaic or borrowed prose from the facts, mechanism, and intended outcome
6. treat specialist terms, sentence length, and paragraph length as contextual choices rather than bans or quotas

Do not generalise the inverted pyramid to essays, proposals, tutorials, personal writing, or narrative features. Do not import newsroom neutrality into genres that require an owned recommendation or point of view. Translate named-publication requests into broad traits; never copy an outlet's recognisable voice, headline manner, ideology, or signature phrasing. See `references/natural-structure-and-digestibility.md` and `references/style-bundles.md` for the working rules.

## Why authorship detection is unsafe

OpenAI withdrew its own text classifier for low accuracy. In its published evaluation, it identified only 26% of AI-written challenge text and falsely labelled 9% of human text. OpenAI also warned that short text, edited text, non-English text, code, and out-of-distribution material make classification less reliable.

Source:

- [OpenAI, *New AI classifier for indicating AI-written text*](https://openai.com/index/new-ai-classifier-for-indicating-ai-written-text/)

Independent work found serious bias against writers of English as an additional language. In one study, detectors misclassified a large share of human TOEFL essays, while superficial rewriting could evade the same systems.

Sources:

- [Liang et al., *GPT detectors are biased against non-native English writers*](https://www.cell.com/patterns/fulltext/S2666-3899(23)00130-7)
- [Stanford HAI summary and implications](https://hai.stanford.edu/news/ai-detectors-biased-against-non-native-english-writers)
- [Weber-Wulff et al., detector accuracy and obfuscation study](https://link.springer.com/article/10.1007/s40979-023-00146-z)
- [Lu et al., transferable attacks on AI-generated text detectors](https://aclanthology.org/2023.findings-emnlp.94/)

Human judgement is not a safe substitute. Experiments have shown that people use manipulable cues and can fail to distinguish model-generated self-presentation from human writing.

Source:

- [Jakesch, Hancock, and Naaman, *Human heuristics for AI-generated language are flawed*](https://sml.stanford.edu/publications/2023/human-heuristics-ai-generated-language-are-flawed)

Operational consequence: this skill and its scanner produce editorial signals, never an accusation, probability of guilt, or academic-integrity verdict.

## Evidence for authorship-preserving revision

Writing guidance from the University of Waterloo recommends revising structure, flow, and clarity before mechanics. It warns that AI suggestions can be generic or wrong and can alter voice and nuance. Research prototypes such as Textfocals support writers with summaries, questions, and advice while leaving replacement prose to the writer.

Sources:

- [University of Waterloo Writing and Communication Centre, *Using Generative AI to Revise Writing*](https://uwaterloo.ca/writing-and-communication-centre/Resources-AI-Revising)
- [Kim et al., *Towards Full Authorship with AI: Supporting Revision with AI-Generated Views*](https://arxiv.org/abs/2403.01055)
- [UNESCO, *Guidance for generative AI in education and research*](https://www.unesco.org/en/articles/guidance-generative-ai-education-and-research)

Operational consequence:

1. keep the writer as the source of thesis, experience, and judgement
2. diagnose before generating replacement prose
3. revise structure and evidence before style
4. preserve culturally and personally meaningful voice
5. verify claims and disclose AI assistance when policy requires it

## Corpus acceptance standard

Classify candidate signals by evidence tier:

| Tier | Evidence | Appropriate use |
|---|---|---|
| A | replicated or large multi-domain research | calibrated feature or strong review prompt |
| B | one controlled corpus or strong domain study | contextual pattern with explicit confounds |
| C | repeated editorial or community observation | low-confidence prompt with counterexamples |
| D | one anecdote or disliked phrase | do not add yet |

Every accepted pattern needs:

- a stable identifier and category
- a precise definition or regex
- positive examples and counterexamples
- severity and confidence kept separate
- a minimum occurrence or cluster rule
- likely confounds and exceptions
- a concrete revision action
- evidence URLs and last-reviewed date

Re-test patterns as models, genres, and human usage change. Remove rules that no longer discriminate a writing problem or that create more harm than editorial value.
