# Patterns

The translator is deterministic by design. It should feel playful, not random.

## Translation Pattern

The forward translator turns a plain statement into an announcement arc with these stages:

1. opener
2. accomplishment restatement
3. reflection on growth, collaboration, or momentum
4. gratitude or forward-looking sentence
5. emoji and hashtags, unless disabled

The exact wording is chosen by hashing the normalized input. That keeps identical inputs stable across runs.

## Intensity Levels

| Intensity | Behavior |
| --- | --- |
| `1` | One short opener plus one grounded summary sentence |
| `2` | Adds a gratitude or reflection sentence |
| `3` | Default. Adds both reflection and gratitude plus 3-4 hashtags |
| `4` | Adds stronger hype and 4-5 hashtags |
| `5` | Maximum cringe: bigger opener, extra framing, and the most flamboyant closer |

## Action Detection

The engine scans for action verbs and nouns, then reframes them:

| Signal | Typical framing |
| --- | --- |
| `shipped`, `launched`, `released` | "brought something into the world" |
| `finished`, `completed`, `wrapped` | "crossed the finish line" |
| `learned`, `studied` | "invested in growth" |
| `hired`, `joined`, `new job` | "starting a new chapter" |
| `spoke`, `presented` | "shared ideas with an incredible room" |
| `fixed`, `debugged` | "turned a challenge into momentum" |
| `built`, `created` | "built something meaningful" |

## Hashtag Selection

Hashtags are derived from topic keywords first, then padded with generic LinkedIn staples.

Topic-aware tags include:

- product work: `#Innovation`, `#ProductManagement`
- shipping or launch work: `#Launch`, `#Execution`
- leadership work: `#Leadership`, `#Teamwork`
- learning work: `#GrowthMindset`, `#ContinuousLearning`
- hiring or career change: `#CareerGrowth`, `#NewBeginnings`
- data or dashboards: `#Analytics`, `#DataStrategy`

Generic fallback tags:

- `#GrowthMindset`
- `#Leadership`
- `#Collaboration`
- `#Innovation`
- `#LearningInPublic`
- `#CareerDevelopment`

## Reverse Pattern

The reverse translator does not attempt perfect semantic parsing. It follows a reliable simplification path:

1. strip emojis and hashtags
2. delete stock hype phrases like "thrilled to announce" and "grateful for the opportunity"
3. collapse extra whitespace and repeated punctuation
4. shorten inflated framing to a plain action sentence
5. trim the output to the most factual clauses

## Example Pairs

| Plain input | LinkedIn-speak |
| --- | --- |
| `I got a new job.` | `Thrilled to share that I'm starting a new chapter with a new role. Moments like this are a reminder that growth compounds when great people invest in you. Grateful for everyone who helped me get here, and excited for what comes next. 🚀 #CareerGrowth #NewBeginnings #GrowthMindset #Leadership` |
| `We launched the dashboard.` | `Excited to announce that we officially brought a new dashboard into the world today. This was a strong lesson in alignment, execution, and building with intention. Proud of the team for turning momentum into something real. 🚀 #Launch #Analytics #Collaboration #Innovation` |

## Read Next

- `references/commands.md` for exact invocation patterns
- `references/gotchas.md` for the rough edges and comedy limits
- `scripts/linkedin_speak.py` for the authoritative implementation
