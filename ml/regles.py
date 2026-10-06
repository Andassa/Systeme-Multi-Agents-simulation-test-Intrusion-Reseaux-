"""Signatures RM1–RM11 (CIM). Confiances = précision mesurée sur le train. Abstention = uniforme."""
import numpy as np

from constants import NB_CLASSES

NOM_CLASSE = {"NORMAL": 0, "DOS": 1, "PROBE": 2, "R2L": 3, "U2R": 4}

# Services typiques des attaques par force brute / accès distant (R2L).
_SERVICES_R2L = ("telnet", "login", "ssh", "ftp", "pop_3", "imap4")

REGLES = [
    ("RM1", lambda d: (d.serror_rate > 0.8) & (d["count"] >= 100), "DOS", 0.999),
    ("RM2", lambda d: (d.protocol_type == "icmp") & (d.src_bytes > 1000), "DOS", 1.000),
    ("RM3", lambda d: (d.flag == "S0") & (d.same_srv_rate > 0.9), "DOS", 0.575),
    ("RM4", lambda d: (d.land == 1), "DOS", 0.720),
    ("RM5", lambda d: (d.diff_srv_rate > 0.7), "PROBE", 0.684),
    ("RM6", lambda d: (d.rerror_rate > 0.8) & (d["count"] >= 50), "PROBE", 0.233),
    # RM7 assoupli (hot >= 1) : précision train ≈ 0.265
    ("RM7", lambda d: (d.is_guest_login == 1) & (d.hot >= 1), "R2L", 0.265),
    ("RM8", lambda d: (d.num_file_creations >= 1) & (d.num_shells >= 1), "U2R", 0.500),
    # RM9–RM11 : ciblage R2L/U2R (précisions train)
    (
        "RM9",
        lambda d: (
            (d.num_failed_logins >= 1)
            & (d.logged_in == 0)
            & (d.service.isin(list(_SERVICES_R2L)))
        ),
        "R2L",
        0.547,
    ),
    (
        "RM10",
        lambda d: (d.service == "telnet") & (d.num_failed_logins >= 1),
        "R2L",
        0.565,
    ),
    (
        "RM11",
        lambda d: (d.root_shell == 1) & (d.num_file_creations >= 1),
        "U2R",
        0.467,
    ),
]


def evaluer(df, k: int = NB_CLASSES):
    n = len(df)
    conf = np.zeros(n)
    cls = np.zeros(n, dtype=int)
    rid = np.empty(n, dtype=object)
    rid[:] = "ABSTENTION"

    for rule_id, pred, classe, cf in REGLES:
        mask = pred(df).values & (cf > conf)
        conf[mask] = cf
        cls[mask] = NOM_CLASSE[classe]
        rid[mask] = rule_id

    p = np.full((n, k), 1.0 / k)
    fire = conf > 0
    p[fire] = (1.0 - conf[fire])[:, None] / (k - 1)
    p[fire, cls[fire]] = conf[fire]
    return p, rid, fire
