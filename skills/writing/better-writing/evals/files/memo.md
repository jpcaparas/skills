# Q3 queue review

We should pause the queue migration until the owner confirms the backfill. In staging, the latest run processed 18.4% more records than the previous run. We have not tested this in production. The change may reduce manual work, but the estimate is still uncertain.

“A faster queue is useful only if we can explain when it is safe.”

Next step: ask the owner for a go/no-go decision before the Q3 cutover.
