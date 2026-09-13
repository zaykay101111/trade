# NFL quarterback impact research comparison

Research only: no odds, ROI, stakes, or evidence of beating bookmakers. Kickoff times were converted from US Eastern by us and schedule observation times are reconstructed, not provider timestamps. Result availability assumes kickoff plus 24h. Development folds may be inspected repeatedly and can be overfit; they are not confirmation.

RESEARCH CANDIDATE. Base NFL features versus the same plus quarterback expected-starter features: mean passing EPA over that quarterback's last 8 games whose results were available before the cutoff, settled start count, an unknown-starter indicator and a backup indicator, all home minus away. The EXPECTED starter is the quarterback who started the team's most recent settled game; the target game's own starter is never read. Declared injury status is NOT used: the nflverse injuries feed carries no timestamp and cannot establish what was declared before a past kickoff. Development evidence only; not confirmation.


- 2022: base 0.652487 vs qb 0.649939
- 2023: base 0.647153 vs qb 0.649529
- 2024: base 0.632872 vs qb 0.619456

Pooled qb minus base (decided games): -0.004537; 95% week-block interval [-0.015701, +0.006485]  (includes zero).

Development evidence only; adoption would require a new frozen release and prospective capture.
