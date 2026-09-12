# Research notes

Use this reference when you need the evidence behind the humanisation rules, want to extend `assets/aiisms.json`, or need to explain why the scanner cannot determine authorship.

Last reviewed: 2026-07-17.

## What the evidence supports

### Lexical preferences exist, but they move

Large-corpus studies have measured abrupt increases in certain style words after widespread LLM adoption. Kobak and colleagues analysed more than 15 million biomedical abstracts and found excess use of families including `additionally`, `delve`, `showcasing`, `crucial`, `notably`, `comprehensive`, `pivotal`, `potential`, `intricate`, and `underscore`. Juzek and Ward examined 26.7 million PubMed abstracts; their focal forms included `delve`, `showcase`, `boast`, `underscore`, `intricate`, `realm`, `garner`, `groundbreaking`, `advancements`, `align`, and `surpass`.

Other studies broaden or qualify the list. Kousha and Thelwall's cross-database full-text study retained `underscore`, `delve`, `showcase`, `unveil`, `intricate`, `meticulous`, `pivotal`, `heighten`, `nuance`, `bolster`, `foster`, and `interplay`, while stressing disciplinary confounds. A multi-genre parallel-corpus study found preferences including `tapestry`, `palpable`, `camaraderie`, `amidst`, and `vibrant`, along with nominalisation and participial clauses. Liang and colleagues found disproportionate praise adjectives in AI-assisted peer reviews, but those results belong to academic-review language rather than prose in general.

These studies estimate change across corpora. They do not establish that a given author or sentence used a model.

Sources:

