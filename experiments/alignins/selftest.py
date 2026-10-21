"""Self-test for src/defenses/alignins.py (iteration 5). CPU seconds, no data.

Synthetic round: 10 clients, 2000 trainable coordinates plus one counter
coordinate. Honest deltas share a direction; 2 'malicious' deltas are rotated.
Checks: (a) trainable-subspace decisions ignore the buffer block entirely;
(b) under `full`, MPSA moves by at most 1/k (the counter is one + coordinate);
(c) under `full`, the TDA spread is compressed and its residue follows the
client's batch count. Prints the numbers; asserts (a) and (b).
"""
import numpy as np

from src.defenses.alignins import AlignIns


def main():
    rng = np.random.RandomState(0)
    n, d = 10, 2000
    base = rng.normal(size=d)
    deltas = 0.05 * (0.6 * base + rng.normal(size=(n, d)))
    deltas[:2] = 0.05 * (0.6 * rng.normal(size=d) + rng.normal(size=(2, d)))  # rotated
    theta = rng.normal(size=d) * 0.1 + 0.3 * base * 0.05
    b = rng.randint(5, 40, size=n).astype(float)         # local batches (Dirichlet-like)
    C = 15 * 16.0                                         # global counter after 15 rounds
    full_d = np.hstack([deltas, b[:, None]])
    full_g = np.hstack([theta, [C]])
    mask = np.r_[np.ones(d, bool), False]

    a_tr = AlignIns(); a_tr.set_signal_mask(mask)
    a_fu = AlignIns(); a_fu.set_signal_mask(None)
    t_tr, m_tr, _ = a_tr.scores(full_d, full_g)
    a_plain = AlignIns()
    t0, m0, _ = a_plain.scores(deltas, theta)            # no buffers at all
    t_fu, m_fu, _ = a_fu.scores(full_d, full_g)
    assert np.allclose(t_tr, t0) and np.allclose(m_tr, m0), "mask must remove buffers"
    k = int((d + 1) * 0.3)
    assert np.max(np.abs(m_fu - m0)) <= 1.0 / k + 0.02, "MPSA should barely move"
    print("TDA trainable:", np.round(t0, 4), "sd", round(float(np.std(t0)), 4))
    print("TDA full     :", np.round(t_fu, 6), "sd", round(float(np.std(t_fu)), 6))
    print("corr(TDA_full, b/||d||):",
          round(float(np.corrcoef(t_fu, b / np.linalg.norm(full_d, axis=1))[0, 1]), 4))
    print("max |MPSA_full - MPSA|:", round(float(np.max(np.abs(m_fu - m0))), 5), "1/k =", round(1 / k, 5))
    keep = lambda t, m, A: (A._mz(m) < 1) & (A._mz(t) < 1)
    print("kept trainable:", np.where(keep(t0, m0, a_plain))[0].tolist())
    print("kept full     :", np.where(keep(t_fu, m_fu, a_fu))[0].tolist(), "(clients 0,1 rotated)")
    print("batch counts  :", b.astype(int).tolist())
    print("OK")


if __name__ == "__main__":
    main()
