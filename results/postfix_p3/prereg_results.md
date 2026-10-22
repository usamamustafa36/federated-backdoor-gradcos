# Confirmatory hypotheses (iterations/PREREG_P3.md); INTERIM: one-sided exact sign-flip, Holm per family

| id | family | rule | part | atk | metric | dir | blind | n | +/- | diff | p (1-sided) | p_Holm | p_Holm blind-only |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| P1 | primary | fltrust | dirichlet | 0 | FPR | + | partial | 10 | 10/0 | +0.638 | 0.0009766 | 0.003906 | nan |
| P2 | primary | fltrust | iid | 0 | FPR | + | yes | 5 | 5/0 | +0.996 | 0.03125 | 0.0625 | 0.0625 |
| P3 | primary | fltrust | dirichlet | 1 | DR | + | partial | 10 | 9/0 | +0.510 | 0.001953 | 0.005859 | nan |
| P4 | primary | fltrust | iid | 1 | DR | + | yes | 5 | 5/0 | +1.000 | 0.03125 | 0.0625 | 0.0625 |
| S1 | secondary | normclip | dirichlet | 0 | CA | + | yes | 10 | 7/3 | +0.005 | 0.04785 | 0.1914 | 0.1436 |
| S2 | secondary | normclip | iid | 0 | CA | + | yes | 10 | 8/2 | +0.001 | 0.07227 | 0.2168 | 0.1445 |
| S3 | secondary | flame | dirichlet | 0 | CA | + | partial | 10 | 5/5 | -0.014 | 0.8994 | 0.9375 | nan |
| S4 | secondary | flame | iid | 0 | CA | + | yes | 5 | 3/2 | +0.000 | 0.4688 | 0.9375 | 0.4688 |