- [Kobak et al., *Delving into LLM-assisted writing in biomedical publications through excess vocabulary*](https://arxiv.org/abs/2406.07016)
- [Juzek and Ward, *Why Does ChatGPT “Delve” So Much?*](https://aclanthology.org/2025.coling-main.426/)
- [Liang et al., *Monitoring AI-Modified Content at Scale*](https://proceedings.mlr.press/v235/liang24b.html)
- [Kousha and Thelwall, full-text marker study in *Scientometrics*](https://link.springer.com/article/10.1007/s11192-026-05601-5)
- [Multi-genre parallel-corpus study in *PNAS*](https://pmc.ncbi.nlm.nih.gov/articles/PMC11874169/)

Lexical signals also drift. Public discussion can make writers and model users avoid a notorious word while other preferred words continue to rise. Human speech can absorb model-associated wording as people encounter it. A static blacklist therefore decays quickly and risks punishing ordinary language.

Sources:

- [Geng and Trotta, *Human-AI Coevolution*](https://arxiv.org/abs/2502.09606)
- [Yakura et al., *Empirical evidence of Large Language Model’s influence on human spoken communication*](https://arxiv.org/abs/2409.01754)

Operational consequence: treat bare words as weak, contextual signals. Record review dates and test counterexamples. A phrase family may still receive an editorial remove or rewrite default when its function is reliably empty or obscuring; that is a house rule for better prose, not evidence of authorship.

### Phrase families are useful editorial leads, not universal fingerprints

Candidate-list evaluations, expert-observation studies, and editorial field guides repeatedly notice families rather than isolated spellings: `valuable insights`, `crucial role in shaping`, `gain deeper understanding`, `not only X but also Y`, `it is important to note`, `in a world where`, `paving the way`, and prestige metaphors such as `landscape`, `realm`, `tapestry`, and `roadmap`. Editorial observations also identify significance frames such as `serves as a testament`, `plays a key role`, `reflects a broader movement`, and `marks a significant shift`.

The limitations are important. Schmalz and Tack evaluate GPTZero vocabulary lists; the lists perform worse than full-vocabulary models and generalise poorly across model families. Russell, Karpinska, and Iyyer study expert authorship judgements, not an editorial standard. Wikipedia's field guide is a descriptive, community-maintained account for one publishing environment. These sources supply candidates and counterexamples. They do not validate a universal blacklist or prove that a phrase is bad after one occurrence.

`Gap` was not among the focal words in the strongest word-frequency studies reviewed; those studies do not establish whether it is or is not a marker. `Shift` appears in limited editorial and community phrase lists, not in evidence that validates a universal ban. The skill uses `bridge the gap` and `marks a significant shift` as house-style examples because they often hide the proposition. It does not treat either noun as evidence of authorship.

Sources:

- [Schmalz and Tack, evaluation of fixed AI-vocabulary lists and cross-model transfer](https://aclanthology.org/2025.bea-1.71/)
- [Russell, Karpinska, and Iyyer, expert comparison of human and model nonfiction](https://aclanthology.org/2025.acl-long.267/)
- [Wikipedia's editorial guide to recurring AI-writing signs](https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing)

Public avoid lists are useful for discovery only. A popular community skill, a LinkedIn discussion, and an editor's Medium post converge on presenter hooks such as `here's the kicker`, negative reveals, generic openings, transition stacks, and formal service language. The discussions themselves contain counterexamples and objections: several commenters note that people used these phrases long before current models and that disability, dialect, genre, and second-language writing can produce the same surface forms. The skill therefore accepts a candidate from such sources only when the phrase also identifies a repairable editorial problem, and it assigns low confidence unless stronger evidence exists.

- [Conor Bronsdon, *Avoid AI Writing* community skill](https://github.com/conorbronsdon/avoid-ai-writing/blob/main/SKILL.md)
- [Christian Di Bratto, LinkedIn discussion of recurring social-post phrases](https://www.linkedin.com/posts/dibratto_i-made-a-list-of-all-the-words-and-phrases-activity-7316792225999269889-auSz)
- [Amelia, editor's list of recurring ChatGPT-style phrases](https://medium.com/@ameliasoul10/10-phrases-that-instantly-tell-me-you-used-chatgpt-from-a-professional-editors-desk-4e9862f96767)
- [UNESCO, *AI and the great linguistic flattening*](https://www.unesco.org/en/articles/ai-and-great-linguistic-flattening)

Mainstream editorial reporting offers corroboration, not causal proof. The Guardian has discussed `delve`, `explore`, `tapestry`, `testament`, and `leverage`, and later reported corpus findings involving `showcase`, `boast`, `underscore`, `garner`, and `align`. Its earlier account also shows why a blacklist can become discriminatory: wording associated with model output may be normal in a regional variety of English.

- [The Guardian, *How cheap, outsourced labour in Africa is shaping AI English*](https://www.theguardian.com/technology/2024/apr/16/techscape-ai-gadgest-humane-ai-pin-chatgpt)
- [The Guardian, *How AI is changing language*](https://www.theguardian.com/books/ng-interactive/2026/jul/04/future-of-fiction-next-great-novel-ai-language-chat-gpt)
- [The Guardian, commentary on the overused `not X, but Y` frame](https://www.theguardian.com/commentisfree/2026/apr/15/chatgpt-stylistic-quirk-its-not-x-its-y)
- [The Atlantic, *The Biggest Tell That Something Was Written by AI*](https://www.theatlantic.com/technology/2026/05/how-to-tell-ai-writing/687345/)
- [The Atlantic, *Why AI Is Incorrigibly Didactic*](https://www.theatlantic.com/ideas/2026/06/ai-writing-style-literature/687536/)

Operational consequence:

1. remove empty assistant and presentation wrappers by default
2. rewrite canned semantic frames from actors, mechanisms, evidence, comparisons, or consequences
3. review ordinary words, transitions, and punctuation only in context or density
4. preserve literal, technical, legal, measured, quoted, and writer-owned uses
5. never treat a match as proof that a model wrote the passage

### Some newer families need genre-specific caution

Academic boilerplate, self-awarded praise, templated empathy, and sentimental narrative diction deserve separate treatment. Peer-review corpora support close review of evaluative words such as `commendable`, `noteworthy`, `invaluable`, and self-awarding success adverbs in that genre. Experimental work on sycophancy supports removing blanket validation that agrees with a user before weighing evidence. Emerging multi-genre and narrative studies support reviewing repeated atmospheric clusters, uniform paragraph movement, compulsory morals, and overly tidy resolution. None of these findings justifies banning an emotion word, an academic phrase, or a narrative technique in isolation.

Sources:

- [Liang et al., AI-modified peer-review language](https://proceedings.mlr.press/v235/liang24b.html)
- [Sycophantic AI decreases prosocial intentions and promotes dependence](https://doi.org/10.1126/science.aec8352)
- [Multi-genre human and model parallel-corpus study](https://arxiv.org/html/2410.16107)
- [StoryScope narrative-feature study](https://arxiv.org/abs/2604.03136)

Operational consequence: use these families to prompt a genre-aware meaning check. Rewrite praise from criteria, validation from evidence, empathy from the actual situation, and atmosphere from observed detail. Preserve deliberate voice, care, quotation, technical meaning, and genre conventions.

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

Operational consequence: scan across categories and explain the observation. A comprehensive catalogue helps editors search; it must not reduce a multidimensional writing problem to mechanical word replacement.

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

Classify candidate signals by evidence tier. The tier records evidence that a distribution or family recurs; it does not grade prose quality and never determines the remove, rewrite, or review action by itself.

| Tier | Evidence | Appropriate use |
|---|---|---|
| A | replicated or large multi-domain research directly observing the feature family | calibrated distributional or structural review prompt |
| B | one controlled corpus or strong domain study directly observing the feature family | contextual pattern confined to the supported genres and confounds |
| C | indirect research lead or repeated editorial/community observation | low-confidence editorial prompt with counterexamples |
| D | one anecdote or disliked phrase | do not add yet |

Every accepted pattern needs:

- a stable identifier and category
- a precise definition or regex
- positive examples and counterexamples
- severity and confidence kept separate
- an explicit action: remove, rewrite, or review
- a minimum occurrence or cluster rule
- a bounded cluster scope where clustering can gate
- likely confounds and exceptions
- a concrete revision action
- evidence URLs and last-reviewed date

Re-test patterns as models, genres, and human usage change. Remove rules that no longer identify a writing problem or that create more harm than editorial value. A rule can remain useful even when it does not distinguish human from model text; the acceptance test is whether it finds a repairable editorial problem without damaging precise prose.
