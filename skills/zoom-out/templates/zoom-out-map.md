**Target**
<Name the symbol, file, route, feature, or subsystem and the repository scope inspected.>

**One-Layer Map**
| Role | Files / Symbols | Why they matter |
| --- | --- | --- |
| Entry points | <paths> | <how execution reaches the area> |
| Orchestrators | <paths> | <what coordinates the behavior> |
| Target owner | <paths> | <where the target is defined or primarily owned> |
| Downstream dependencies | <paths> | <what the target invokes or persists through> |
| Tests / fixtures | <paths> | <what verifies or documents behavior> |

**Caller Paths**
1. <entrypoint> -> <caller> -> <target> [Verified by <file/symbol>]
2. <possible caller> -> <target> [Likely/Lead: <evidence>]

**Boundaries**
- <Boundary type>: <what crosses it and where>

**Evidence**
- Commands/searches: `<command>`
- Files read: <paths>
- Symbols inspected: <symbols>

**Unknowns**
- <What is not yet verified and how to verify it>

**Next Reads**
1. <highest-value file>
2. <next file>
3. <test/config/registration file>
