# Confirmatory hypotheses (iterations/PREREG_P3.md); INTERIM: one-sided exact sign-flip, Holm per family

| id | family | rule | part | atk | metric | dir | blind | n | +/- | diff | p (1-sided) | p_Holm | p_Holm blind-only |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| P1 | primary | fltrust | dirichlet | 0 | FPR | + | partial | 5 | 5/0 | +0.716 | 0.03125 | 0.125 | nan |
| P2 | primary | fltrust | iid | 0 | FPR | + | yes | 0 | 0/0 | +nan | nan | 1 | 1 |
| P3 | primary | fltrust | dirichlet | 1 | DR | + | partial | 5 | 5/0 | +0.580 | 0.03125 | 0.125 | nan |
| P4 | primary | fltrust | iid | 1 | DR | + | yes | 0 | 0/0 | +nan | nan | 1 | 1 |
| S1 | secondary | normclip | dirichlet | 0 | CA | + | yes | 5 | 4/1 | +0.008 | 0.0625 | 0.25 | 0.1875 |
| S2 | secondary | normclip | iid | 0 | CA | + | yes | 0 | 0/0 | +nan | nan | 1 | 1 |
| S3 | secondary | flame | dirichlet | 0 | CA | + | partial | 5 | 3/2 | -0.006 | 0.6875 | 1 | nan |
| S4 | secondary | flame | iid | 0 | CA | + | yes | 0 | 0/0 | +nan | nan | 1 | 1 |
